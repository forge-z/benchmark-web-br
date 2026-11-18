#!/usr/bin/env python3
"""Parallel search, extract, and Task core, all on /v1.

Docs read on 2026-11-18:
- POST /v1/search: search_queries is required; max_chars_total is top-level.
  max_results lives in advanced_settings. Mode omitted: the default is advanced.
- POST /v1/extract: urls is required; full_content lives in advanced_settings.
- POST /v1/tasks/runs: processor core, only on prova 3. output_schema is
  {"type": "json", "json_schema": {...}}.

No beta header. No FindAll.
"""

from __future__ import annotations

from runners import common, costs, fields

BASE = "https://api.parallel.ai"
SEARCH = f"{BASE}/v1/search"
EXTRACT = f"{BASE}/v1/extract"
TASKS = f"{BASE}/v1/tasks/runs"
KEY = "PARALLEL_API_KEY"
MAX_CHARS = 8000


def _headers() -> dict:
    return {"x-api-key": common.header_key(KEY), "Content-Type": "application/json"}


def _objective(row, ctx) -> str:
    if ctx["prova"] == "noticias":
        return row["consulta"]
    if ctx["prova"] == "leitura":
        return "Extrair título, data, preço em reais, vendedor e disponibilidade desta página."
    return common.task_text(row["nome"], ctx["perguntas"])


def _search_body(objective: str, query: str) -> dict:
    return {
        "objective": objective,
        "search_queries": [query],
        "max_chars_total": MAX_CHARS,
        "advanced_settings": {"max_results": 10},
    }


def plan_search(row, ctx) -> list[dict]:
    notes = (
        "POST /v1/search. max_chars_total no topo; max_results em advanced_settings. "
        "Modo omitido: o padrão documentado é advanced, US$ 5 / 1.000."
    )
    if ctx["prova"] == "noticias":
        body = _search_body(row["consulta"], row["consulta"])
        return [common.call_record("search", "POST", SEARCH, body, credits=None, cost=costs.PARALLEL_SEARCH_CEILING_USD, notes=notes)]
    if ctx["prova"] == "leitura":
        body = {
            "urls": [row["url"]],
            "objective": _objective(row, ctx),
            "max_chars_total": MAX_CHARS,
            "advanced_settings": {"full_content": True},
        }
        return [common.call_record(
            "extract", "POST", EXTRACT, body, credits=None,
            cost=costs.PARALLEL_EXTRACT_USD,
            notes="POST /v1/extract. full_content fica em advanced_settings. Preço de lista: US$ 1 / 1.000 URLs.",
        )]
    body = _search_body(_objective(row, ctx), row["nome"])
    extract = {
        "urls": [],
        "objective": _objective(row, ctx),
        "max_chars_total": MAX_CHARS,
    }
    return [
        common.call_record("search", "POST", SEARCH, body, credits=None, cost=costs.PARALLEL_SEARCH_CEILING_USD, notes=notes),
        common.call_record(
            "extract", "POST", EXTRACT, extract, credits=None,
            cost=3 * costs.PARALLEL_EXTRACT_USD,
            notes="Até 3 URLs. Custo estimado assume 3.",
        ),
    ]


def plan_task(row, ctx) -> list[dict]:
    body = {
        "processor": "core",
        "input": common.task_text(row["nome"], ctx["perguntas"]),
        "task_spec": {
            "output_schema": {
                "type": "json",
                "json_schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {field: {"type": "string"} for field in fields.COMPANY_FIELDS},
                },
            }
        },
    }
    return [common.call_record(
        "task", "POST", TASKS, body, credits=None,
        cost=costs.PARALLEL_TASK_CORE_USD,
        notes="Task processor core, US$ 25 / 1.000 execuções concluídas. Falha não é cobrada; se a chamada falhar o custo realizado deve ser lido como zero.",
    )]


def _items(payload: dict) -> list[dict]:
    items = []
    for result in payload.get("results") or []:
        excerpts = result.get("excerpts") or []
        snippet = " ".join(excerpts) if isinstance(excerpts, list) else str(excerpts or "")
        items.append(fields.news_item(
            result.get("url") or "",
            result.get("title") or "",
            result.get("publish_date") or "",
            snippet,
        ))
    return items


def _apply_text(answers: dict, text: str, urls: list[str]) -> None:
    cnpj = fields.format_cnpj(text)
    if cnpj and fields.cnpj_valid(cnpj):
        answers["cnpj"]["value"] = cnpj
        answers["cnpj"]["citations"] = urls[:1]
    link = fields.linkedin_company_url(text)
    if link:
        answers["linkedin_empresa"]["value"] = link
        answers["linkedin_empresa"]["citations"] = urls[:1]


