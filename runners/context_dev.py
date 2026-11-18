#!/usr/bin/env python3
"""Context.dev scrape, web search, news search, and company search.

Docs read on 2026-11-18: https://docs.context.dev
Auth: Authorization Bearer from CONTEXT_DEV_API_KEY.

News search has no publisher country `br`. The news proof filters articleLanguage=pt
and the 48 h window. Authors are not copied into the result.
"""

from __future__ import annotations

from runners import common, costs, fields

BASE = "https://api.context.dev/v1"
KEY = "CONTEXT_DEV_API_KEY"


def _headers() -> dict:
    return {"Authorization": f"Bearer {common.header_key(KEY)}", "Content-Type": "application/json"}


def _ms(moment) -> int:
    return int(moment.timestamp() * 1000)


def plan(row, ctx) -> list[dict]:
    if ctx["prova"] == "noticias":
        body = {
            "searchBy": {"type": "natural_language", "query": row["consulta"]},
            "filterBy": {
                "articleLanguage": ["pt"],
                "date": {"from": _ms(ctx["window_start"]), "to": _ms(ctx["window_end"])},
            },
            "limit": 10,
        }
        return [common.call_record(
            "news_search", "POST", f"{BASE}/news/search", body,
            credits=costs.CONTEXT_NEWS_CREDITS_PER_10, cost=None,
            notes="1 crédito por 10 resultados. sourceCountry não tem br; o filtro é idioma pt mais a janela. USD por crédito não publicado.",
        )]
    if ctx["prova"] == "leitura":
        body = {"url": row["url"], "formats": {"markdown": True}}
        return [common.call_record(
            "scrape", "POST", f"{BASE}/web/scrape", body,
            credits=costs.CONTEXT_SCRAPE_CREDITS, cost=None,
            notes="1 crédito por scrape em markdown, sem JSON nem product (esses somam créditos).",
        )]
    query = row["nome"]
    return [
        common.call_record(
            "web_search", "POST", f"{BASE}/web/search",
            {"query": query, "numResults": 10, "country": "br"},
            credits=costs.CONTEXT_WEB_SEARCH_CREDITS_PER_10, cost=None,
            notes="1 crédito por 10 resultados.",
        ),
        common.call_record(
            "company_search", "POST", f"{BASE}/company/search",
            {"query": query, "mode": "fast"},
            credits=costs.CONTEXT_COMPANY_SEARCH_FAST_CREDITS, cost=None,
            notes="2 créditos por página no modo fast. ultra não é usado.",
        ),
        common.call_record(
            "news_search", "POST", f"{BASE}/news/search",
            {"searchBy": {"type": "natural_language", "query": query}, "filterBy": {"articleLanguage": ["pt"]}, "limit": 5},
            credits=costs.CONTEXT_NEWS_CREDITS_PER_10, cost=None,
            notes="Notícia recente da prova 3. 1 crédito por 10 resultados; aqui o limite é 5.",
        ),
        common.call_record(
            "scrape", "POST", f"{BASE}/web/scrape",
            {"url": "", "formats": {"markdown": True}},
            credits=costs.CONTEXT_SCRAPE_CREDITS, cost=None,
            notes="Um scrape da primeira URL. 1 crédito.",
        ),
    ]


def _news_items(payload: dict) -> list[dict]:
    items = []
    for article in payload.get("data") or []:
        if not isinstance(article, dict):
            continue
        # authors is personal data and is dropped on purpose
        items.append(fields.news_item(
            article.get("url") or "",
            article.get("title") or "",
            article.get("published_at") or "",
            article.get("description") or "",
        ))
    return items


def _web_items(payload: dict) -> list[dict]:
    data = payload.get("data") or payload.get("results") or []
    items = []
    if isinstance(data, dict):
        data = data.get("results") or data.get("web") or []
    for result in data:
        if not isinstance(result, dict):
            continue
        items.append(fields.news_item(
            result.get("url") or "",
            result.get("title") or "",
            result.get("published_at") or result.get("publishedAt") or "",
            result.get("description") or result.get("snippet") or "",
        ))
    return items


