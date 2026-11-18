# Methodology

Portuguese version: [METODOLOGIA.md](METODOLOGIA.md).

What this benchmark measures, how it measures, and what one round does not let you conclude. The rules for right, wrong, and blank are in `grade/grading_rules.md`. This file is the design. That one is the operational answer key.

The inspiration is [research-agent-eval](https://github.com/itsyusufahmed/research-agent-eval). The shape of the score came from there: three outcomes, net = right − wrong, a bootstrap interval, rules published before the round. The tasks, the datasets, and the text of the rules are from this repository.

## Question

Given the same input, how much of what the tool returns about the Brazilian web is right, how much is wrong, and how much does it leave blank? Latency and cost sit beside the net. They do not go inside it.

"The same input" means the same text. There is no extra prompt for the tool that did worse on the last round. Where the API requires a structural field (`news` category, `tbs`, `recency_minutes`, `articleLanguage`), the runner maps the 48-hour window onto that field and records the mapping. That is not a different prompt. It is the same time cut.

## Three tasks

### 1. Dated news search

A panel of 25 Brazilian sites, checked on 2026-11-18, in the bands industry and machining, economy, technology, and automotive. Forty pt-BR queries, ten per band, with a 48-hour window from the run's `started_at`.

The panel describes the coverage that matters. It does not become a domain filter. A news item outside the 25 sites counts, if it is inside the window. Panel coverage may become a metric in a later version. Today it is not a score.

Metrics:

- items with an ISO date inside the window (right), outside it (wrong), or with no date (blank)
- duplicate URLs, apart from the net
- client latency
- estimated cost per 1,000 queries, from the sum of the calls

There is no expected URL. The window moves with the clock, so an answer key of links would be stale the next day. The 40 rows are `a revisar` for that reason, not for lack of text.

### 2. Page reading

The tool receives a URL and returns title, clean text, date, price in reais, seller, and availability.

The target was about 60 URLs: 20 news pages, 10 PDFs, and 30 product pages. The 20 news pages have a title and a date read on the page or in the RSS of the same story. The 10 PDFs are Anfavea letters (`carta477.pdf` through `carta486.pdf`). All ten URLs opened with HTTP 200. Four titles were read on the first page (issues 479, 480, 481, and 486). The other six titles stayed empty. I did not infer the month from the sequence.

Product pages: 30 rows. 26 are checked: Kabum (1, with title, price `R$ 49,98`, and seller), Mercado Livre (5), Amazon.com.br (5), Casas Bahia (5), Americanas (5), and Magalu (5). Price, seller, or availability stays empty when the page did not tie the field to the product. An empty cell does not enter the denominator. Four Shopee URLs (l57–l60) are `a revisar`: the read hit a traffic check, and title, price, seller, and availability stayed empty. One Shopee URL is still missing to reach 5. That fifth row was not invented. The recorded price is the 2026-11-18 snapshot.

Metrics:

- per field with an answer key: right, wrong, or blank
- noise rate: text lines that look like a menu or a link list, apart from the net
- block (HTTP 401, 403, 429, 503, or the page says captcha)
- latency and cost

The canonical price is `R$ 1.234,56`. Comparison uses that form, not the raw text.

### 3. Brazilian company research

Thirty companies, in four groups: Santa Catarina industry, manufacturers and industrial groups with a national presence, and cutting-tool distributors. The presence band was observed, not estimated:

- rich: CNPJ confirmed on BrasilAPI and an official site that opened
- medium: Tupy and Portobello. The band stayed `media` even after the switch to the head office. For Portobello the CVM still lists Florianópolis and BrasilAPI lists Tijucas. For Tupy, head office and CVM agree on Joinville. The band was not promoted on this round
- thin: KSC Ferramentas. The site opened and the city in the text is Joinville, but no CNPJ was tied to it
- to review: Intelbras and Marcopolo. The registration is fine and the site did not open from here

Twenty-nine rows have the head-office cadastral block and `gabarito_status` checked. One stays to review: KSC Ferramentas. The answer-key CNPJ is the head office on BrasilAPI (`descricao_identificador_matriz_filial`), not the branch. A `/0001` suffix does not prove head office. Three rows switched from branch to head office on 2026-11-18: Tupy (`/0003-00`, Joinville, iron and steel foundry), Romi (`/0014-88`, same city and CNAE), and Randoncorp (`/0011-98`, holding-company CNAE). Company LinkedIn was filled for Kennatech, Repatri, and BFT, only with `/company/` URLs. The role was filled only for Kennatech, as “Diretor Técnico e Comercial” (technical and commercial director), with no personal name. Recent news is still empty. Distributor pages that listed people, email, and phone were not copied.

The ten questions are the same for every tool: CNPJ, legal name, city, state (UF), size class (`porte`), segment, site, company LinkedIn, commercial decision-maker's role, recent news. The runner receives the name and those questions. It does not receive CNPJ, site, or city.

Each tool searches and extracts with its own pair of endpoints, all on the current API. Parallel uses `/v1/search` and `/v1/extract`. Firecrawl, on task 3, calls `/v2/scrape` with JSON format (schema and prompt) on up to three URLs from the search. `parallel_task_core` is the task-3 reference: one request to the `core` processor at `/v1/tasks/runs`, with an `output_schema` of type `json`. It does not run on tasks 1 and 2.

The baseline abstains on this task. Giving it the official site would hand it the answer. A future `url_partida` column, separate from the answer key, would allow a baseline that reads a start page without seeing the expected value.

`porte` is the BrasilAPI text. `DEMAIS` is whoever is not MEI, ME, or a small business. In this sample, 28 filled rows are `DEMAIS` and Repatri is `EMPRESA DE PEQUENO PORTE`. The field barely separates size.

## Score

For each graded fact:

- right
- wrong
- blank, when an answer key exists and the answer came back empty

A cell with no answer key does not enter the denominator. Exception: a CNPJ with an invalid check digit is wrong even with no answer key.

```
net = 100 * (right − wrong) / (right + wrong + blank)
```

A blank does not add. A wrong answer costs as much as a right answer earns. Abstaining, when there was an answer key, earns nothing and costs nothing.

The 95% interval resamples the items (the query, the URL, or the company), not the loose cells. A query with ten news items goes in together. There are 2,000 resamples, seed `20261118`, percentiles 2.5 and 97.5. The comparison between two tools uses the paired difference on the same item. An interval that does not contain zero is the mark of a separation. The repository does not turn that into a "winner" sentence.

A query with many items weighs more in the score than a query with one item, because the net is over cells. The bootstrap returns the whole item, so the uncertainty respects the item. Weighting queries equally is an open decision.

Duplicates, latency, cost, blocks, and noise do not enter the net in this version.

## What is deterministic

Date, price in reais, and CNPJ do not go through a model.

- News date: ISO, inside the 48 hours before `started_at`.
- Page date: the same civil date in `America/Sao_Paulo`, or a difference of up to 26 hours. The CIMM feed came with timezone `+0300`. The date was stored in UTC, and the tolerance covers one day of a swapped timezone. That timezone is worth a review.
- Price: the canonical form above.
- CNPJ: 14 digits of the head office and the two check digits. Comparison ignores punctuation. A branch CNPJ with a valid check digit is wrong. A `/0001` suffix does not prove the establishment is the head office.
- Legal name, city, state (UF), and `porte`: equality with accents and case stripped. City, state, `porte`, and segment are those of the head office on BrasilAPI. If the CVM disagrees on the city or the state, BrasilAPI wins. The disagreement stays in `notas`. `porte` is the BrasilAPI text (`DEMAIS` or `EMPRESA DE PEQUENO PORTE`).
- Segment: one string contains the other, after folding. The answer key is the head office's main CNAE, not the CVM's and not a branch's.
- Site: the host, without `www`.
- LinkedIn: only a URL with `/company/`. A personal profile does not count and is not stored.

Role and recent news do not enter the score. There is no LLM judge: the code does not call a model. An email or a phone number in the answer stays wrong by a fixed rule. Human review is a reproducible sample:

```bash
python -m grade.amostra --cells results/cells.jsonl --out results/amostra.csv --n 10 --seed 20261118
```

Without `--cells`, the draw uses the dataset rows. The population is ordered and the seed is `20261118`, the same as the bootstrap. The CSV brings `revisao_humana` and `comentario` empty.

## Cost

Each call records an estimated credit count and an estimated cost in dollars, with the public-table sentence read on 2026-11-18 (`runners/costs.py`).

| Tool | Estimate used |
|---|---|
| Exa search `auto` | US$ 7 / 1,000, up to 10 results, plus highlights |
| Exa contents | US$ 1 / 1,000 pages |
| Parallel search | advanced mode, the `/v1` default, US$ 5 / 1,000 |
| Parallel extract | US$ 1 / 1,000 URLs |
| Parallel Task core | US$ 25 / 1,000 successful runs. A failure zeroes the estimate |
| TinyFish | US$ 0 inside the documented quota (12,000 searches/day, 1,000 fetch URLs/day). Overage is not fixed in the code |
| Firecrawl search | 2 credits per 10 results. Dollars per credit are not in the table used |
| Firecrawl scrape markdown | 1 credit. Page reading uses markdown only |
| Firecrawl scrape JSON | 5 credits per page (1 for the scrape + 4 for the JSON format), up to 3 URLs on task 3 |
| Context.dev | 1 credit per 10 news items, 1 per 10 on web search, 1 on scrape, 2 on company search in `fast` mode. Dollars per credit are not published |

Cost per 1,000 queries is the mean estimated cost of the rows, times 1,000. It is not the invoice.

## What the runners do not do

- They do not call a high-priced "agent" product: Firecrawl Agent, Parallel FindAll, TinyFish automation, TinyFish research.
- They do not restrict the domain to the panel.
- They do not receive the answer key.
- They do not store the key. The key goes from the environment variable to the header and dies there.
- They do not redistribute the page body. The reading baseline may store the SHA-256 locally. The `snapshots/` directory is in `.gitignore`.

## Limits

The sample of companies with a checked registration is, in large part, publicly held. They have a site and a CNPJ that are easy to find. The "rich" band measures "the site opened and the CNPJ matches", not brand authority. Several do not repeat the CNPJ in the HTML. The link is the name on the CVM plus BrasilAPI plus a site that opened with that name.

Tupy's old CNPJ (`/0001-49`) was a branch in São Paulo. The head office is `/0003-00`, in Joinville, and that is what is in the answer key. Portobello stays in Tijucas, which is the head office on BrasilAPI. The CVM still lists Florianópolis. KSC Ferramentas still has no CNPJ: two active Joinville registrations have similar names, and neither was tied to the site.

`porte` barely discriminates: 28 rows are `DEMAIS` and one is `EMPRESA DE PEQUENO PORTE`.

Task 1 has no URL answer key. It measures date and duplicates, not whether the story is the one an editor would pick.

A 2026 marketplace page is built on the client. The 26 checked product rows are a 2026-11-18 snapshot. The price goes stale. The four Shopee URLs were not read: the page hit a traffic check. A fifth Shopee URL is still missing.

Context.dev does not filter news by Brazil. Firecrawl does not apply `tbs` on the news source. Exa uses the `news` category. These three task-1 runs are not the same geographic cut, and the difference is in the runner on purpose, because the API does not offer the same field. Treating that as a tie on "search in Brazil" would be forcing it.

The CIMM `+0300` timezone may be a CMS error. The date was converted to UTC, and the one-day tolerance absorbs the case on task 2. It does not absorb a story on the edge of the 48-hour window.

Before round 1, no paid call was made. The runners were exercised with `--dry-run`. The request schema can fail live (a 422, for example), and that shows up only with credit. In round 1, Exa, TinyFish, and Parallel ran on paid accounts; Firecrawl and Context.dev used a free plan.

## How to reproduce a round

1. `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
2. Export only the keys that will be used. Without the variable, the tool is skipped.
3. Start with `--limit 1` and look at the JSONL. `--dry-run` shows the request without opening a socket.
4. `--limit 0` only when the estimated cost of the 1-item sample, times the dataset size, fits in the free credit.
5. `python -m grade.grade --results <arquivo.jsonl> --out results/cells.jsonl`
6. `python -m grade.score --cells results/cells.jsonl`
7. `python -m grade.amostra --cells results/cells.jsonl --out results/amostra.csv --n 10 --seed 20261118`

Loose JSONL from a run stays out of git (`results/*.jsonl`). Whoever publishes a round uploads the aggregate (net, interval, cost per 1,000, latency) and, with the third-party body already removed, the JSONL under `results/round-*/`. The round cites the dataset version. An extracted third-party body is not uploaded.

The seed and the resample count are in the code (`20261118`, 2000). Changing either changes the interval and has to be stated next to the number.

## Round 1 (2026-11-18): deviations from the design

Results are in `results/round-1-2026-11-18/`. What this round did differently from what the README describes:

1. **Calls through Executor.** The tools were called through a tool gateway (Executor), not through `httpx` directly. The runners ran unchanged: a local adapter swapped `common.request_json` for the equivalent tool's response on the gateway, with the same request body. Latency includes the gateway overhead. On Task core, latency is from creation to the end of the run.
2. **Firecrawl.** The gateway requires `formats` and `sources` as objects (`[{"type": "markdown"}]`, `[{"type": "web"}]`) instead of strings. `tbs` stayed at the top of the request. The request content is the same as the runner's.
3. **Samples under a credit cap.** The cap of about 60% of the free balance applied to Firecrawl and Context.dev. That is why the companies task ran on a sample for Firecrawl (e01–e12, 12 of 30) and Context.dev (e01–e24, 24 of 30). Their other tasks are complete. Exa, TinyFish, and Parallel (including Task) ran on paid accounts.
4. **Context.dev free-plan limits.** 2 concurrent requests and 10 per minute. Calls were made in batches of up to 9 per minute.
5. **Exa.** The first run used the Exa MCP, without `category: news` and without a date filter, and was discarded. The three tasks were redone through the API (`/search` and `/contents`) with the runner's exact body. Summed `costDollars`: US$ 0.631.
6. **Parallel Task core** ran only on the companies task, as a reference column.
7. **Possible double charge.** Some gateway programs failed on a transport timeout, and the calls with no response were retried. They may have been charged twice. The balance read before and after is in the PR cost table, and the per-item estimate does not include those retries.
8. **Context.dev reading.** The runner started reading title and date from the scrape `metadata` (with a fallback to openGraph and JSON-LD `datePublished`). The 60 responses already collected were reprocessed with no new calls. The net went from −1.7 to 33.9.
9. **News.** The 48-hour window on the requests was fixed at each tool's first run. Grading uses each item's `started_at`. The gap between the two is under 1 hour.

### Caveats

How to read the table in `results/round-1-2026-11-18/`:

1. **Unequal samples.** On the companies task, Firecrawl has 12 rows (e01–e12) and Context.dev has 24 (e01–e24). Those two nets are not directly comparable to the tools that have all 30. News (40 queries) and reading (60 URLs) have one row per item.
2. **The net is in points.** It is the percent right minus the percent wrong, from −100 to 100: `100 × (right − wrong) / (right + wrong + blank)`. It is not a percentage.
3. **One round, no repeats.** 40 queries, 60 URLs, 30 companies. A gap of a few points can be noise.
4. **Tool plus runner.** Each tool ran through a runner in this repository, not necessarily in the vendor's best setup. The number measures the two together. Exa reached 100 on news on the full-API run (item 5: `/search` and `/contents`, with `category: news` and the date window). Context.dev reading went from −1.7 to 33.9 after the runner was fixed (item 8), on the same 60 responses, with no new call.
5. **Parallel Task sits apart.** It is a research agent. The median was 2.4 minutes per company (142800 ms in the latency table). Search and extraction stay in seconds. The row is separate because the time and the kind of call are different.
6. **Cheap next step.** When there is credit, finish the 18 companies missing from Firecrawl (e13–e30) and the 6 from Context.dev (e25–e30).
