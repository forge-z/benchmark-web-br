# benchmark-web-br

Public comparison of web tools on Brazilian sites. Three tasks, the same input, the same output schema, no per-tool prompt tuning.

Scoring follows [research-agent-eval](https://github.com/itsyusufahmed/research-agent-eval): each fact is right, wrong, or blank, and the net is right minus wrong. The 95% interval is a bootstrap over items. Rules are in `grade/grading_rules.md`. The long write-up is `METODOLOGIA.md` (Portuguese).

This is the initial skeleton. Dataset gaps are counted. No paid API call was made to build the repo.

## Why Python

Python 3.11, the standard library, and one dependency: `httpx`. CSV, JSONL, HTML, XML, hashing, and the bootstrap stay in the stdlib. Every tool goes through the same HTTP client, so the request body is visible and no vendor SDK is pinned. Tests use `unittest`.

## Licenses

- Code: MIT (`LICENSE`)
- Datasets and results: CC BY 4.0 (`LICENSE-DATA`)
- Third-party page bodies are not redistributed. `snapshots-index/` stores URL, SHA-256, and date

## Layout

| Path | Contents |
|---|---|
| `datasets/` | Sites, queries, URLs, companies. Counts in `datasets/README.md` |
| `runners/` | One runner per tool, plus the HTTP/RSS baseline |
| `grade/` | Deterministic grading, the rules, and the net score |
| `results/` | Empty in git. Format in `results/SCHEMA.md` |
| `snapshots-index/` | Index only. Raw bytes are gitignored |

## Tools

| Runner | Key | Calls |
|---|---|---|
| `baseline` | none | page GET, and RSS when the dataset has a feed |
| `exa` | `EXA_API_KEY` | `POST /search`, `POST /contents` |
| `parallel` | `PARALLEL_API_KEY` | `POST /v1beta/search`, `POST /v1beta/extract` |
| `parallel_task_core` | `PARALLEL_API_KEY` | `POST /v1/tasks/runs` with processor `core`, task 3 only |
| `tinyfish` | `TINYFISH_API_KEY` | search GET and fetch POST |
| `firecrawl` | `FIRECRAWL_API_KEY` | `/v2/search`, `/v2/scrape`, `/v2/extract` |
| `context_dev` | `CONTEXT_DEV_API_KEY` | news search, web search, company search, scrape |

A missing key writes `skipped` and does not open a socket. No Firecrawl Agent, Parallel FindAll, or TinyFish automation/research.

The request is the query, the URL, or the company name plus the ten questions. Answer keys are not sent. The 48-hour window is mapped onto a date filter only where the API has one.

## Reproduce

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m runners.baseline --prova noticias --dry-run --limit 1
```

`--limit` defaults to 1. `--limit 0` walks the whole dataset. CI runs the unit tests on Python 3.11 with no keys and no network.

```bash
python -m runners.exa --prova noticias --limit 1
python -m grade.grade --results results/exa__noticias__<run_id>.jsonl --out results/cells.jsonl
python -m grade.score --cells results/cells.jsonl
```

Result JSONL and `snapshots/` stay out of git. Each call records an estimated credit count and list-price cost. See `runners/costs.py`. An estimate is not an invoice.

## Dataset counts (checked 2026-11-18)

| Dataset | Target | Rows | Checked | Still open |
|---|---:|---:|---:|---:|
| News sites | ~25 | 25 | 25 homepages HTTP 200 (17 with RSS) | 0 |
| pt-BR queries | ~40 | 40 | 40 query strings | 40 have no expected URL, on purpose |
| Page read, news | 20 | 20 | 20 with title and date | 0 |
| Page read, Anfavea PDF | 10 | 10 | 10 URLs opened | field keys open; 4 have a title that was read |
| Page read, product | 30 | 1 | the Kabum URL opened | 29 product URLs are missing |
| Companies | ~30 | 30 | 21 with a cadastral block | 9 |
| Questions | ~10 | 10 | 10 question strings | 0 |

Company LinkedIn, the commercial role, and recent news are empty on every row. Presence bands: 19 rich, 2 medium, 5 thin, 4 still open.

## Open decisions

1. Parallel's current docs point new integrations at `/v1`. Search and extract here stay on `/v1beta`, with `max_chars_total` inside `excerpts`.
2. Firecrawl `/v2/extract` is removed on 2026-12-10. The replacement is JSON scrape, which costs more credits.
3. Context.dev news search has no `br` country. The filter is Portuguese plus the date, so Portugal is in scope.
4. Firecrawl `tbs` does not filter the `news` source. Task 1 uses `web` plus `tbs`.
5. Exa uses `type: auto` (US$ 7 / 1,000 ceiling). `lite` is cheaper.
6. Parallel beta search has no separate price. The estimate uses the v1 advanced ceiling, US$ 5 / 1,000.
7. The 25-site panel does not restrict the search domain. Panel coverage is not a score yet.
8. The task-3 baseline abstains. It is not given the official site, because that would leak the answer.
9. Duplicate URLs are a separate metric, not part of the net. A query with more items weighs more than a query with one.
10. The LLM-judge hook does not send a request. Role and recent-news stay ungraded until a model is wired.
11. 29 product URLs are missing. From this environment the marketplaces did not yield a product link, or did not open.
12. Tupy and Portobello: the CVM city and the BrasilAPI city disagree, so city was left blank.
13. `parallel_task_core` is a separate tool id on task 3. It can stay a reference column instead of joining the ranking.
14. Marketplace prices move. The canonical `R$` form is defined; the price key is still empty.

No personal names, emails, phone numbers, or secrets are stored. A decision-maker, if filled later, is a role, not a person.
