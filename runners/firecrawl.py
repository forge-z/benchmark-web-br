#!/usr/bin/env python3
"""Firecrawl search, scrape, and extract. No agent endpoint.

Docs read on 2026-11-18:
- POST https://api.firecrawl.dev/v2/search
- POST https://api.firecrawl.dev/v2/scrape
- POST https://api.firecrawl.dev/v2/extract  (removido em 2026-12-10; ver README)

`tbs` só filtra a fonte web, não a fonte news. A prova 1 usa web + tbs na janela de 48 h.
Auth: Authorization Bearer from FIRECRAWL_API_KEY. Sem chave, a ferramenta é pulada
(não usamos o modo sem chave).
"""

from __future__ import annotations

from runners import common, costs, fields

BASE = "https://api.firecrawl.dev/v2"
KEY = "FIRECRAWL_API_KEY"


def _headers() -> dict:
    return {"Authorization": f"Bearer {common.header_key(KEY)}", "Content-Type": "application/json"}


def _tbs(ctx) -> str:
    start = ctx["window_start"]
    end = ctx["window_end"]
    # The documented custom range uses M/D/YYYY.
    return f"cdr:1,cd_min:{start.month}/{start.day}/{start.year},cd_max:{end.month}/{end.day}/{end.year}"


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {field: {"type": "string"} for field in fields.COMPANY_FIELDS},
    }


def plan(row, ctx) -> list[dict]:
    if ctx["prova"] == "noticias":
        body = {"query": row["consulta"], "limit": 10, "sources": ["web"], "tbs": _tbs(ctx)}
        return [common.call_record(
            "search", "POST", f"{BASE}/search", body,
            credits=costs.FIRECRAWL_SEARCH_CREDITS_PER_10, cost=None,
            notes="2 créditos por 10 resultados. tbs na fonte web, porque a fonte news ignora tbs. USD não fixado: depende do plano.",
        )]
    if ctx["prova"] == "leitura":
        body = {"url": row["url"], "formats": ["markdown"]}
        return [common.call_record(
            "scrape", "POST", f"{BASE}/scrape", body,
            credits=costs.FIRECRAWL_SCRAPE_CREDITS, cost=None,
            notes="1 crédito por página em markdown. Sem JSON, para não somar os 4 créditos do modo LLM.",
        )]
    search = {"query": row["nome"], "limit": 10, "sources": ["web"]}
    extract = {
        "urls": [],
        "prompt": common.task_text(row["nome"], ctx["perguntas"]),
        "schema": _schema(),
        "enableWebSearch": False,
    }
    return [
        common.call_record(
            "search", "POST", f"{BASE}/search", search,
            credits=costs.FIRECRAWL_SEARCH_CREDITS_PER_10, cost=None,
            notes="2 créditos por 10 resultados.",
        ),
        common.call_record(
            "extract", "POST", f"{BASE}/extract", extract,
            credits=None, cost=None,
            notes="Extract cobra por token (1 crédito = 15 tokens). O valor só existe na resposta. Endpoint sai do ar em 2026-12-10.",
        ),
    ]


def _items(payload: dict) -> list[dict]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = []
    if isinstance(data, dict):
        rows = data.get("web") or data.get("news") or []
    elif isinstance(data, list):
        rows = data
    items = []
    for result in rows:
        if not isinstance(result, dict):
            continue
        items.append(fields.news_item(
            result.get("url") or "",
            result.get("title") or "",
            result.get("publishedAt") or result.get("published_at") or "",
            result.get("description") or result.get("markdown") or "",
        ))
    return items


def execute(row, ctx) -> dict:
    planned = plan(row, ctx)
    if ctx["prova"] == "noticias":
        status, payload, _raw = common.request_json("POST", f"{BASE}/search", headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        return {"output": {"items": _items(payload)}, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    if ctx["prova"] == "leitura":
        status, payload, _raw = common.request_json("POST", f"{BASE}/scrape", headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        data = payload.get("data") or {}
        text = data.get("markdown") or ""
        meta = data.get("metadata") or {}
        page = fields.empty_page(row["url"])
        page["title"] = meta.get("title") or ""
        page["text"] = text[:20000]
        page["published_at"] = fields.to_iso(meta.get("publishedTime") or meta.get("article:published_time") or "")
        page["price_brl"] = fields.canonical_price(text)
        page["blocked"] = status in {401, 402, 403, 429} or meta.get("statusCode") in {401, 403, 429}
        return {"output": page, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    status, payload, _raw = common.request_json("POST", f"{BASE}/search", headers=_headers(), body=planned[0]["request"])
    planned[0]["http_status"] = status
    urls = [item["url"] for item in _items(payload) if item["url"]][:3]
    answers = fields.empty_answers()
    if urls:
        body = dict(planned[1]["request"])
        body["urls"] = urls
        planned[1]["request"] = body
        status2, payload2, _raw2 = common.request_json("POST", f"{BASE}/extract", headers=_headers(), body=body, timeout=60)
        planned[1]["http_status"] = status2
        job = payload2.get("id")
        data = payload2.get("data")
        if job and not data:
            status3, payload3, _raw3 = common.request_json("GET", f"{BASE}/extract/{job}", headers=_headers(), timeout=60)
            planned.append(common.call_record(
                "extract_status", "GET", f"{BASE}/extract/{job}", {},
                credits=None, cost=None, notes="Uma leitura do job. Sem loop longo.", status=status3,
            ))
            data = payload3.get("data")
            status2 = status3
        if isinstance(data, dict):
            for field in fields.COMPANY_FIELDS:
                value = data.get(field)
                if isinstance(value, str):
                    answers[field]["value"] = value
                    answers[field]["citations"] = urls[:1]
        credits = payload2.get("creditsUsed") or payload2.get("credits_used")
        if isinstance(credits, int):
            planned[1]["estimated_credits"] = credits
    return {
        "output": {"answers": answers, "mode": "search_extract"},
        "calls": planned, "http_status": status,
        "error": "" if status == 200 else f"http {status}",
    }


def main(argv: list[str] | None = None) -> int:
    return common.run([
        {"tool": "firecrawl", "env_key": KEY, "plan": plan, "execute": execute},
    ], argv)


if __name__ == "__main__":
    raise SystemExit(main())
