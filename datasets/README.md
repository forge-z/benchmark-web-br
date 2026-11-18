# Datasets

Conferidos em 2026-11-18, a partir de páginas que abriram neste ambiente, da BrasilAPI (`/api/cnpj/v1`) e do cadastro público de companhias abertas da CVM (`cad_cia_aberta.csv`). Nada aqui foi inventado para completar a cota. Célula vazia com `gabarito_status` `a revisar` é lacuna, não zero.

Licença destes arquivos: CC BY 4.0 (`../LICENSE-DATA`).

## Contagem

| Arquivo | Linhas | Completo | A revisar |
|---|---:|---:|---:|
| `sites_noticias.csv` | 25 | 25 homepages HTTP 200 | 0. RSS gravado em 17; 8 sem feed confirmado |
| `consultas_noticias.csv` | 40 | 40 textos de consulta | 40 sem URL esperada, de propósito: a janela de 48 h anda com a execução |
| `urls_leitura.csv` | 31 | 20 notícias com título e data | 10 PDFs da Anfavea (URL abriu; 4 com título lido e 6 sem título) e 1 produto |
| `empresas.csv` | 30 | 22 com bloco cadastral (CNPJ, razão, cidade, UF, porte, segmento) | 8 |
| `perguntas_empresas.csv` | 10 | 10 perguntas | 0. São o instrumento, não o gabarito |

A meta da prova 2 era cerca de 60 URLs: 20 notícias, 10 PDFs e 30 páginas de produto. Notícias e PDFs fecharam. Páginas de produto: **1 de 30**. Mercado Livre, Americanas, Kabum e Shopee abriram a busca, mas o HTML não trazia links de produto (página montada no cliente). Amazon, Magalu, Casas Bahia e Carrefour não abriram daqui (403 ou 503). A única URL de produto é a da Kabum que o HTML da busca citava; o título e o preço não foram amarrados ao produto, então o gabarito desses campos ficou vazio.

## Empresas

Faixa de presença, observada neste ambiente, não estimada:

- `rica` (19): CNPJ confirmado na BrasilAPI e site oficial que abriu
- `media` (2): Tupy e Portobello. O CNPJ confere, o site abriu, e a cidade da CVM não é a mesma da BrasilAPI. O gabarito de cidade e UF usa a BrasilAPI (SAO PAULO/SP e TIJUCAS/SC). O segmento da Tupy continua vazio
- `fraca` (5): distribuidores regionais de ferramenta de corte cujo HTML não traz CNPJ
- `a revisar` (4): Intelbras e Marcopolo (cadastro ok, site 403) e OSG e Tungaloy (site abriu, CNPJ não conferido)

LinkedIn da empresa, cargo e notícia recente estão vazios em todas as linhas. Páginas de distribuidor chegam a listar gente, e-mail e telefone; nada disso foi copiado.

`porte` `DEMAIS` é o código da Receita para quem não é MEI, ME nem EPP. Não foi traduzido para "grande".

## O que o runner recebe

O runner de notícias lê `consulta`. O de leitura lê `url`. O de empresas lê `nome` e as perguntas. Colunas de gabarito não entram no pedido.
