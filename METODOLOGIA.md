# Metodologia

English version: [METHODOLOGY.md](METHODOLOGY.md).

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

Páginas de produto: 30 linhas. 26 estão verificadas: Kabum (1, com título, preço `R$ 49,98` e vendedor), Mercado Livre (5), Amazon.com.br (5), Casas Bahia (5), Americanas (5) e Magalu (5). Preço, vendedor ou disponibilidade ficam vazios quando a página não amarrava o campo ao produto; célula vazia não entra no denominador. Quatro URLs da Shopee (l57–l60) estão a revisar: a leitura caiu na verificação de tráfego e título, preço, vendedor e disponibilidade ficaram vazios. Falta 1 URL da Shopee para fechar 5; essa quinta linha não foi inventada. O preço gravado é o snapshot de 2026-11-18.

Métricas:

- por campo com gabarito: certo, errado ou branco
- taxa de ruído: linhas do texto que parecem menu ou lista de links, à parte do líquido
- bloqueio (HTTP 401, 403, 429, 503, ou a página diz captcha)
- latência e custo

O preço canônico é `R$ 1.234,56`. A comparação é nessa forma, não no texto cru.

### 3. Pesquisa de empresas brasileiras

Trinta empresas, em quatro grupos: indústria de Santa Catarina, fabricantes e grupos industriais com presença nacional, e distribuidores de ferramenta de corte. A faixa de presença foi observada, não estimada:

- rica: CNPJ confirmado na BrasilAPI e site oficial que abriu
- média: Tupy e Portobello. A faixa ficou `media` mesmo depois da troca para a matriz. Em Portobello a CVM ainda lista Florianópolis e a BrasilAPI lista Tijucas. Em Tupy, matriz e CVM coincidem em Joinville; a faixa não foi promovida nesta rodada
- fraca: KSC Ferramentas. O site abriu e a cidade do texto é Joinville, mas nenhum CNPJ foi amarrado
- a revisar: Intelbras e Marcopolo. O cadastro está ok e o site não abriu daqui

Vinte e nove linhas têm o bloco cadastral da matriz e `gabarito_status` verificado. Uma fica a revisar: KSC Ferramentas. O CNPJ do gabarito é o da matriz na BrasilAPI (`descricao_identificador_matriz_filial`), não o da filial. O sufixo `/0001` não garante matriz. Três linhas trocaram de filial para matriz em 2026-11-18: Tupy (`/0003-00`, Joinville, fundição de ferro e aço), Romi (`/0014-88`, mesma cidade e CNAE) e Randoncorp (`/0011-98`, CNAE de holding). LinkedIn da empresa entrou em Kennatech, Repatri e BFT, só com URL `/company/`. O cargo entrou só na Kennatech, como “Diretor Técnico e Comercial”, sem nome de pessoa. Notícia recente continua vazia. Páginas de distribuidor que listavam gente, e-mail e telefone não foram copiadas.

As dez perguntas são as mesmas para toda ferramenta: CNPJ, razão social, cidade, UF, porte, segmento, site, LinkedIn da empresa, cargo do decisor comercial, notícia recente. O runner recebe o nome e essas perguntas. Não recebe CNPJ, site nem cidade.

Cada ferramenta faz busca e extrato com o próprio par de endpoints, todos na API atual. A Parallel usa `/v1/search` e `/v1/extract`. A Firecrawl, na prova 3, faz `/v2/scrape` com formato JSON (schema e prompt) em até três URLs da busca. `parallel_task_core` é a referência da prova 3: um pedido ao processador `core` em `/v1/tasks/runs`, com `output_schema` do tipo `json`. Não entra nas provas 1 e 2.

O baseline se abstém nesta prova. Dar a ele o site oficial seria entregar a resposta. Uma coluna futura `url_partida`, separada do gabarito, permitiria um baseline que lê uma página de partida sem ver o esperado.

`porte` é o texto da BrasilAPI. `DEMAIS` é quem não é MEI, ME nem empresa de pequeno porte. Nesta amostra, 28 linhas preenchidas são `DEMAIS` e a Repatri é `EMPRESA DE PEQUENO PORTE`. O campo quase não separa tamanho.

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
- CNPJ: 14 dígitos da matriz e os dois verificadores. A comparação ignora pontuação. Um CNPJ de filial com dígito verificador válido é errado. O sufixo `/0001` não prova que o estabelecimento é a matriz.
- Razão social, cidade, UF e porte: igualdade sem acento e sem caixa. Cidade, UF, porte e segmento são os da matriz na BrasilAPI. Se a CVM divergir no município ou na UF, vale a BrasilAPI. A divergência fica em `notas`. O porte é o texto da BrasilAPI (`DEMAIS` ou `EMPRESA DE PEQUENO PORTE`).
- Segmento: um texto contém o outro, depois de dobrar. O gabarito é o CNAE principal da matriz, não o da CVM nem o de uma filial.
- Site: o host, sem `www`.
- LinkedIn: só URL com `/company/`. Perfil de pessoa não conta e não é armazenado.

