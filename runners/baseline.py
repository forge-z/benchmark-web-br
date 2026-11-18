#!/usr/bin/env python3
"""Baseline: HTTP direto e RSS público. Sem chave, custo zero.

Na prova 3 o baseline não recebe o site do gabarito, então abstém.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

from runners import common, fields

STOP = {
    "ULTIMAS", "HORAS", "SOBRE", "PARA", "PELA", "PELO", "COMO", "MAIS", "NAS", "NOS",
    "UMA", "UNS", "NOTICIAS", "NOTICIADO", "NOTICIADOS", "NOTICIADA", "BRASIL",
    "BRASILEIRA", "BRASILEIRAS", "BRASILEIRO", "NOVAS", "NOVO", "NOVA", "COM", "SEM",
    "DOS", "DAS", "QUE", "POR", "ENTRE", "DESDE",
}


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title: list[str] = []
        self._skip = 0
        self._in_title = False
        self.metas: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        ad = {k.lower(): v for k, v in attrs}
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (ad.get("property") or ad.get("name") or "").lower()
            content = ad.get("content") or ""
            if key and content:
                self.metas.append((key, content))

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title.append(data)
        elif data.strip():
            self.parts.append(data.strip())


def _feeds(ctx) -> list[str]:
    path = Path(ctx["datasets"]) / "sites_noticias.csv"
    return [row["rss_url"] for row in common.read_csv(path) if row.get("rss_url")]


def _tokens(query: str) -> list[str]:
    words = [w for w in fields.fold(query).split() if len(w) >= 4 and w not in STOP]
    return words


def plan_news(row, ctx) -> list[dict]:
    feeds = _feeds(ctx)
    return [common.call_record(
        "rss", "GET", "rss",
        {"feeds": feeds, "consulta": row["consulta"], "janela_horas": 48},
        credits=0, cost=0,
        notes="RSS público dos sites do painel. Custo de API zero.",
    )]


def plan_page(row, ctx) -> list[dict]:
    return [common.call_record(
        "fetch", "GET", row["url"], {"url": row["url"]},
        credits=0, cost=0, notes="HTTP direto. Custo de API zero.",
    )]


def plan_company(row, ctx) -> list[dict]:
    return [common.call_record(
        "baseline", "NONE", "",
        {"nome": row["nome"], "motivo": "sem URL de partida; o site do gabarito não entra no pedido"},
        credits=0, cost=0,
        notes="O baseline da prova 3 abstém. Não recebe o site esperado.",
    )]


def plan(row, ctx):
    return {"noticias": plan_news, "leitura": plan_page, "empresas": plan_company}[ctx["prova"]](row, ctx)


def _parse_feed(body: bytes) -> list[dict]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    items = []
    for node in root.iter():
        tag = node.tag.lower().split("}")[-1]
        if tag not in {"item", "entry"}:
            continue
        title = link = published = snippet = ""
        for child in list(node):
            name = child.tag.lower().split("}")[-1]
            text = "".join(child.itertext()).strip()
            if name == "title":
                title = text
            elif name == "link":
                href = child.attrib.get("href") or text
                if href.startswith("http"):
                    link = href
            elif name in {"pubdate", "published", "updated"} and text:
                published = text
            elif name in {"description", "summary"} and text and not snippet:
                snippet = text[:300]
        if link and title:
            items.append(fields.news_item(link, title, published, snippet))
    return items


def _load_feeds(ctx) -> list[dict]:
    cache = ctx.setdefault("_rss_items", None)
    if cache is not None:
        return cache
    items: list[dict] = []
    for url in _feeds(ctx):
        try:
            status, _payload, body = common.request_json("GET", url, headers={"User-Agent": "benchmark-web-br/0.1", "Accept": "application/rss+xml, application/xml, text/xml"})
        except Exception:
            continue
        if status == 200:
            items.extend(_parse_feed(body))
    ctx["_rss_items"] = items
    return items


def execute_news(row, ctx) -> dict:
    tokens = _tokens(row["consulta"])
    start, end = ctx["window_start"], ctx["window_end"]
    kept = []
    for item in _load_feeds(ctx):
        when = fields.parse_datetime(item["published_at"])
        if when is None or not (start <= when <= end):
            continue
        hay = fields.fold(item["title"] + " " + item["snippet"])
        if tokens and not any(token in hay for token in tokens):
            continue
        kept.append(item)
        if len(kept) >= 10:
            break
    call = plan_news(row, ctx)[0]
    call["http_status"] = 200
    return {"output": {"items": kept}, "calls": [call], "http_status": 200, "error": ""}


def execute_page(row, ctx) -> dict:
    url = row["url"]
    try:
        status, _payload, body = common.request_json(
            "GET", url,
            headers={"User-Agent": "benchmark-web-br/0.1", "Accept": "text/html,application/pdf,*/*"},
            timeout=30,
        )
    except Exception as exc:
        call = plan_page(row, ctx)[0]
        call["error"] = type(exc).__name__
        page = fields.empty_page(url)
        page["blocked"] = True
        return {"output": page, "calls": [call], "http_status": None, "error": type(exc).__name__}
    common.index_snapshot(ctx["snapshots"], url=url, body=body, tool="baseline", prova="leitura", item_id=row["id"])
    text = body.decode("utf-8", "replace")
    parser = _Text()
    try:
        parser.feed(text)
    except Exception:
        pass
    page = fields.empty_page(url)
    page["title"] = " ".join(parser.title).strip()[:300]
    page["text"] = "\n".join(parser.parts)[:20000]
    page["price_brl"] = fields.canonical_price(text)
    page["blocked"] = status in {401, 403, 429, 503} or "captcha" in text.lower()
    for key, content in parser.metas:
        if key in {"article:published_time", "pubdate", "date"} and not page["published_at"]:
            page["published_at"] = fields.to_iso(content) or content
    call = plan_page(row, ctx)[0]
    call["http_status"] = status
    return {"output": page, "calls": [call], "http_status": status, "error": ""}


def execute_company(row, ctx) -> dict:
    output = fields.empty_answers()
    return {
        "output": {"answers": output, "mode": "baseline"},
        "calls": plan_company(row, ctx),
        "http_status": None,
        "error": "",
    }


def execute(row, ctx):
    return {"noticias": execute_news, "leitura": execute_page, "empresas": execute_company}[ctx["prova"]](row, ctx)


def main(argv: list[str] | None = None) -> int:
    return common.run([
        {"tool": "baseline", "env_key": None, "plan": plan, "execute": execute},
    ], argv)


if __name__ == "__main__":
    raise SystemExit(main())
