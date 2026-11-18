# Metodologia

O que este benchmark mede, como mede, e o que uma rodada não autoriza a concluir. As regras de certo, errado e branco estão em `grade/grading_rules.md`. Este arquivo é o desenho; aquele é o gabarito operacional.

A inspiração é o [research-agent-eval](https://github.com/itsyusufahmed/research-agent-eval). De lá veio a forma da nota: três desfechos, líquido = certo − errado, intervalo por bootstrap, regras publicadas antes da rodada. As provas, os datasets e o texto das regras são deste repositório.

## Pergunta

Dada a mesma entrada, quanto do que a ferramenta devolve sobre a web brasileira está certo, quanto está errado, e quanto ela deixa em branco? Latência e custo entram ao lado, não dentro do líquido.

"A mesma entrada" quer dizer o mesmo texto. Não há prompt extra para a ferramenta que foi pior na última rodada. Onde a API exige um campo estrutural (categoria `news`, `tbs`, `recency_minutes`, `articleLanguage`), o runner traduz a janela de 48 horas para esse campo e anota a tradução. Isso não é um prompt diferente. É o mesmo recorte de tempo.

## Três provas

### 1. Busca de notícias com data

Painel de 25 sites brasileiros, conferidos em 2026-11-18, nas faixas indústria e usinagem, economia, tecnologia e automotivo. Quarenta consultas em pt-BR, dez por faixa, com janela de 48 horas a partir de `started_at` da execução.

O painel descreve a cobertura que interessa. Ele não vira filtro de domínio. Uma notícia fora dos 25 sites, dentro da janela, conta. Cobertura do painel pode virar métrica numa versão seguinte; hoje não é nota.

Métricas:

- itens com data ISO dentro da janela (certo), fora (errado) ou sem data (branco)
- duplicatas de URL, à parte do líquido
- latência do cliente
- custo estimado por 1.000 consultas, a partir da soma das chamadas

Não há URL esperada. A janela anda com o relógio, então um gabarito de links ficaria velho no dia seguinte. As 40 linhas estão `a revisar` por esse motivo, não por falta de texto.

### 2. Leitura de página

A ferramenta recebe uma URL e devolve título, texto limpo, data, preço em reais, vendedor e disponibilidade.

A meta era cerca de 60 URLs: 20 notícias, 10 PDFs e 30 páginas de produto. As 20 notícias têm título e data lidos na página ou no RSS da mesma matéria. Os 10 PDFs são cartas da Anfavea (`carta477.pdf` a `carta486.pdf`); as dez URLs abriram com HTTP 200. Quatro títulos foram lidos na primeira página (edições 479, 480, 481 e 486). Os outros seis títulos ficaram vazios. Não inferi o mês pela sequência.

Páginas de produto: 1 de 30. A URL da Kabum que o HTML da busca citava abriu. O título da página era genérico e o preço visível no HTML não foi amarrado ao produto, então esses campos ficaram vazios. Mercado Livre, Americanas e Shopee abriram a busca e o HTML não trazia link de produto. Amazon, Magalu, Casas Bahia e Carrefour não abriram daqui (403 ou 503). Essas 29 URLs não foram inventadas.

Métricas:

- por campo com gabarito: certo, errado ou branco
- taxa de ruído: linhas do texto que parecem menu ou lista de links, à parte do líquido
- bloqueio (HTTP 401, 403, 429, 503, ou a página diz captcha)
- latência e custo

O preço canônico é `R$ 1.234,56`. A comparação é nessa forma, não no texto cru.

### 3. Pesquisa de empresas brasileiras

Trinta empresas, em quatro grupos: indústria de Santa Catarina, fabricantes e grupos industriais com presença nacional, e distribuidores de ferramenta de corte. A faixa de presença foi observada, não estimada:

- rica: CNPJ confirmado na BrasilAPI e site oficial que abriu
- média: CNPJ confirmado, site abriu, e a cidade da CVM não é a mesma da BrasilAPI (Tupy, Portobello). A cidade ficou vazia
- fraca: site de distribuidor regional abriu e o HTML não traz CNPJ
- a revisar: cadastro ok e site não abriu (Intelbras, Marcopolo), ou site abriu sem CNPJ conferido (OSG, Tungaloy)

Vinte e uma linhas têm o bloco cadastral preenchido e `gabarito_status` verificado. Nove ficam a revisar. LinkedIn, cargo e notícia recente estão vazios em todas. Páginas de distribuidor listam gente, e-mail e telefone; nada disso foi copiado. O cargo, se for preenchido, é o cargo público da função, sem nome de pessoa.

As dez perguntas são as mesmas para toda ferramenta: CNPJ, razão social, cidade, UF, porte, segmento, site, LinkedIn da empresa, cargo do decisor comercial, notícia recente. O runner recebe o nome e essas perguntas. Não recebe CNPJ, site nem cidade.

Cada ferramenta faz busca e extrato com o próprio par de endpoints. `parallel_task_core` é a referência da prova 3: um pedido ao processador `core`, com schema de saída dos dez campos. Não entra nas provas 1 e 2.

O baseline se abstém nesta prova. Dar a ele o site oficial seria entregar a resposta. Uma coluna futura `url_partida`, separada do gabarito, permitiria um baseline que lê uma página de partida sem ver o esperado.

`porte` `DEMAIS` é o código da Receita para quem não é MEI, ME nem EPP. Todas as empresas com porte preenchido estão nessa faixa, então o campo não separa tamanho nesta amostra.

## Nota

Para cada fato graduado:

- certo
- errado
- branco, quando o gabarito existe e a resposta veio vazia

Célula sem gabarito não entra no denominador. Exceção: CNPJ com dígito verificador inválido é errado mesmo sem gabarito.

```
líquido = 100 * (certos − errados) / (certos + errados + brancos)
```

Branco não soma. Errar custa o mesmo que acertar rende. Abstener-se, quando havia gabarito, não rende ponto e não tira.

O intervalo de 95% reamostra os itens (a consulta, a URL ou a empresa), não as células soltas. Uma consulta com dez notícias entra junta. São 2000 reamostras, semente `20261118`, percentis 2,5 e 97,5. A comparação entre duas ferramentas usa a diferença pareada no mesmo item. O intervalo que não contém zero é a marca de separação; o repositório não transforma isso numa frase de "vencedor".

Uma consulta com muitos itens pesa mais no ponto do que uma consulta com um item, porque o líquido é sobre células. O bootstrap devolve o item inteiro, então a incerteza respeita o item. Pesar consultas por igual é decisão em aberto.

Duplicata, latência, custo, bloqueio e ruído não entram no líquido nesta versão.

## O que é determinístico

Data, preço em reais e CNPJ não passam por modelo.

- Data de notícia: ISO, dentro das 48 horas anteriores a `started_at`.
- Data de página: a mesma data civil em `America/Sao_Paulo`, ou diferença de até 26 horas. O feed da CIMM veio com fuso `+0300`; a data foi gravada em UTC e a tolerância cobre um dia de fuso trocado. Vale revisar esse fuso.
- Preço: a forma canônica acima.
- CNPJ: 14 dígitos e os dois verificadores. A comparação ignora pontuação.
- Razão social, cidade, UF e porte: igualdade sem acento e sem caixa. A cidade do gabarito está como a Receita devolve, sem acento.
- Segmento: um texto contém o outro, depois de dobrar.
- Site: o host, sem `www`.
- LinkedIn: só URL com `/company/`. Perfil de pessoa não conta e não é armazenado.

Cargo e notícia recente estão marcados como juiz. O gancho lê `GRADE_LLM_API_KEY` e, nesta versão, não envia pedido. Sem o juiz, esses dois campos ficam de fora, salvo e-mail ou telefone na resposta, que já é errado por regra fixa.

O juiz, quando alguém ligar, deve ler as regras e a página citada, sem ver o nome da ferramenta. Um valor que confere com o gabarito e cuja citação não abre não vira errado só por isso.

## Custo

Cada chamada grava crédito estimado e custo estimado em dólares, com a frase da tabela pública lida em 2026-11-18 (`runners/costs.py`).

| Ferramenta | Estimativa usada |
|---|---|
| Exa busca `auto` | US$ 7 / 1.000, até 10 resultados, mais highlights |
| Exa contents | US$ 1 / 1.000 páginas |
| Parallel busca | teto advanced da v1, US$ 5 / 1.000. O beta não publica preço próprio |
| Parallel extrato | US$ 1 / 1.000 URLs |
| Parallel Task core | US$ 25 / 1.000 execuções com sucesso. Falha zera a estimativa |
| TinyFish | US$ 0 dentro da cota documentada (12.000 buscas/dia, 1.000 URLs de fetch/dia). Excedente não está fixado no código |
| Firecrawl busca | 2 créditos por 10 resultados. Dólar por crédito não está na tabela usada |
| Firecrawl scrape markdown | 1 crédito. Modo JSON não é usado na leitura, para não gastar o extra |
| Firecrawl extract | 1 crédito a cada 15 tokens. `enableWebSearch` fica falso |
| Context.dev | 1 crédito por 10 notícias, 1 por 10 na busca web, 1 no scrape, 2 na busca de empresa em modo `fast`. Dólar por crédito não publicado |

O custo por 1.000 consultas é a média do custo estimado das linhas, vezes 1.000. Não é a fatura.

## O que os runners não fazem

- Não chamam produto "agent" de preço alto: Firecrawl Agent, Parallel FindAll, TinyFish automation, TinyFish research.
- Não restringem domínio ao painel.
- Não recebem o gabarito.
- Não gravam a chave. A chave sai da variável de ambiente para o header e morre ali.
- Não redistribuem o corpo da página. O baseline de leitura pode gravar o SHA-256 localmente. A pasta `snapshots/` está no `.gitignore`.

## Limitações

A amostra de empresas com cadastro verificado é, em grande parte, companhia aberta. Elas têm site e CNPJ fáceis de achar. A faixa "rica" mede "o site abriu e o CNPJ confere", não autoridade de marca. Várias não repetem o CNPJ no HTML; o vínculo é o nome na CVM mais a BrasilAPI mais um site que abriu com esse nome.

Tupy e Portobello têm conflito de cidade entre CVM e BrasilAPI. Não escolhi um lado.

O porte não discrimina: quem está preenchido é `DEMAIS`.

A prova 1 não tem gabarito de URL. Ela mede data e duplicata, não se a matéria é a que um editor escolheria.

Marketplace em 2026 é página montada no cliente. Um runner HTTP sem navegador não vê o produto. Completar as 29 URLs pede alguém abrindo a loja, ou um navegador, e mesmo assim o preço envelhece.

Context.dev não filtra notícia por Brasil. Firecrawl não aplica `tbs` na fonte de notícias. Exa usa a categoria `news`. Essas três provas 1 não são o mesmo recorte geográfico, e a diferença está no runner de propósito, porque a API não oferece o mesmo campo. Tratar isso como empate de "busca no Brasil" seria forçar.

O fuso `+0300` da CIMM pode ser erro do CMS. A data foi convertida para UTC e a tolerância de um dia absorve o caso na prova 2. Não absorve uma matéria no limite da janela de 48 horas.

Nenhuma chamada paga foi feita. Os runners foram exercitados em `--dry-run`. O schema do pedido pode falhar ao vivo (um 422 da Parallel beta, por exemplo) e isso só aparece com crédito.

## Como reproduzir uma rodada

1. `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
2. Exportar só as chaves que forem usadas. Sem a variável, a ferramenta é pulada.
3. Começar com `--limit 1` e olhar o JSONL. `--dry-run` mostra o pedido sem abrir socket.
4. `--limit 0` só quando o custo estimado da amostra de 1 item, vezes o tamanho do dataset, couber no crédito grátis.
5. `python -m grade.grade --results <arquivo.jsonl> --out results/cells.jsonl`
6. `python -m grade.score --cells results/cells.jsonl`

O arquivo de células e o JSONL de resultado ficam fora do git. Quem publicar um resultado sobe o agregado (líquido, intervalo, custo por 1.000, latência) e cita a versão do dataset. O corpo extraído de terceiro não sobe.

A semente e o número de reamostras estão no código (`20261118`, 2000). Mudar os dois muda o intervalo e deve ser dito junto com o número.
