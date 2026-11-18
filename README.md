# benchmark-web-br

Comparação pública de ferramentas de web em sites brasileiros. Três provas, a mesma entrada, o mesmo schema de saída, sem ajuste de prompt por ferramenta.

A nota segue o desenho de [research-agent-eval](https://github.com/itsyusufahmed/research-agent-eval): cada fato é certo, errado ou branco, e o líquido é certos menos errados. O intervalo de 95% é um bootstrap por item. As regras estão em `grade/grading_rules.md`, publicadas com o código.

Isto é a estrutura inicial. Os datasets têm lacunas contadas. Nenhuma chamada paga foi feita para montar o repositório.

## Por que Python

Python 3.11, com a biblioteca padrão e uma dependência: `httpx`. CSV, JSONL, HTML, XML, hash e o bootstrap cabem na stdlib. `httpx` é o único cliente HTTP, então o corpo do pedido de cada ferramenta fica visível no runner, sem SDK de fornecedor. Os testes usam `unittest`.

## Licenças

- Código: MIT (`LICENSE`)
- Datasets e resultados: CC BY 4.0 (`LICENSE-DATA`)
- Corpo de página de terceiro não é redistribuído. O índice em `snapshots-index/` guarda URL, SHA-256 e data

## O que tem aqui

| Caminho | Conteúdo |
|---|---|
| `datasets/` | Sites, consultas, URLs e empresas. Ver a contagem em `datasets/README.md` |
| `runners/` | Um runner por ferramenta, mais o baseline HTTP/RSS |
| `grade/` | Correção determinística, regras e o líquido |
| `results/` | Vazio no git. O formato está em `results/SCHEMA.md` |
| `snapshots-index/` | Só o índice. Bytes crus ficam fora do git |
| `METODOLOGIA.md` | O que é medido, como, e o que não dá para concluir |

## Ferramentas

| Runner | Chave | O que chama |
|---|---|---|
| `baseline` | nenhuma | GET da página, e RSS quando o dataset tem feed |
| `exa` | `EXA_API_KEY` | `POST /search` e `POST /contents` |
| `parallel` | `PARALLEL_API_KEY` | `POST /v1/search` e `POST /v1/extract` |
| `parallel_task_core` | `PARALLEL_API_KEY` | `POST /v1/tasks/runs` com processador `core`, só na prova 3 |
| `tinyfish` | `TINYFISH_API_KEY` | `GET api.search.tinyfish.ai` e `POST api.fetch.tinyfish.ai` |
| `firecrawl` | `FIRECRAWL_API_KEY` | `/v2/search` e `/v2/scrape` (markdown na leitura; JSON na prova 3) |
| `context_dev` | `CONTEXT_DEV_API_KEY` | notícias, busca web, busca de empresa e scrape |

Sem a variável, o runner grava a linha com `skipped` e não chama a rede. Não há Firecrawl Agent, Parallel FindAll, TinyFish automation nem TinyFish research.

O pedido é o mesmo texto para todas: a consulta, a URL, ou o nome da empresa mais as dez perguntas de `perguntas_empresas.csv`. O gabarito não entra no pedido. A janela de 48 horas vira filtro de data só onde a API tem esse campo, e isso está anotado no runner.

## Como reproduzir

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

O CI faz a mesma coisa, em Python 3.11, sem chave e sem rede.

Dry-run, um item, sem socket:

```bash
python -m runners.baseline --prova noticias --dry-run --limit 1
python -m runners.exa --prova leitura --dry-run --limit 1
python -m runners.parallel --prova empresas --dry-run --limit 1
```

`--limit 0` percorre o dataset inteiro. O padrão é `1`, para uma execução ao vivo não gastar a cota sem querer. A chave vem do ambiente (veja `.env.example`) e não é gravada no JSONL.

Uma execução ao vivo, ainda no limite de 1, só depois de exportar a chave:

```bash
python -m runners.exa --prova noticias --limit 1
python -m grade.grade --results results/exa__noticias__<run_id>.jsonl --out results/cells.jsonl
python -m grade.score --cells results/cells.jsonl
python -m grade.amostra --cells results/cells.jsonl --out results/amostra.csv --n 10 --seed 20261118
```

A correção não chama modelo. `grade/amostra.py` sorteia uma amostra reprodutível para revisão humana. Sem `--cells`, sorteia as linhas dos datasets.

O JSONL de resultado e o corpo em `snapshots/` ficam de fora do git. Custo e crédito estimados estão em cada chamada, com a fonte da tabela em `runners/costs.py`. Estimativa de lista não é fatura.

## Contagem dos datasets (2026-11-18)

| Dataset | Meta | No arquivo | Verificado | A revisar |
|---|---:|---:|---:|---:|
| Sites de notícia | ~25 | 25 | 25 homepages HTTP 200 (17 com RSS) | 0 |
| Consultas pt-BR | ~40 | 40 | 40 textos | 40 sem URL esperada, de propósito |
| Leitura, notícia | 20 | 20 | 20 com título e data | 0 |
| Leitura, PDF Anfavea | 10 | 10 | 10 URLs abriram | 10 no gabarito de campos; 4 têm título lido |
| Leitura, produto | 30 | 30 | 26 com título (Kabum, Mercado Livre, Amazon, Casas Bahia, Americanas, Magalu) | 4 Shopee sem página lida; falta 1 URL |
| Empresas | ~30 | 30 | 29 com cadastro da matriz | 1 (KSC Ferramentas, sem CNPJ) |
| Perguntas | ~10 | 10 | 10 textos | 0 |

LinkedIn da empresa entrou em três linhas, só com URL `/company/`. O cargo entrou só na Kennatech, como título público, sem nome de pessoa. Notícia recente continua vazia. Faixa de presença: 25 rica, 2 média, 1 fraca, 2 a revisar. O detalhe está em `datasets/README.md`.

## Decisões em aberto

1. A busca de notícias da Context.dev não tem país `br`. O filtro é idioma `pt` mais a data, então Portugal entra.
2. O `tbs` da Firecrawl não filtra a fonte `news`. A prova 1 usa a fonte `web` com `tbs`.
3. Exa está em `type: auto` (teto de US$ 7 / 1.000). `lite` é mais barato e pode caber melhor em crédito grátis.
4. O painel de 25 sites não restringe o domínio da busca. Cobertura do painel ainda não é nota.
5. O baseline da prova 3 se abstém. Ele não recebe o site oficial, senão a resposta vazaria. Dá para criar depois uma coluna `url_partida`, separada do gabarito.
6. Duplicata de URL é métrica, não entra no líquido. Consulta com mais itens pesa mais do que consulta com um item.
7. KSC Ferramentas continua sem CNPJ. Há dois cadastros ativos em Joinville com razão parecida e nenhum foi amarrado ao site.
8. Shopee: 4 URLs listadas, nenhuma página lida, e falta 1 para fechar 5. Em várias fichas já verificadas, preço, vendedor ou disponibilidade ficaram vazios.
9. `parallel_task_core` é uma ferramenta à parte, só na prova 3. Pode ser coluna de referência em vez de entrar no mesmo ranking.
10. Preço de marketplace é um snapshot de 2026-11-18 e envelhece. A forma canônica continua `R$ 1.234,56`.

## Privacidade

Repositório público. Sem nome de pessoa, e-mail, telefone ou chave. O cargo gravado é o título, não a pessoa.