Cargo e notícia recente não entram na nota. Não há juiz de LLM: o código não chama modelo. E-mail ou telefone na resposta continua errado por regra fixa. A revisão humana é uma amostra reprodutível:

```bash
python -m grade.amostra --cells results/cells.jsonl --out results/amostra.csv --n 10 --seed 20261118
```

Sem `--cells`, o sorteio usa as linhas dos datasets. A população é ordenada e a semente é `20261118`, a mesma do bootstrap. O CSV traz `revisao_humana` e `comentario` vazios.

## Custo

Cada chamada grava crédito estimado e custo estimado em dólares, com a frase da tabela pública lida em 2026-11-18 (`runners/costs.py`).

| Ferramenta | Estimativa usada |
|---|---|
| Exa busca `auto` | US$ 7 / 1.000, até 10 resultados, mais highlights |
| Exa contents | US$ 1 / 1.000 páginas |
| Parallel busca | modo advanced, o padrão da `/v1`, US$ 5 / 1.000 |
| Parallel extrato | US$ 1 / 1.000 URLs |
| Parallel Task core | US$ 25 / 1.000 execuções com sucesso. Falha zera a estimativa |
| TinyFish | US$ 0 dentro da cota documentada (12.000 buscas/dia, 1.000 URLs de fetch/dia). Excedente não está fixado no código |
| Firecrawl busca | 2 créditos por 10 resultados. Dólar por crédito não está na tabela usada |
| Firecrawl scrape markdown | 1 crédito. A leitura de página usa só markdown |
| Firecrawl scrape JSON | 5 créditos por página (1 do scrape + 4 do formato JSON), até 3 URLs na prova 3 |
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

O CNPJ antigo da Tupy (`/0001-49`) era filial em São Paulo. A matriz é `/0003-00`, em Joinville, e é o que está no gabarito. Portobello permanece em Tijucas, que é a matriz na BrasilAPI; a CVM ainda lista Florianópolis. KSC Ferramentas segue sem CNPJ: dois cadastros ativos em Joinville têm razão parecida e nenhum foi amarrado ao site.

O porte quase não discrimina: 28 linhas são `DEMAIS` e uma é `EMPRESA DE PEQUENO PORTE`.

A prova 1 não tem gabarito de URL. Ela mede data e duplicata, não se a matéria é a que um editor escolheria.

Marketplace em 2026 é página montada no cliente. As 26 fichas verificadas são um snapshot de 2026-11-18; o preço envelhece. As quatro URLs da Shopee não foram lidas: a página caiu na verificação de tráfego. Falta uma quinta URL da Shopee.

Context.dev não filtra notícia por Brasil. Firecrawl não aplica `tbs` na fonte de notícias. Exa usa a categoria `news`. Essas três provas 1 não são o mesmo recorte geográfico, e a diferença está no runner de propósito, porque a API não oferece o mesmo campo. Tratar isso como empate de "busca no Brasil" seria forçar.

O fuso `+0300` da CIMM pode ser erro do CMS. A data foi convertida para UTC e a tolerância de um dia absorve o caso na prova 2. Não absorve uma matéria no limite da janela de 48 horas.

Antes da rodada 1, nenhuma chamada paga foi feita. Os runners foram exercitados em `--dry-run`. O schema do pedido pode falhar ao vivo (um 422, por exemplo) e isso só aparece com crédito. Na rodada 1, Exa, TinyFish e Parallel rodaram em conta paga; Firecrawl e Context.dev usaram plano grátis.

## Como reproduzir uma rodada

