#!/usr/bin/env python3
"""Sorteia uma amostra reprodutível para revisão humana.

A correção automática não chama modelo. Este script escolhe itens com
random.Random(seed) e grava um CSV com colunas vazias para o revisor.

Sem --cells, a população são as linhas dos datasets (consulta, URL, empresa),
ordenadas por prova e id. Com --cells, a população são os pares
(ferramenta, prova, item) que têm ao menos uma célula certo, errado ou branco,
e o CSV traz cada célula graduada desses itens.

A população é ordenada antes do sorteio. A mesma semente e o mesmo n devolvem
o mesmo CSV. A semente padrão é 20261118.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from runners.common import ROOT, read_csv

SEED = 20261118
COLUMNS = [
    "tool", "prova", "item_id", "field", "grade", "expected", "answer",
    "revisao_humana", "comentario",
]


def dataset_units(datasets: Path) -> list[tuple[str, str, str]]:
    units = [("noticias", row["id"], row["consulta"]) for row in read_csv(datasets / "consultas_noticias.csv")]
    units += [("leitura", row["id"], row["url"]) for row in read_csv(datasets / "urls_leitura.csv")]
    units += [("empresas", row["id"], row["nome"]) for row in read_csv(datasets / "empresas.csv")]
    units.sort(key=lambda item: (item[0], item[1]))
    return units


def cell_units(cells: list[dict]) -> list[tuple[str, str, str]]:
    seen = {
        (cell["tool"], cell["prova"], cell["item_id"])
        for cell in cells
        if cell.get("grade") in {"certo", "errado", "branco"}
    }
    return sorted(seen)


def draw(units: list, n: int, seed: int) -> list:
    if n >= len(units):
        return list(units)
    return random.Random(seed).sample(list(units), n)


def rows_from_datasets(datasets: Path, n: int, seed: int) -> list[dict]:
    chosen = draw(dataset_units(datasets), n, seed)
    chosen.sort(key=lambda item: (item[0], item[1]))
    return [
        {
            "tool": "", "prova": prova, "item_id": item_id, "field": "",
            "grade": "", "expected": reference, "answer": "",
            "revisao_humana": "", "comentario": "",
        }
        for prova, item_id, reference in chosen
    ]


def rows_from_cells(cells: list[dict], n: int, seed: int) -> list[dict]:
    chosen = set(draw(cell_units(cells), n, seed))
    picked = [
        cell for cell in cells
        if (cell.get("tool"), cell.get("prova"), cell.get("item_id")) in chosen
        and cell.get("grade") in {"certo", "errado", "branco"}
    ]
    picked.sort(key=lambda cell: (cell["tool"], cell["prova"], cell["item_id"], cell["field"]))
    return [
        {
            "tool": cell["tool"],
            "prova": cell["prova"],
            "item_id": cell["item_id"],
            "field": cell["field"],
            "grade": cell["grade"],
            "expected": cell.get("expected") or "",
            "answer": cell.get("answer") or "",
            "revisao_humana": "",
            "comentario": "",
        }
        for cell in picked
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Amostra reprodutível para revisão humana.")
    parser.add_argument("--cells", default="", help="JSONL de células do grade.py. Sem isto, sorteia o dataset.")
    parser.add_argument("--datasets", default=str(ROOT / "datasets"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    if args.n < 1:
        print("n precisa ser pelo menos 1")
        return 1
    if args.cells:
        path = Path(args.cells)
        if not path.exists():
            print("sem células para amostrar")
            return 0
        cells = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = rows_from_cells(cells, args.n, args.seed)
    else:
        rows = rows_from_datasets(Path(args.datasets), args.n, args.seed)
    write_csv(Path(args.out), rows)
    print(f"{len(rows)} linhas em {args.out} (semente {args.seed})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
