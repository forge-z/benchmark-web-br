#!/usr/bin/env python3
"""Correção determinística. O juiz de LLM fica desligado se não houver chave e --llm.

As regras publicadas estão em grade/grading_rules.md. Este arquivo aplica a parte
que não precisa de modelo: data, preço, CNPJ, cidade, UF, porte, razão social,
segmento, site e a vedação de e-mail ou telefone.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import timedelta
from pathlib import Path

from runners import fields
from runners.common import ROOT, read_csv

RULES = Path(__file__).with_name("grading_rules.md")
DETERMINISTIC = {
    "cnpj", "razao_social", "cidade", "uf", "porte", "segmento", "site", "linkedin_empresa",
}


def _cell(record, field, grade, expected, answer, note) -> dict:
    return {
        "tool": record["tool"],
        "prova": record["prova"],
        "item_id": record["item_id"],
        "field": field,
        "grade": grade,
        "expected": expected,
        "answer": answer,
        "note": note,
    }


def _title_match(expected: str, answer: str) -> bool:
    left, right = fields.fold(expected), fields.fold(answer)
    if not left or not right:
        return False
    if left == right or left in right or right in left:
        return min(len(left), len(right)) >= 20 or left == right
    return False


def _date_match(expected: str, answer: str) -> bool:
    from zoneinfo import ZoneInfo

    left, right = fields.parse_datetime(expected), fields.parse_datetime(answer)
    if left is None or right is None:
        return False
    if abs((left - right).total_seconds()) <= 26 * 3600:
        return True
    zone = ZoneInfo("America/Sao_Paulo")
    return left.astimezone(zone).date() == right.astimezone(zone).date()


def grade_news(record) -> list[dict]:
    started = fields.parse_datetime(record.get("started_at") or "")
    items = (record.get("output") or {}).get("items") or []
    if started is None:
        return [
            _cell(record, "data_na_janela", "branco", "", "", "execução sem started_at"),
            _metric(record, "duplicatas_de_url", 0),
        ]
    start = started - timedelta(hours=48)
    if not items:
        return [
            _cell(record, "data_na_janela", "branco", "", "", "nenhum item"),
            _metric(record, "duplicatas_de_url", 0),
        ]
    cells = []
    seen = set()
    duplicates = 0
    for item in items:
        url = (item.get("url") or "").split("?")[0].rstrip("/")
        if url and url in seen:
            duplicates += 1
        if url:
            seen.add(url)
        raw = item.get("published_at") or ""
        parsed = fields.parse_datetime(raw)
        if not raw:
            cells.append(_cell(record, "data_na_janela", "branco", "", raw, "sem data"))
        elif parsed is None:
            cells.append(_cell(record, "data_na_janela", "errado", "", raw, "data não é ISO"))
        elif start <= parsed <= started:
            cells.append(_cell(record, "data_na_janela", "certo", "", raw, "dentro de 48 h"))
        else:
            cells.append(_cell(record, "data_na_janela", "errado", "", raw, "fora da janela de 48 h"))
    if cells and cells[0]["grade"] != "metrica":
        cells[0]["note"] = cells[0]["note"] + f"; duplicatas_de_url={duplicates}"
    cells.append(_metric(record, "duplicatas_de_url", duplicates))
    return cells


_MENU = {
    fields.fold(word) for word in (
        "menu", "home", "início", "contato", "contact", "login", "entrar",
        "cadastre-se", "newsletter", "assinar", "compartilhar", "share",
        "buscar", "search", "categorias", "institucional",
    )
}


def noise_ratio(text: str) -> float | None:
    """Share of short lines that look like a menu or a bare link. Not a grade."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if len(lines) < 5:
        return None
    noisy = 0
    for line in lines:
        folded = fields.fold(line)
        if len(line) <= 40 and folded in _MENU:
            noisy += 1
        elif ("http://" in line or "https://" in line) and len(line) < 160:
            noisy += 1
        elif len(folded.split()) <= 4 and line[:1] in "-*•":
            noisy += 1
    return round(noisy / len(lines), 4)


def _metric(record, field: str, value) -> dict:
    return {
        "tool": record["tool"],
        "prova": record["prova"],
        "item_id": record["item_id"],
        "field": field,
        "grade": "metrica",
        "expected": "",
        "answer": "" if value is None else str(value),
        "note": "não entra no líquido",
    }