1. `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
2. Exportar só as chaves que forem usadas. Sem a variável, a ferramenta é pulada.
3. Começar com `--limit 1` e olhar o JSONL. `--dry-run` mostra o pedido sem abrir socket.
4. `--limit 0` só quando o custo estimado da amostra de 1 item, vezes o tamanho do dataset, couber no crédito grátis.
5. `python -m grade.grade --results <arquivo.jsonl> --out results/cells.jsonl`
6. `python -m grade.score --cells results/cells.jsonl`
7. `python -m grade.amostra --cells results/cells.jsonl --out results/amostra.csv --n 10 --seed 20261118`

O JSONL solto de uma execução fica fora do git (`results/*.jsonl`). Quem publicar uma rodada sobe o agregado (líquido, intervalo, custo por 1.000, latência) e, com o corpo de terceiro já retirado, o JSONL em `results/round-*/`. A rodada cita a versão do dataset. O corpo extraído de terceiro não sobe.

A semente e o número de reamostras estão no código (`20261118`, 2000). Mudar os dois muda o intervalo e deve ser dito junto com o número.

## Rodada 1 (2026-11-18): desvios do desenho

Resultados em `results/round-1-2026-11-18/`. O que esta rodada fez diferente do que o README descreve:

1. **Chamadas pelo Executor.** As ferramentas foram chamadas por um gateway de ferramentas (Executor), não por `httpx` direto. Os runners rodaram sem alteração: um adaptador local trocou `common.request_json` pela resposta da ferramenta equivalente no gateway, com o mesmo corpo de pedido. A latência inclui o overhead do gateway. No Task core, a latência é da criação ao fim do run.
2. **Firecrawl.** O gateway exige `formats` e `sources` como objetos (`[{"type": "markdown"}]`, `[{"type": "web"}]`) em vez de strings. O `tbs` ficou no topo do pedido. O conteúdo do pedido é o mesmo do runner.
3. **Amostras por teto de crédito.** O teto de cerca de 60% do saldo grátis valia para a Firecrawl e a Context.dev. Por isso a prova de empresas rodou em amostra na Firecrawl (e01–e12, 12 de 30) e na Context.dev (e01–e24, 24 de 30). As outras provas dessas duas estão completas. Exa, TinyFish e Parallel (incluindo o Task) rodaram em conta paga.
4. **Limites do plano grátis da Context.dev.** 2 pedidos simultâneos e 10 por minuto. As chamadas foram feitas em lotes de até 9 por minuto.
5. **Exa.** A primeira execução usou o MCP da Exa, sem `category: news` nem filtro de data, e foi descartada. As três provas foram refeitas pela API (`/search` e `/contents`) com o corpo exato do runner. Custo somado do `costDollars`: US$ 0,631.
6. **Parallel Task core** rodou só na prova de empresas, como coluna de referência.
7. **Cobrança duplicada possível.** Alguns programas do gateway caíram por timeout de transporte, e as chamadas sem resposta foram refeitas. Elas podem ter sido cobradas duas vezes. O saldo lido antes e depois está na tabela de custo do PR, e a estimativa por item não inclui essas repetições.
8. **Context.dev leitura.** O runner passou a ler título e data do `metadata` do scrape (com fallback em openGraph e JSON-LD `datePublished`). As 60 respostas já coletadas foram reprocessadas sem novas chamadas. O líquido foi de −1,7 para 33,9.
9. **Notícias.** A janela de 48 h dos pedidos foi fixada na primeira execução de cada ferramenta. A correção usa o `started_at` de cada item; a diferença entre os dois é menor que 1 hora.

### Ressalvas

Como ler a tabela em `results/round-1-2026-11-18/`:

1. **Amostras desiguais.** Na prova de empresas, a Firecrawl tem 12 linhas (e01–e12) e a Context.dev tem 24 (e01–e24). O líquido dessas duas não é comparável direto ao das ferramentas com as 30. Notícias (40 consultas) e leitura (60 URLs) têm uma linha por item.
2. **O líquido é em pontos.** A conta é a % de certos menos a % de errados, de −100 a 100: `100 × (certos − errados) / (certos + errados + brancos)`. Não é uma porcentagem.
3. **Uma rodada, sem repetição.** São 40 consultas, 60 URLs e 30 empresas. Diferença de poucos pontos pode ser ruído.
4. **Ferramenta mais runner.** Cada ferramenta rodou por um runner deste repositório, não necessariamente na melhor configuração do fornecedor. O número mede os dois juntos. A Exa chegou a 100 em notícias na execução pela API completa (item 5: `/search` e `/contents`, com `category: news` e a janela de data). A leitura da Context.dev subiu de −1,7 para 33,9 depois de corrigir o runner (item 8), nas mesmas 60 respostas, sem chamada nova.
5. **Parallel Task à parte.** É um agente de pesquisa. A mediana foi 2,4 min por empresa (142800 ms na tabela de latência). Busca e extração ficam em segundos. A linha fica separada porque o tempo e o tipo de chamada são outros.
6. **Próximo passo barato.** Quando houver crédito, completar as 18 empresas que faltam na Firecrawl (e13–e30) e as 6 da Context.dev (e25–e30).
