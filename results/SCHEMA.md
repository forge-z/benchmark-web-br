# Resultados

Um JSONL por execução, uma linha por item e ferramenta. JSONL solto em `results/*.jsonl` fica de fora do git (`.gitignore`). Uma rodada publicada, com o texto de terceiro já retirado, mora em `results/round-*/`. O nome do arquivo é `{ferramenta}__{prova}__{run_id}.jsonl`.

A linha segue `schema_version` `1`:

| Campo | Significado |
|---|---|
| `run_id` | id da execução |
| `prova` | `noticias`, `leitura` ou `empresas` |
| `tool` | `baseline`, `exa`, `parallel`, `parallel_task_core`, `tinyfish`, `firecrawl`, `context_dev` |
| `item_id` | id da linha do dataset |
| `dry_run` | verdadeiro quando nenhuma rede foi chamada |
| `skipped` | verdadeiro quando a chave da ferramenta não estava no ambiente |
| `skip_reason` | vazio, ou `sem NOME_DA_CHAVE` |
| `started_at`, `finished_at` | ISO 8601 em UTC |
| `latency_ms` | relógio do cliente. Zero no dry-run |
| `http_status` | status da última chamada, ou nulo |
| `error` | vazio quando a chamada principal voltou 200 |
| `estimated_credits` | soma das chamadas, ou nulo quando a tabela não publica crédito |
| `estimated_cost_usd` | soma das estimativas de lista, ou nulo |
| `calls` | uma entrada por chamada, com `call`, `method`, `endpoint`, `request`, `http_status`, `estimated_credits`, `estimated_cost_usd`, `cost_notes` |
| `output` | o schema comum da prova |

`request` não leva chave. A chave sai só do header, lido na hora, e não é gravado.

## Saída por prova

Notícias:

```json
{"items": [{"url": "", "title": "", "published_at": "", "snippet": ""}]}
```

Leitura:

```json
{"url": "", "title": "", "text": "", "published_at": "", "price_brl": "", "seller": "", "availability": "", "blocked": false}
```

`text` é cortado em 20 mil caracteres. Empresas:

```json
{"answers": {"cnpj": {"value": "", "citations": []}}, "mode": "search_extract"}
```

Os dez campos estão em `runners/fields.py` (`COMPANY_FIELDS`). `parallel_task_core` usa `mode` `task_core`.

O texto extraído fica no JSONL local para a correção. Não versionar esse arquivo cru: ele pode repetir texto de terceiros.

## Rodada publicada

`results/round-1-2026-11-18/` entra no git de propósito. O `.gitignore` só casa `results/*.jsonl` na raiz de `results/`, então o subdiretório não precisou de exceção.

Para não redistribuir texto de terceiro:

- `output.text` da leitura está vazio; no lugar ficam `text_chars` e `text_sha256`
- `snippet` das notícias está vazio; no lugar fica `snippet_chars`
- URL de perfil pessoal do LinkedIn, slug de post ou pulse e título que ainda trazia nome de pessoa viram `[perfil-pessoal-removido]`

Os campos de `schema_version` `1` continuam presentes. Os campos extras não entram no líquido.
