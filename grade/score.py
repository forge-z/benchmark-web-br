#!/usr/bin/env python3
"""Líquido = certo − errado, com intervalo de 95% por bootstrap.

O bootstrap sorteia os itens (consulta, URL ou empresa) com reposição e
recalcula o líquido nas células desses itens. Uma consulta com vários
resultados não é partida no meio.

Semente 20261118, 2000 reamostras. O percentil usa o mesmo corte do método
de referência: a posição round(0,025 n) − 1 e round(0,975 n) − 1 da lista
ordenada.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def net(cells: list[dict], penalty: float = 1.0) -> float:
    right = sum(cell["grade"] == "certo" for cell in cells)
    wrong = sum(cell["grade"] == "errado" for cell in cells)
    blank = sum(cell["grade"] == "branco" for cell in cells)
    total = right + wrong + blank
    if not total:
        return 0.0
    return 100.0 * (right - penalty * wrong) / total


def counts(cells: list[dict]) -> dict:
    graded = [cell for cell in cells if cell["grade"] in {"certo", "errado", "branco"}]
    right = sum(cell["grade"] == "certo" for cell in graded)
    wrong = sum(cell["grade"] == "errado" for cell in graded)
    blank = sum(cell["grade"] == "branco" for cell in graded)
    total = right + wrong + blank
    return {
        "graded": total,
        "certo": right,
        "errado": wrong,
        "branco": blank,
        "certo_por_100": round(100 * right / total, 1) if total else 0.0,
        "errado_por_100": round(100 * wrong / total, 1) if total else 0.0,
        "branco_por_100": round(100 * blank / total, 1) if total else 0.0,
        "liquido": round(net(graded), 1) if total else 0.0,
    }


def bootstrap(cells: list[dict], *, resamples: int = 2000, seed: int = 20261118, penalty: float = 1.0) -> tuple[float, float]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for cell in cells:
        if cell["grade"] in {"certo", "errado", "branco"}:
            grouped[cell["item_id"]].append(cell)
    keys = sorted(grouped)
    if not keys:
        return 0.0, 0.0
    rng = random.Random(seed)
    samples = []
    for _ in range(resamples):
        drawn = [rng.choice(keys) for _ in keys]
        pooled = [cell for key in drawn for cell in grouped[key]]
        samples.append(net(pooled, penalty))
    samples.sort()
    low_i = int(round(0.025 * resamples)) - 1
    high_i = int(round(0.975 * resamples)) - 1
    low_i = max(0, min(low_i, resamples - 1))
    high_i = max(0, min(high_i, resamples - 1))
    return samples[low_i], samples[high_i]


def _is_grade(cell: dict) -> bool:
    return cell.get("grade") in {"certo", "errado", "branco"}


def by_tool(cells: list[dict], **kwargs) -> list[dict]:
    tools = sorted({cell["tool"] for cell in cells if _is_grade(cell)})
    rows = []
    for tool in tools:
        subset = [cell for cell in cells if cell["tool"] == tool]
        row = {"tool": tool, **counts(subset)}
        low, high = bootstrap(subset, **kwargs)
        row["liquido_lo"] = round(low, 1)
        row["liquido_hi"] = round(high, 1)
        rows.append(row)
    rows.sort(key=lambda row: -row["liquido"])
    return rows


def paired(cells: list[dict], **kwargs) -> list[dict]:
    tools = sorted({cell["tool"] for cell in cells if _is_grade(cell)})
    out = []
    for i, left in enumerate(tools):
        for right in tools[i + 1:]:
            # Difference of nets on the same resampled items, right minus left.
            grouped: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
            for cell in cells:
                if cell["tool"] in {left, right} and cell["grade"] in {"certo", "errado", "branco"}:
                    grouped[cell["item_id"]][cell["tool"]].append(cell)
            keys = sorted(grouped)
            if not keys:
                continue
            rng = random.Random(kwargs.get("seed", 20261118))
            resamples = kwargs.get("resamples", 2000)
            diffs = []
            for _ in range(resamples):
                drawn = [rng.choice(keys) for _key in keys]
                a = [cell for key in drawn for cell in grouped[key][left]]
                b = [cell for key in drawn for cell in grouped[key][right]]
                diffs.append(net(b) - net(a))
            diffs.sort()
            low_i = max(0, int(round(0.025 * resamples)) - 1)
            high_i = min(resamples - 1, int(round(0.975 * resamples)) - 1)
            low, high = diffs[low_i], diffs[high_i]
            out.append({
                "primeiro": left,
                "segundo": right,
                "diferenca": round(net([c for c in cells if c["tool"] == right]) - net([c for c in cells if c["tool"] == left]), 1),
                "lo": round(low, 1),
                "hi": round(high, 1),
                "longe_de_zero": bool(low > 0 or high < 0),
            })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calcula o líquido e o intervalo de 95%.")
    parser.add_argument("--cells", required=True, help="JSONL de células produzido por grade.py")
    parser.add_argument("--resamples", type=int, default=2000)
    args = parser.parse_args(argv)
    path = Path(args.cells)
    if not path.exists():
        print("sem células para pontuar")
        return 0
    cells = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cells:
        print("sem células para pontuar")
        return 0
    rows = by_tool(cells, resamples=args.resamples)
    print(json.dumps({"por_ferramenta": rows, "pares": paired(cells, resamples=args.resamples)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
