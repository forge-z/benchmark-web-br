#!/usr/bin/env python3
"""Firecrawl search and scrape. No agent endpoint, no /extract.

Docs read on 2026-11-18:
- POST https://api.firecrawl.dev/v2/search
- POST https://api.firecrawl.dev/v2/scrape

A prova 3 usa scrape com formats json (schema + prompt) no lugar de /v2/extract,
que sai do ar em 2026-12-10. O JSON custa 4 créditos além do 1 da página.
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
    calls = [common.call_record(
        "search", "POST", f"{BASE}/search", search,
        credits=costs.FIRECRAWL_SEARCH_CREDITS_PER_10, cost=None,
        notes="2 créditos por 10 resultados.",
    )]
    prompt = common.task_text(row["nome"], ctx["perguntas"])
    for _ in range(3):
        body = {
            "url": "",
            "formats": [{"type": "json", "schema": _schema(), "prompt": prompt}],
        }
        calls.append(common.call_record(
            "scrape_json", "POST", f"{BASE}/scrape", body,
            credits=costs.FIRECRAWL_SCRAPE_JSON_CREDITS, cost=None,
            notes=(
                "POST /v2/scrape com formato json. 5 créditos por página (1 do scrape + 4 do JSON). "
                "A URL fica vazia no dry-run e é preenchida com o resultado da busca, até 3 páginas. "
                "Substitui /v2/extract."
            ),
        ))
    return calls


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
    for index, call in enumerate(planned[1:]):
        if index >= len(urls):
            call["estimated_credits"] = 0
            call["cost_notes"] += " Não enviada: a busca devolveu menos de 3 URLs."
            continue
        body = dict(call["request"])
        body["url"] = urls[index]
        call["request"] = body
        status2, payload2, _raw2 = common.request_json("POST", f"{BASE}/scrape", headers=_headers(), body=body, timeout=60)
        call["http_status"] = status2
        data = ((payload2.get("data") or {}).get("json") or {}) if isinstance(payload2, dict) else {}
        if isinstance(data, dict):
            for field in fields.COMPANY_FIELDS:
                value = data.get(field)
                if isinstance(value, str) and value and not answers[field]["value"]:
                    answers[field]["value"] = value
                    answers[field]["citations"] = [urls[index]]
        credits = payload2.get("creditsUsed") or payload2.get("credits_used") if isinstance(payload2, dict) else None
        if isinstance(credits, int):
            call["estimated_credits"] = credits
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
