# Datasets

Conferidos em 2026-11-18, a partir de páginas que abriram neste ambiente, da BrasilAPI (`/api/cnpj/v1`) e do cadastro público de companhias abertas da CVM (`cad_cia_aberta.csv`). Nada aqui foi inventado para completar a cota. Célula vazia com `gabarito_status` `a revisar` é lacuna, não zero.

Licença destes arquivos: CC BY 4.0 (`../LICENSE-DATA`).

## Contagem

| Arquivo | Linhas | Completo | A revisar |
|---|---:|---:|---:|
| `sites_noticias.csv` | 25 | 25 homepages HTTP 200 | 0. RSS gravado em 17; 8 sem feed confirmado |
| `consultas_noticias.csv` | 40 | 40 textos de consulta | 40 sem URL esperada, de propósito: a janela de 48 h anda com a execução |
| `urls_leitura.csv` | 60 | 20 notícias com título e data, e 26 produtos com título | 10 PDFs da Anfavea (URL abriu; 4 com título lido e 6 sem título) e 4 produtos da Shopee |
| `empresas.csv` | 30 | 29 com bloco da matriz (CNPJ, razão, cidade, UF, porte, segmento) | 1, a KSC Ferramentas, sem CNPJ |
| `perguntas_empresas.csv` | 10 | 10 perguntas | 0. São o instrumento, não o gabarito |

A meta da prova 2 era cerca de 60 URLs: 20 notícias, 10 PDFs e 30 páginas de produto. Notícias e PDFs fecharam. Páginas de produto: **30 linhas, 26 verificadas**. Kabum, Mercado Livre, Amazon.com.br, Casas Bahia, Americanas e Magalu têm 1 ou 5 fichas com título. A Kabum (l31) tem título, preço `R$ 49,98` e vendedor. Quatro URLs da Shopee estão a revisar, sem título nem preço, porque a página caiu na verificação de tráfego. Falta 1 URL da Shopee; não foi inventada. Célula de preço, vendedor ou disponibilidade vazia não entra na nota.

## Empresas

Faixa de presença, observada neste ambiente, não estimada:

- `rica` (25): CNPJ da matriz confirmado na BrasilAPI e site oficial que abriu
- `media` (2): Tupy e Portobello. As duas têm CNPJ de matriz e site. Portobello continua com município divergente entre CVM (Florianópolis) e BrasilAPI (Tijucas). A faixa da Tupy não foi promovida nesta rodada
- `fraca` (1): KSC Ferramentas. O site abriu; o CNPJ não foi amarrado
- `a revisar` (2): Intelbras e Marcopolo. O cadastro está ok e o site não abriu daqui

O CNPJ gravado é o da matriz (`descricao_identificador_matriz_filial` na BrasilAPI). Três filiais foram trocadas: Tupy `84.683.374/0003-00`, Romi `56.720.428/0014-88`, Randoncorp `89.086.144/0011-98`. LinkedIn da empresa, só `/company/`, entrou em Kennatech, Repatri e BFT. O cargo entrou só na Kennatech (“Diretor Técnico e Comercial”), sem nome de pessoa. Notícia recente continua vazia. Páginas que listavam gente, e-mail e telefone não foram copiadas.

`porte` vem no texto da BrasilAPI. Quase todas as linhas preenchidas são `DEMAIS`. A Repatri é `EMPRESA DE PEQUENO PORTE`. Não foi traduzido para "grande" nem para a sigla EPP.

## O que o runner recebe

O runner de notícias lê `consulta`. O de leitura lê `url`. O de empresas lê `nome` e as perguntas. Colunas de gabarito não entram no pedido.
