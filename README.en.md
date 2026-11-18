# benchmark-web-br

Public comparison of web tools on Brazilian sites. Three tasks, the same input, the same output schema, no per-tool prompt tuning.

Scoring follows [research-agent-eval](https://github.com/itsyusufahmed/research-agent-eval): each fact is right, wrong, or blank, and the net is right minus wrong. The 95% interval is a bootstrap over items. Rules are in `grade/grading_rules.md`. The long write-up is `METHODOLOGY.md`.

This is the initial skeleton. Dataset gaps are counted. No paid API call was made to build the repo.

## Round 1

Scores from 2026-11-18 are in [`results/round-1-2026-11-18/`](results/round-1-2026-11-18/SUMMARY.md). Net = right − wrong per 100 cells, in points from −100 to 100, with a 95% interval. Parentheses mark a sample smaller than the dataset. Exa, TinyFish, and Parallel (including Task) ran on paid accounts. Firecrawl and Context.dev used free-plan credit. Round deviations are in `METHODOLOGY.md`, section "Round 1".

| Tool | News | Reading | Companies |
|---|---:|---:|---:|
| baseline | 98.4 [96.4; 99.7] | 24.3 [8.8; 40.4] | 0.0 [0.0; 0.0] |
| exa | 100.0 [100.0; 100.0] | 33.9 [18.0; 50.0] | 0.5 [0.0; 1.5] |
| parallel | -45.8 [-60.0; -29.8] | 37.4 [21.1; 53.2] | 10.1 [6.3; 13.3] |
| parallel_task_core | — | — | 87.4 [76.3; 95.2] |
| tinyfish | -45.3 [-63.4; -22.7] | 13.9 [3.5; 23.7] | 0.5 [0.0; 1.5] |
| firecrawl | 0.0 [0.0; 0.0] | 21.7 [7.6; 36.5] | -7.1 [-26.2; 11.9] (12/30) |
| context_dev | 100.0 [100.0; 100.0] | 33.9 [17.6; 50.0] | 10.0 [2.4; 17.0] (24/30) |

### Caveats

1. Unequal samples in the Companies column. Firecrawl ran 12 of 30 and Context.dev ran 24 of 30. Those two nets are not directly comparable to tools that ran all 30. News (40 queries) and reading (60 URLs) have one row per item.
2. The net is in points, not a percentage. It is the percent right minus the percent wrong, on a scale from −100 to 100.
3. One round, no repeats: 40 queries, 60 URLs, 30 companies. A gap of a few points can be noise.
4. Each tool ran through a runner in this repo, not necessarily in the vendor's best setup. The number measures tool plus runner. Exa reached 100 on news with the full API (`/search` and `/contents`, with `category: news` and the date window); the earlier run was discarded. Context.dev reading went from −1.7 to 33.9 after the runner was fixed, with no new calls.
5. Parallel Task is a research agent, with a median of 2.4 minutes per company. It is not comparable to the search and extraction tools, which finish in seconds. That is why the row is separate.
6. Low-cost next step: finish the 18 missing Firecrawl companies and the 6 missing Context.dev companies when there is credit.

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
| `results/` | Round 1 in `results/round-1-2026-11-18/`. Format in `results/SCHEMA.md`. Loose JSONL (`results/*.jsonl`) stays out of git |
| `snapshots-index/` | Index only. Raw bytes are gitignored |
| `METHODOLOGY.md` | What is measured, how, and what a round does not support |

## Tools

| Runner | Key | Calls |
|---|---|---|
| `baseline` | none | page GET, and RSS when the dataset has a feed |
| `exa` | `EXA_API_KEY` | `POST /search`, `POST /contents` |
| `parallel` | `PARALLEL_API_KEY` | `POST /v1/search`, `POST /v1/extract` |
| `parallel_task_core` | `PARALLEL_API_KEY` | `POST /v1/tasks/runs` with processor `core`, task 3 only |
| `tinyfish` | `TINYFISH_API_KEY` | search GET and fetch POST |
| `firecrawl` | `FIRECRAWL_API_KEY` | `/v2/search`, `/v2/scrape` (markdown for pages, JSON for task 3) |
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

Loose JSONL in `results/*.jsonl` and `snapshots/` stay out of git. Round 1, with third-party text already removed, is in `results/round-1-2026-11-18/`. Each call records an estimated credit count and list-price cost. See `runners/costs.py`. An estimate is not an invoice.

## Dataset counts (checked 2026-11-18)

| Dataset | Target | Rows | Checked | Still open |
|---|---:|---:|---:|---:|
| News sites | ~25 | 25 | 25 homepages HTTP 200 (17 with RSS) | 0 |
| pt-BR queries | ~40 | 40 | 40 query strings | 40 have no expected URL, on purpose |
| Page read, news | 20 | 20 | 20 with title and date | 0 |
| Page read, Anfavea PDF | 10 | 10 | 10 URLs opened | field keys open; 4 have a title that was read |
| Page read, product | 30 | 30 | 26 with a title (Kabum, Mercado Livre, Amazon, Casas Bahia, Americanas, Magalu) | 4 Shopee URLs unread; 1 Shopee URL still missing |
| Companies | ~30 | 30 | 29 with the head-office cadastral block | 1 (KSC Ferramentas, no CNPJ) |
| Questions | ~10 | 10 | 10 question strings | 0 |

The answer key CNPJ is the head office on BrasilAPI (`descricao_identificador_matriz_filial`). A `/0001` suffix does not prove that. Tupy, Romi, and Randoncorp were switched from a branch to the head office. Company LinkedIn is filled on three rows, only `/company/` URLs. The commercial role is filled only for Kennatech, as a public title, with no personal name. Recent news is still empty. Presence bands: 25 rich, 2 medium, 1 thin, 2 still open. When the CVM city disagrees with BrasilAPI, the key uses BrasilAPI. Portobello stays TIJUCAS/SC. Tupy's head office is JOINVILLE/SC.

Scoring is automatic only. There is no LLM judge. `python -m grade.amostra` draws a reproducible sample (`--seed`, default `20261118`) and writes a CSV with empty `revisao_humana` and `comentario` columns.

## Open decisions

1. Context.dev news search has no `br` country. The filter is Portuguese plus the date, so Portugal is in scope.
2. Firecrawl `tbs` does not filter the `news` source. Task 1 uses `web` plus `tbs`.
3. Exa uses `type: auto` (US$ 7 / 1,000 ceiling). `lite` is cheaper and lowers the cost.
4. The 25-site panel does not restrict the search domain. Panel coverage is not a score yet.
5. The task-3 baseline abstains. It is not given the official site, because that would leak the answer.
6. Duplicate URLs are a separate metric, not part of the net. A query with more items weighs more than a query with one.
7. KSC Ferramentas still has no CNPJ. Two active Joinville registrations have similar names, and neither was tied to the site.
8. Shopee: 4 URLs are listed, none of the pages were read, and 1 URL is still missing to reach 5. On several verified product rows, price, seller, or availability stayed empty.
9. `parallel_task_core` is a separate tool id on task 3. It can stay a reference column instead of joining the ranking.
10. Marketplace prices are a 2026-11-18 snapshot and will go stale. The canonical form is still `R$ 1.234,56`.

No personal names, emails, phone numbers, or secrets are stored. A decision-maker, if filled later, is a role, not a person.
