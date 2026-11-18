"""CLI, dataset loading, and the JSONL record shared by every runner.

--dry-run never opens a socket. A missing API key skips the tool instead of calling it.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from runners.fields import COMPANY_FIELDS, empty_answers, empty_page

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1"
PROVAS = ("noticias", "leitura", "empresas")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roda uma prova do benchmark-web-br.")
    parser.add_argument("--prova", required=True, choices=PROVAS)
    parser.add_argument("--limit", type=int, default=1, help="Itens a processar. 0 = dataset inteiro. Padrão: 1.")
    parser.add_argument("--dry-run", action="store_true", help="Não chama rede. Grava o pedido que seria enviado.")
    parser.add_argument("--datasets", default=str(ROOT / "datasets"))
    parser.add_argument("--out", default=str(ROOT / "results"))
    parser.add_argument("--snapshots", default=str(ROOT / "snapshots-index"))
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_inputs(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    base = Path(args.datasets)
    perguntas = read_csv(base / "perguntas_empresas.csv")
    if args.prova == "noticias":
        rows = read_csv(base / "consultas_noticias.csv")
    elif args.prova == "leitura":
        rows = read_csv(base / "urls_leitura.csv")
    else:
        rows = read_csv(base / "empresas.csv")
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    return rows, perguntas


def window(hours: int = 48, now: datetime | None = None) -> tuple[datetime, datetime]:
    end = now or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return end - timedelta(hours=hours), end


def task_text(nome: str, perguntas: list[dict]) -> str:
    lines = [
        f"Empresa: {nome}",
        "Responda só com fatos públicos. Se não souber um campo, deixe vazio.",
        "Não inclua nome de pessoa, e-mail ou telefone. No cargo, escreva só o cargo.",
    ]
    for item in perguntas:
        lines.append(f"- {item['campo']}: {item['pergunta']}")
    return "\n".join(lines)


def skeleton(prova: str, url: str = "") -> dict:
    if prova == "noticias":
        return {"items": []}
    if prova == "leitura":
        return empty_page(url)
    return {"answers": empty_answers(), "mode": "search_extract"}


def record(
    *,
    run_id: str,
    prova: str,
    tool: str,
    item_id: str,
    dry_run: bool,
    skipped: bool,
    skip_reason: str,
    started_at: str,
    finished_at: str,
    latency_ms: int,
    http_status: int | None,
    error: str,
    calls: list[dict],
    output: dict,
) -> dict:
    credits = _sum(calls, "estimated_credits")
    cost = _sum(calls, "estimated_cost_usd")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "prova": prova,
        "tool": tool,
        "item_id": item_id,
        "dry_run": dry_run,
        "skipped": skipped,
        "skip_reason": skip_reason,
        "started_at": started_at,
        "finished_at": finished_at,
        "latency_ms": latency_ms,
        "http_status": http_status,
        "error": error,
        "estimated_credits": credits,
        "estimated_cost_usd": cost,
        "calls": calls,
        "output": output,
    }


def _sum(calls: list[dict], key: str):
    total = 0
    seen = False
    for call in calls:
        value = call.get(key)
        if isinstance(value, (int, float)):
            total += value
            seen = True
    return round(total, 6) if seen else None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def request_json(method: str, url: str, *, headers: dict, body: dict | None = None, params: dict | None = None, timeout: float = 45):
    """HTTP JSON. Callers must not put secrets in the URL. Raises on transport errors."""
    import httpx

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.request(method, url, headers=headers, json=body, params=params)
    try:
        payload = response.json()
    except Exception:
        payload = {"_text": response.text[:1000]}
    return response.status_code, payload, response.content


def index_snapshot(directory: Path, *, url: str, body: bytes, tool: str, prova: str, item_id: str) -> None:
    """Store a hash, not the body. Raw bytes go to snapshots/, which is gitignored."""
    import hashlib

    if not body:
        return
    digest = hashlib.sha256(body).hexdigest()
    raw_dir = ROOT / "snapshots"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / digest).write_bytes(body)
    directory.mkdir(parents=True, exist_ok=True)
    line = {
        "url": url,
        "sha256": digest,
        "fetched_at": now_iso(),
        "bytes": len(body),
        "tool": tool,
        "prova": prova,
        "item_id": item_id,
    }
    with (directory / "index.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def run(specs: list[dict], argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows, perguntas = load_inputs(args)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    start_window, end_window = window(48)
    ctx = {
        "prova": args.prova,
        "perguntas": perguntas,
        "window_start": start_window,
        "window_end": end_window,
        "datasets": Path(args.datasets),
        "dry_run": args.dry_run,
        "snapshots": Path(args.snapshots),
    }
    wrote = 0
    for spec in specs:
        if args.prova not in spec.get("provas", PROVAS):
            continue
        tool = spec["tool"]
        env_key = spec.get("env_key")
        missing = bool(env_key) and not os.environ.get(env_key or "")
        path = out_dir / f"{tool}__{args.prova}__{run_id}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                item_id = row["id"]
                started = time.monotonic()
                started_at = now_iso()
                if missing and not args.dry_run:
                    payload = record(
                        run_id=run_id, prova=args.prova, tool=tool, item_id=item_id,
                        dry_run=False, skipped=True, skip_reason=f"sem {env_key}",
                        started_at=started_at, finished_at=now_iso(), latency_ms=0,
                        http_status=None, error="", calls=[], output=skeleton(args.prova, row.get("url", "")),
                    )
                elif args.dry_run:
                    calls = spec["plan"](row, ctx)
                    payload = record(
                        run_id=run_id, prova=args.prova, tool=tool, item_id=item_id,
                        dry_run=True, skipped=False, skip_reason="",
                        started_at=started_at, finished_at=now_iso(), latency_ms=0,
                        http_status=None, error="", calls=calls,
                        output=skeleton(args.prova, row.get("url", "")),
                    )
                else:
                    try:
                        result = spec["execute"](row, ctx)
                        error = result.get("error") or ""
                        status = result.get("http_status")
                        output = result.get("output") or skeleton(args.prova, row.get("url", ""))
                        calls = result.get("calls") or []
                    except Exception as exc:  # a runner bug should not hide the item
                        error = type(exc).__name__
                        status = None
                        output = skeleton(args.prova, row.get("url", ""))
                        calls = []
                    payload = record(
                        run_id=run_id, prova=args.prova, tool=tool, item_id=item_id,
                        dry_run=False, skipped=False, skip_reason="",
                        started_at=started_at, finished_at=now_iso(),
                        latency_ms=int((time.monotonic() - started) * 1000),
                        http_status=status, error=error, calls=calls, output=output,
                    )
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                wrote += 1
        print(f"{tool}: {path} ({len(rows)} itens)", file=sys.stderr)
    return 0 if wrote else 1


def call_record(name: str, method: str, endpoint: str, body: dict | None, *, credits, cost, notes: str, status: int | None = None, latency_ms: int = 0, error: str = "") -> dict:
    return {
        "call": name,
        "method": method,
        "endpoint": endpoint,
        "request": body or {},
        "http_status": status,
        "latency_ms": latency_ms,
        "error": error,
        "estimated_credits": credits,
        "estimated_cost_usd": cost,
        "cost_notes": notes,
    }


def header_key(env_name: str) -> str:
    return os.environ.get(env_name, "")


# Re-exported for runners that build company output.
ANSWER_FIELDS = COMPANY_FIELDS
