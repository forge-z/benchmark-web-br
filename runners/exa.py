#!/usr/bin/env python3
"""Exa search and contents. No Agent API.

Docs read on 2026-11-18:
- POST https://api.exa.ai/search  (type auto, category news on the news proof)
- POST https://api.exa.ai/contents
Auth: x-api-key from EXA_API_KEY.
"""

from __future__ import annotations

from runners import common, costs, fields

SEARCH = "https://api.exa.ai/search"
CONTENTS = "https://api.exa.ai/contents"
KEY = "EXA_API_KEY"


def _headers() -> dict:
    return {"x-api-key": common.header_key(KEY), "Content-Type": "application/json"}


def _search_body(query: str, ctx, *, category: str | None) -> dict:
    body = {
        "query": query,
        "type": "auto",
        "numResults": 10,
        "contents": {"highlights": True},
    }
    if category:
        body["category"] = category
    if ctx["prova"] == "noticias":
        body["startPublishedDate"] = ctx["window_start"].strftime("%Y-%m-%dT%H:%M:%SZ")
        body["endPublishedDate"] = ctx["window_end"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return body


def _search_cost(notes: str) -> tuple[float, str]:
    # auto search + highlights estimated as one content type on up to 10 results
    cost = costs.EXA_SEARCH_AUTO_USD + 10 * costs.EXA_CONTENTS_TEXT_USD
    return cost, notes


def plan(row, ctx) -> list[dict]:
    if ctx["prova"] == "noticias":
        body = _search_body(row["consulta"], ctx, category="news")
        cost, notes = _search_cost("Busca auto + highlights. category=news e a janela de 48 h são o filtro documentado, não um prompt extra.")
        return [common.call_record("search", "POST", SEARCH, body, credits=None, cost=cost, notes=notes)]
    if ctx["prova"] == "leitura":
        body = {"urls": [row["url"]], "text": True}
        return [common.call_record(
            "contents", "POST", CONTENTS, body, credits=None,
            cost=costs.EXA_CONTENTS_TEXT_USD,
            notes="POST /contents com text. US$ 1 / 1.000 páginas por tipo de conteúdo.",
        )]
    query = row["nome"]
    search = _search_body(query, ctx, category=None)
    search["contents"] = {"highlights": True}
    cost, notes = _search_cost("Busca pelo nome da empresa. Sem category, para não restringir a notícia.")
    contents = {"urls": [], "text": True}
    return [
        common.call_record("search", "POST", SEARCH, search, credits=None, cost=cost, notes=notes),
        common.call_record(
            "contents", "POST", CONTENTS, contents, credits=None,
            cost=3 * costs.EXA_CONTENTS_TEXT_USD,
            notes="Até 3 páginas via /contents. O custo estimado assume 3 URLs.",
        ),
    ]


def _items_from_search(payload: dict) -> list[dict]:
    items = []
    for result in payload.get("results") or []:
        highlights = result.get("highlights") or []
        snippet = " ".join(highlights) if isinstance(highlights, list) else str(highlights or "")
        items.append(fields.news_item(
            result.get("url") or "",
            result.get("title") or "",
            result.get("publishedDate") or result.get("published_date") or "",
            snippet,
        ))
    return items


def _page_from_result(url: str, result: dict) -> dict:
    page = fields.empty_page(url)
    page["title"] = result.get("title") or ""
    page["text"] = (result.get("text") or "")[:20000]
    page["published_at"] = fields.to_iso(result.get("publishedDate") or "") or (result.get("publishedDate") or "")
    page["price_brl"] = fields.canonical_price(page["text"])
    return page


def execute(row, ctx) -> dict:
    planned = plan(row, ctx)
    if ctx["prova"] == "noticias":
        body = planned[0]["request"]
        status, payload, _raw = common.request_json("POST", SEARCH, headers=_headers(), body=body)
        planned[0]["http_status"] = status
        error = "" if status == 200 else f"http {status}"
        return {"output": {"items": _items_from_search(payload)}, "calls": planned, "http_status": status, "error": error}
    if ctx["prova"] == "leitura":
        body = planned[0]["request"]
        status, payload, _raw = common.request_json("POST", CONTENTS, headers=_headers(), body=body)
        planned[0]["http_status"] = status
        results = payload.get("results") or []
        page = _page_from_result(row["url"], results[0] if results else {})
        page["blocked"] = status in {401, 402, 403, 429}
        return {"output": page, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    search_body = {k: v for k, v in planned[0]["request"].items()}
    status, payload, _raw = common.request_json("POST", SEARCH, headers=_headers(), body=search_body)
    planned[0]["http_status"] = status
    urls = [item["url"] for item in _items_from_search(payload) if item["url"]][:3]
    answers = fields.empty_answers()
    text_blob = " ".join(item["snippet"] for item in _items_from_search(payload))
    if urls:
        contents_body = {"urls": urls, "text": True}
        planned[1]["request"] = contents_body
        planned[1]["estimated_cost_usd"] = len(urls) * costs.EXA_CONTENTS_TEXT_USD
        status2, payload2, _raw2 = common.request_json("POST", CONTENTS, headers=_headers(), body=contents_body)
        planned[1]["http_status"] = status2
        chunks = []
        for result in payload2.get("results") or []:
            chunks.append(result.get("text") or "")
            if result.get("url"):
                answers["site"]["citations"].append(result["url"])
        text_blob = "\n".join(chunks)
    _fill_company(answers, text_blob, urls)
    output = {"answers": answers, "mode": "search_extract"}
    error = "" if status == 200 else f"http {status}"
    return {"output": output, "calls": planned, "http_status": status, "error": error}


def _fill_company(answers: dict, text: str, urls: list[str]) -> None:
    cnpj = fields.format_cnpj(text)
    if cnpj and fields.cnpj_valid(cnpj):
        answers["cnpj"]["value"] = cnpj
        answers["cnpj"]["citations"] = urls[:1]
    link = fields.linkedin_company_url(text)
    if link:
        answers["linkedin_empresa"]["value"] = link


def main(argv: list[str] | None = None) -> int:
    return common.run([
        {"tool": "exa", "env_key": KEY, "plan": plan, "execute": execute},
    ], argv)


if __name__ == "__main__":
    raise SystemExit(main())