def _company_fill(answers: dict, payload: dict, nome: str) -> None:
    data = payload.get("data") or payload.get("results") or []
    if isinstance(data, dict):
        data = data.get("companies") or data.get("results") or []
    target = fields.fold(nome)
    for company in data:
        if not isinstance(company, dict):
            continue
        if target and target not in fields.fold(company.get("name") or ""):
            continue
        domain = company.get("domain") or ""
        if domain and not answers["site"]["value"]:
            answers["site"]["value"] = domain if domain.startswith("http") else f"https://{domain}"
        hq = company.get("headquarters") or {}
        city = hq.get("city") if isinstance(hq, dict) else ""
        if city and not answers["cidade"]["value"]:
            answers["cidade"]["value"] = city
        socials = company.get("socials") or {}
        link = ""
        if isinstance(socials, dict):
            link = fields.linkedin_company_url(socials.get("linkedin") or "")
        if not link:
            link = fields.linkedin_company_url(str(company.get("linkedin") or ""))
        if link:
            answers["linkedin_empresa"]["value"] = link
        break


def _page_meta(payload: dict) -> tuple[str, str]:
    """Title and publish date from the scrape `metadata` (title, openGraph, publishedTime, JSON-LD)."""
    meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    og = meta.get("openGraph") if isinstance(meta.get("openGraph"), dict) else {}
    title = meta.get("title") or og.get("title") or ""
    published = meta.get("publishedTime") or og.get("article:published_time") or ""
    if not published:
        blocks = meta.get("jsonLd") if isinstance(meta.get("jsonLd"), list) else []
        stack = list(blocks)
        while stack and not published:
            item = stack.pop(0)
            if isinstance(item, dict):
                published = item.get("datePublished") or ""
                stack.extend(item.get("@graph") or [])
    return str(title).strip(), fields.to_iso(str(published)) if published else ""


def execute(row, ctx) -> dict:
    planned = plan(row, ctx)
    if ctx["prova"] == "noticias":
        status, payload, _raw = common.request_json("POST", f"{BASE}/news/search", headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        return {"output": {"items": _news_items(payload)}, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    if ctx["prova"] == "leitura":
        status, payload, _raw = common.request_json("POST", f"{BASE}/web/scrape", headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        markdown = ((payload.get("markdown") or {}) if isinstance(payload.get("markdown"), dict) else {})
        text = markdown.get("data") or ""
        if not text and isinstance(payload.get("data"), dict):
            text = payload["data"].get("markdown") or ""
        page = fields.empty_page(row["url"])
        page["title"], page["published_at"] = _page_meta(payload)
        page["text"] = (text or "")[:20000]
        page["price_brl"] = fields.canonical_price(page["text"])
        page["blocked"] = status in {401, 402, 403, 429}
        return {"output": page, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    answers = fields.empty_answers()
    status, web_payload, _raw = common.request_json("POST", f"{BASE}/web/search", headers=_headers(), body=planned[0]["request"])
    planned[0]["http_status"] = status
    found = _web_items(web_payload)
    urls = [item["url"] for item in found if item["url"]][:1]
    status_c, company_payload, _raw_c = common.request_json("POST", f"{BASE}/company/search", headers=_headers(), body=planned[1]["request"])
    planned[1]["http_status"] = status_c
    _company_fill(answers, company_payload, row["nome"])
    status_n, news_payload, _raw_n = common.request_json("POST", f"{BASE}/news/search", headers=_headers(), body=planned[2]["request"])
    planned[2]["http_status"] = status_n
    news = _news_items(news_payload)
    if news:
        first = news[0]
        answers["noticia_recente"]["value"] = " | ".join(part for part in (first["title"], first["url"], first["published_at"]) if part)
        if first["url"]:
            answers["noticia_recente"]["citations"] = [first["url"]]
    if urls:
        body = {"url": urls[0], "formats": {"markdown": True}}
        planned[3]["request"] = body
        status_s, scrape_payload, _raw_s = common.request_json("POST", f"{BASE}/web/scrape", headers=_headers(), body=body)
        planned[3]["http_status"] = status_s
        markdown = scrape_payload.get("markdown") if isinstance(scrape_payload.get("markdown"), dict) else {}
        text = (markdown or {}).get("data") or ""
        cnpj = fields.format_cnpj(text)
        if cnpj and fields.cnpj_valid(cnpj):
            answers["cnpj"]["value"] = cnpj
            answers["cnpj"]["citations"] = urls
    error = "" if status == 200 else f"http {status}"
    return {"output": {"answers": answers, "mode": "search_extract"}, "calls": planned, "http_status": status, "error": error}


def main(argv: list[str] | None = None) -> int:
    return common.run([
        {"tool": "context_dev", "env_key": KEY, "plan": plan, "execute": execute},
    ], argv)


if __name__ == "__main__":
    raise SystemExit(main())
