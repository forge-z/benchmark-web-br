# Rodada 1 — 2026-11-18

Líquido = certo − errado, por 100 células, com intervalo de 95% por bootstrap (`grade/score.py`, 2.000 reamostragens). Correção só por regra automática (`grade/grading_rules.md`). Entre parênteses, amostra menor que o dataset.

| Ferramenta | Notícias | Leitura | Empresas |
|---|---:|---:|---:|
| baseline | 98,4 [96,4; 99,7] | 24,3 [8,8; 40,4] | 0,0 [0,0; 0,0] |
| exa | 100,0 [100,0; 100,0] | 33,9 [18,0; 50,0] | 0,5 [0,0; 1,5] |
| parallel | -45,8 [-60,0; -29,8] | 37,4 [21,1; 53,2] | 10,1 [6,3; 13,3] |
| parallel_task_core | — | — | 87,4 [76,3; 95,2] |
| tinyfish | -45,3 [-63,4; -22,7] | 13,9 [3,5; 23,7] | 0,5 [0,0; 1,5] |
| firecrawl | 0,0 [0,0; 0,0] | 21,7 [7,6; 36,5] | -7,1 [-26,2; 11,9] (12/30) |
| context_dev | 100,0 [100,0; 100,0] | 33,9 [17,6; 50,0] | 10,0 [2,4; 17,0] (24/30) |

`parallel_task_core` é coluna de referência: roda só na prova de empresas.

## Latência e custo

Latência por item = soma das chamadas, medida dentro do Executor (inclui o overhead dele). Task core = criação → fim do run. Custo e crédito são estimativas de lista, salvo a Exa, que usa o `costDollars` devolvido pela API.

| Ferramenta | Prova | Itens | Erros | Latência mediana (ms) | p90 (ms) | Créditos est. | US$ est. |
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

## Arquivos

- `raw/`: um JSONL por ferramenta e prova (`results/SCHEMA.md`). Para não redistribuir texto de terceiros, `output.text` da leitura foi esvaziado e trocado por `text_chars` e `text_sha256`, e `snippet` das notícias por `snippet_chars`. URLs de perfil pessoal do LinkedIn foram substituídas por `[perfil-pessoal-removido]`. O mesmo marcador entrou no título que ainda trazia o nome da pessoa e nos slugs de post e pulse (`/posts/`, `/pulse/`). Recorrigir estes arquivos reproduz o mesmo líquido; só a métrica `ruido` depende do texto e vem das células.
- `grade/`: `cells__<prova>.jsonl` e `score__<prova>.json`, gerados do JSONL completo.
- `latencia_custo.tsv`: a tabela acima.

Os desvios desta rodada estão em `METODOLOGIA.md`, seção "Rodada 1".