def execute_search(row, ctx) -> dict:
    planned = plan_search(row, ctx)
    if ctx["prova"] == "noticias":
        status, payload, _raw = common.request_json("POST", SEARCH, headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        return {"output": {"items": _items(payload)}, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    if ctx["prova"] == "leitura":
        status, payload, _raw = common.request_json("POST", EXTRACT, headers=_headers(), body=planned[0]["request"])
        planned[0]["http_status"] = status
        results = payload.get("results") or []
        first = results[0] if results else {}
        text = first.get("full_content") or " ".join(first.get("excerpts") or [])
        page = fields.empty_page(row["url"])
        page["title"] = first.get("title") or ""
        page["text"] = (text or "")[:20000]
        page["published_at"] = fields.to_iso(first.get("publish_date") or "")
        page["price_brl"] = fields.canonical_price(page["text"])
        page["blocked"] = status in {401, 402, 403, 429}
        return {"output": page, "calls": planned, "http_status": status, "error": "" if status == 200 else f"http {status}"}
    status, payload, _raw = common.request_json("POST", SEARCH, headers=_headers(), body=planned[0]["request"])
    planned[0]["http_status"] = status
    found = _items(payload)
    urls = [item["url"] for item in found if item["url"]][:3]
    answers = fields.empty_answers()
    blob = " ".join(item["snippet"] for item in found)
    if urls:
        body = dict(planned[1]["request"])
        body["urls"] = urls
        planned[1]["request"] = body
        planned[1]["estimated_cost_usd"] = len(urls) * costs.PARALLEL_EXTRACT_USD
        status2, payload2, _raw2 = common.request_json("POST", EXTRACT, headers=_headers(), body=planned[1]["request"])
        planned[1]["http_status"] = status2
        chunks = []
        for result in payload2.get("results") or []:
            chunks.append(result.get("full_content") or " ".join(result.get("excerpts") or []))
        blob = "\n".join(chunks)
    _apply_text(answers, blob, urls)
    return {
        "output": {"answers": answers, "mode": "search_extract"},
        "calls": planned, "http_status": status,
        "error": "" if status == 200 else f"http {status}",
    }


def execute_task(row, ctx) -> dict:
    planned = plan_task(row, ctx)
    status, payload, _raw = common.request_json("POST", TASKS, headers=_headers(), body=planned[0]["request"])
    planned[0]["http_status"] = status
    run_id = payload.get("run_id") or ""
    answers = fields.empty_answers()
    error = "" if status in {200, 202} else f"http {status}"
    if run_id:
        result_url = f"{TASKS}/{run_id}/result"
        status2, payload2, _raw2 = common.request_json(
            "GET", result_url, headers=_headers(), params={"timeout": 60}, timeout=70,
        )
        planned.append(common.call_record(
            "task_result", "GET", result_url, {"timeout": 60},
            credits=None, cost=0,
            notes="A leitura do resultado não tem preço próprio. timeout=60.",
            status=status2,
        ))
        content = ((payload2.get("output") or {}).get("content") or {})
        if isinstance(content, dict):
            for field in fields.COMPANY_FIELDS:
                value = content.get(field)
                if isinstance(value, str):
                    answers[field]["value"] = value
        basis = ((payload2.get("output") or {}).get("basis") or [])
        if isinstance(basis, list):
            for item in basis:
                field = item.get("field") if isinstance(item, dict) else None
                citations = item.get("citations") if isinstance(item, dict) else None
                if field in answers and isinstance(citations, list):
                    answers[field]["citations"] = [c.get("url") for c in citations if isinstance(c, dict) and c.get("url")]
        if status2 != 200:
            error = f"resultado http {status2}"
            planned[0]["estimated_cost_usd"] = 0
            planned[0]["cost_notes"] += " Chamada sem resultado 200: custo estimado zerado (falha não é cobrada)."
    return {"output": {"answers": answers, "mode": "task_core"}, "calls": planned, "http_status": status, "error": error}


def main(argv: list[str] | None = None) -> int:
    return common.run([
        {"tool": "parallel", "env_key": KEY, "plan": plan_search, "execute": execute_search},
        {"tool": "parallel_task_core", "env_key": KEY, "plan": plan_task, "execute": execute_task, "provas": ("empresas",)},
    ], argv)


if __name__ == "__main__":
    raise SystemExit(main())
