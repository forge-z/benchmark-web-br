# Round 1 — 2026-11-18

Net score = correct − wrong, per 100 cells, with a 95% bootstrap interval (`grade/score.py`, 2,000 resamples). Grading uses only the automatic rules in `grade/grading_rules.md`. Parentheses mark a sample smaller than the dataset.

| Tool | News | Reading | Companies |
|---|---:|---:|---:|
| baseline | 98.4 [96.4; 99.7] | 24.3 [8.8; 40.4] | 0.0 [0.0; 0.0] |
| exa | 100.0 [100.0; 100.0] | 33.9 [18.0; 50.0] | 0.5 [0.0; 1.5] |
| parallel | -45.8 [-60.0; -29.8] | 37.4 [21.1; 53.2] | 10.1 [6.3; 13.3] |
| parallel_task_core | — | — | 87.4 [76.3; 95.2] |
| tinyfish | -45.3 [-63.4; -22.7] | 13.9 [3.5; 23.7] | 0.5 [0.0; 1.5] |
| firecrawl | 0.0 [0.0; 0.0] | 21.7 [7.6; 36.5] | -7.1 [-26.2; 11.9] (12/30) |
| context_dev | 100.0 [100.0; 100.0] | 33.9 [17.6; 50.0] | 10.0 [2.4; 17.0] (24/30) |

`parallel_task_core` is a reference column: it runs only on the companies test.

## Latency and cost

Per-item latency is the sum of its calls, measured inside Executor (includes Executor overhead). Task core is run creation → completion. Credits and USD are list-price estimates, except Exa, which uses the `costDollars` returned by its API.

| Tool | Test | Items | Errors | Median latency (ms) | p90 (ms) | Est. credits | Est. USD |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline | noticias | 40 | 0 | 10 | 12 | 0 | 0 |
| baseline | leitura | 60 | 0 | 2107 | 3319 | 0 | 0 |
| baseline | empresas | 30 | 0 | 0 | 0 | 0 | 0 |
| exa | noticias | 40 | 0 | 1484 | 3157 | 0 | 0.28 |
| exa | leitura | 60 | 0 | 767 | 2698 | 0 | 0.051 |
| exa | empresas | 30 | 0 | 2234 | 2964 | 0 | 0.3 |
| parallel | noticias | 40 | 0 | 1385 | 3926 | 0 | 0.2 |
| parallel | leitura | 60 | 0 | 1556 | 2152 | 0 | 0.06 |
| parallel | empresas | 30 | 0 | 4551 | 6012 | 0 | 0.24 |
| parallel_task_core | empresas | 30 | 0 | 142800 | 225781 | 0 | 0.75 |
| tinyfish | noticias | 40 | 0 | 1439 | 2304 | 0 | 0 |
| tinyfish | leitura | 60 | 0 | 2118 | 8675 | 0 | 0 |
| tinyfish | empresas | 30 | 0 | 4404 | 9321 | 0 | 0 |
| firecrawl | noticias | 40 | 0 | 3464 | 8827 | 80 | 0 |
| firecrawl | leitura | 60 | 5 | 374 | 649 | 60 | 0 |
| firecrawl | empresas | 12 | 0 | 9102 | 13369 | 204 | 0 |
| context_dev | noticias | 40 | 0 | 813 | 2223 | 40 | 0 |
| context_dev | leitura | 60 | 0 | 497 | 20877 | 60 | 0 |
| context_dev | empresas | 24 | 0 | 6150 | 9985 | 120 | 0 |

## Files

- `raw/`: one JSONL per tool and test (`results/SCHEMA.md`). To avoid redistributing third-party text, reading `output.text` is emptied and replaced by `text_chars` and `text_sha256`, and news `snippet` by `snippet_chars`. Personal LinkedIn profile URLs are replaced by `[perfil-pessoal-removido]`. The same marker replaced a profile title that still carried the person's name, and personal slugs in post and pulse URLs (`/posts/`, `/pulse/`). Regrading these files reproduces the same net scores; only the `ruido` metric needs the text and comes from the cells.
- `grade/`: `cells__<prova>.jsonl` and `score__<prova>.json`, generated from the full JSONL.
- `latencia_custo.tsv`: the table above.

Round deviations are listed in `METODOLOGIA.md`, section "Rodada 1".
