#!/usr/bin/env python3
"""TinyFish search and fetch. No automation and no research API.

Docs read on 2026-11-18:
- GET https://api.search.tinyfish.ai
- POST https://api.fetch.tinyfish.ai
Auth: X-API-Key from TINYFISH_API_KEY.
Search is free up to 12,000 requests/day. Fetch is free up to 1,000 URLs/day.
"""

from __future__ import annotations

from urllib.parse import urlencode

from runners import common, costs, fields

SEARCH = "https://api.search.tinyfish.ai"
FETCH = "https://api.fetch.tinyfish.ai"
KEY = "TINYFISH_API_KEY"


def _headers() -> dict:
    return {"X-API-Key": common.header_key(KEY)}


def _search_params(query: str, ctx) -> dict:
    params = {
        "query": query,
        "location": "BR",
        "language": "pt",
    }
    if ctx["prova"] == "noticias":
        params["domain_type"] = "news"
        params["recency_minutes"] = 48 * 60
    return params


def plan(row, ctx) -> list[dict]:
    search_notes = (
        f"GET / search. Cota documentada: {costs.TINYFISH_SEARCH_FREE_PER_DAY} pedidos/dia sem cobrança. "
        "Acima disso a carteira é debitada; o preço fora da cota não está fixado aqui. Custo estimado 0 dentro da cota."
    )
    fetch_notes = (
        f"POST fetch, format=markdown. Cota documentada: {costs.TINYFISH_FETCH_FREE_URLS_PER_DAY} URLs/dia. "
        "Custo estimado 0 dentro da cota."
    )
    if ctx["prova"] == "noticias":
        params = _search_params(row["consulta"], ctx)
        return [common.call_record("search", "GET", SEARCH + "?" + urlencode(params), params, credits=0, cost=0, notes=search_notes)]
    if ctx["prova"] == "leitura":
        body = {"urls": [row["url"]], "format": "markdown"}
        return [common.call_record("fetch", "POST", FETCH, body, credits=0, cost=0, notes=fetch_notes)]
    params = _search_params(row["nome"], ctx)
    return [
        common.call_record("search", "GET", SEARCH + "?" + urlencode(params), params, credits=0, cost=0, notes=search_notes),
        common.call_record(
            "fetch", "POST", FETCH,
            {"urls": [], "format": "markdown"},
            credits=0, cost=0, notes=fetch_notes,
        ),
    ]


def _items(payload: dict) -> list[dict]:
    items = []
    for result in payload.get("results") or []:
        published = result.get("published_date") or result.get("date") or result.get("published_at") or ""
        items.append(fields.news_item(
            result.get("url") or "",
            result.get("title") or "",
            str(published),
            result.get("snippet") or "",
        ))
    return items


def execute(row, ctx) -> dict:
    planned = plan(row, ctx)
    if ctx["prova"] == "noticias":
        status, payload, _raw = common.request_json("GET", SEARCH, headers=_headers(), params=planned[0]["request"])
        planned[0]["http_status"] = status
        return {"output": {"items": _items(payload)}, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    if ctx["prova"] == "leitura":
        status, payload, _raw = common.request_json("POST", FETCH, headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        results = payload.get("results") or []
        first = results[0] if results else {}
        text = first.get("text") or ""
        page = fields.empty_page(row["url"])
        page["title"] = first.get("title") or ""
        page["text"] = text[:20000]
        page["price_brl"] = fields.canonical_price(text)
        page["blocked"] = status in {401, 402, 403, 429} or bool(first.get("error"))
        return {"output": page, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    params = {k: v for k, v in planned[0]["request"].items()}
    status, payload, _raw = common.request_json("GET", SEARCH, headers=_headers(), params=params)
    planned[0]["http_status"] = status
    found = _items(payload)
    urls = [item["url"] for item in found if item["url"]][:3]
    answers = fields.empty_answers()
    blob = " ".join(item["snippet"] for item in found)
    if urls:
        body = {"urls": urls, "format": "markdown"}
        planned[1]["request"] = body
        status2, payload2, _raw2 = common.request_json("POST", FETCH, headers=_headers(), body=body)
        planned[1]["http_status"] = status2
        chunks = [item.get("text") or "" for item in (payload2.get("results") or [])]
        blob = "\n".join(chunks)
    cnpj = fields.format_cnpj(blob)
    if cnpj and fields.cnpj_valid(cnpj):
        answers["cnpj"]["value"] = cnpj
        answers["cnpj"]["citations"] = urls[:1]
    link = fields.linkedin_company_url(blob)
    if link:
        answers["linkedin_empresa"]["value"] = link
    return {
        "output": {"answers": answers, "mode": "search_extract"},
        "calls": planned, "http_status": status,
        "error": "" if status == 200 else f"http {status}",
    }


def main(argv: list[str] | None = None) -> int:
    return common.run([
        {"tool": "tinyfish", "env_key": KEY, "plan": plan, "execute": execute},
    ], argv)


if __name__ == "__main__":
    raise SystemExit(main())