def grade_page(record, expected: dict) -> list[dict]:
    output = record.get("output") or {}
    pairs = [
        ("titulo", expected.get("titulo_esperado") or "", output.get("title") or "", "titulo"),
        ("data", expected.get("data_esperada") or "", output.get("published_at") or "", "data"),
        ("preco_brl", expected.get("preco_esperado") or "", output.get("price_brl") or "", "preco"),
        ("vendedor", expected.get("vendedor_esperado") or "", output.get("seller") or "", "texto"),
        ("disponibilidade", expected.get("disponibilidade_esperada") or "", output.get("availability") or "", "texto"),
    ]
    cells = []
    for field, exp, ans, kind in pairs:
        if not exp:
            continue
        if not ans:
            cells.append(_cell(record, field, "branco", exp, ans, "gabarito preenchido e resposta vazia"))
            continue
        if kind == "titulo":
            ok = _title_match(exp, ans)
        elif kind == "data":
            ok = _date_match(exp, ans)
        elif kind == "preco":
            ok = fields.canonical_price(exp) == fields.canonical_price(ans) and fields.canonical_price(exp) != ""
        else:
            ok = fields.fold(exp) == fields.fold(ans)
        cells.append(_cell(record, field, "certo" if ok else "errado", exp, ans, ""))
    cells.append(_metric(record, "ruido", noise_ratio(output.get("text") or "")))
    cells.append(_metric(record, "bloqueio", bool(output.get("blocked"))))
    return cells


def _company_match(field: str, expected: str, answer: str) -> bool:
    if field == "cnpj":
        return fields.cnpj_valid(answer) and fields.cnpj_digits(expected) == fields.cnpj_digits(answer)
    if field == "site":
        return fields.host_of(expected) == fields.host_of(answer) and fields.host_of(expected) != ""
    if field == "linkedin_empresa":
        return fields.linkedin_company_url(answer).rstrip("/").lower() == (expected or "").rstrip("/").lower() and "/company/" in answer.lower()
    if field == "segmento":
        left, right = fields.fold(expected), fields.fold(answer)
        return bool(left) and (left == right or left in right or right in left)
    return fields.fold(expected) == fields.fold(answer) and bool(fields.fold(expected))


def grade_company(record, expected: dict, judge: bool) -> list[dict]:
    answers = ((record.get("output") or {}).get("answers") or {})
    cells = []
    for field in fields.COMPANY_FIELDS:
        exp = (expected.get(field) or "").strip()
        raw = answers.get(field) or {}
        ans = (raw.get("value") or "").strip() if isinstance(raw, dict) else str(raw or "").strip()
        if ans and fields.contains_contact(ans):
            cells.append(_cell(record, field, "errado", exp, ans, "resposta traz e-mail ou telefone"))
            continue
        if field not in DETERMINISTIC:
            # Cargo e notícia ficam de fora enquanto o juiz não roda.
            continue
        if field == "cnpj" and ans and not fields.cnpj_valid(ans):
            cells.append(_cell(record, field, "errado", exp, ans, "CNPJ com dígito verificador inválido"))
            continue
        if not exp:
            continue
        if not ans:
            cells.append(_cell(record, field, "branco", exp, ans, "gabarito preenchido e resposta vazia"))
            continue
        ok = _company_match(field, exp, ans)
        cells.append(_cell(record, field, "certo" if ok else "errado", exp, ans, ""))
    return cells


def load_expected(datasets: Path) -> dict[str, dict]:
    pages = {row["id"]: row for row in read_csv(datasets / "urls_leitura.csv")}
    companies = {row["id"]: row for row in read_csv(datasets / "empresas.csv")}
    return {"leitura": pages, "empresas": companies}


def grade_records(records: list[dict], datasets: Path, *, judge: bool = False) -> list[dict]:
    expected = load_expected(datasets)
    cells = []
    for record in records:
        if record.get("dry_run") or record.get("skipped"):
            continue
        prova = record.get("prova")
        if prova == "noticias":
            cells.extend(grade_news(record))
        elif prova == "leitura":
            cells.extend(grade_page(record, expected["leitura"].get(record["item_id"], {})))
        elif prova == "empresas":
            cells.extend(grade_company(record, expected["empresas"].get(record["item_id"], {}), judge))
    return cells


def maybe_judge(cells: list[dict]) -> list[dict]:
    """Optional hook. Off unless GRADE_LLM_API_KEY and GRADE_LLM_BASE_URL are set.

    The call is intentionally not made from the default path. This function is
    the only place a judge request would be built, and tests do not call it.
    """
    if not os.environ.get("GRADE_LLM_API_KEY") or not os.environ.get("GRADE_LLM_BASE_URL"):
        return cells
    return cells


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Corrige um JSONL de resultados.")
    parser.add_argument("--results", required=True)
    parser.add_argument("--datasets", default=str(ROOT / "datasets"))
    parser.add_argument("--out", default="")
    parser.add_argument("--llm", action="store_true", help="Não faz nada sem GRADE_LLM_API_KEY. Desligado por padrão.")
    args = parser.parse_args(argv)
    path = Path(args.results)
    if not path.exists():
        print("sem resultados para corrigir")
        return 0
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    judge = bool(args.llm and os.environ.get("GRADE_LLM_API_KEY"))
    if args.llm and not judge:
        print("juiz desligado: falta GRADE_LLM_API_KEY")
    cells = grade_records(records, Path(args.datasets), judge=judge)
    if judge:
        cells = maybe_judge(cells)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as handle:
            for cell in cells:
                handle.write(json.dumps(cell, ensure_ascii=False) + "\n")
    else:
        for cell in cells:
            print(json.dumps(cell, ensure_ascii=False))
    print(f"{len(cells)} células", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
