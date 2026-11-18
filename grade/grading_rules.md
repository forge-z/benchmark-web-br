# Regras de correção

Publicadas antes da rodada. O que não está aqui não entra na nota.

Há três desfechos para cada fato graduado:

- **certo**: a resposta confere com a regra abaixo
- **errado**: a resposta afirma um valor que a regra rejeita
- **branco**: o gabarito existe e a resposta veio vazia

Célula sem gabarito não entra no denominador, com uma exceção: CNPJ com dígito verificador inválido é errado mesmo sem gabarito, porque o dígito é uma regra pública, não um fato escondido.

O líquido é `100 * (certos − errados) / (certos + errados + brancos)`. Branco não soma e não subtrai. O intervalo de 95% é um bootstrap por item (consulta, URL ou empresa), 2000 reamostras, semente `20261118`.

O juiz de LLM está desligado. Sem `GRADE_LLM_API_KEY` e sem `--llm`, cargo e notícia recente não são graduados. Esta versão também não envia essas células a um modelo quando a chave existe: o gancho está no código e a chamada não foi ligada. Ligar o juiz é decisão em aberto.

## O que não pode aparecer

Se a resposta de qualquer campo trouxer e-mail ou telefone, o campo é errado. Nome de pessoa no cargo ou na notícia também é errado quando o juiz estiver ligado. O cargo, se um dia for preenchido no gabarito, é só o cargo.

## Prova 1, notícias

Cada item devolvido é uma célula no campo `data_na_janela`. A janela é de 48 horas, de `started_at` para trás.

- data ISO dentro da janela: certo
- data ausente: branco
- data que não parseia, ou fora da janela: errado
- zero itens: uma célula branco

Duplicata de URL é métrica à parte e não entra no líquido nesta versão. Latência e custo também não.

"Data correta" contra a página de origem só vale na prova 2, quando `data_esperada` está preenchida. Na prova 1 o gabarito de URL está vazio de propósito.

## Prova 2, leitura de página

Só entra campo com célula esperada preenchida.

- título: o texto dobrado (sem acento, caixa alta) de um contém o outro
- data: a mesma data civil em `America/Sao_Paulo`, ou diferença absoluta de até 26 horas
- preço: forma canônica `R$ 1.234,56` (ponto de milhar, vírgula decimal, duas casas)
- vendedor e disponibilidade: igualdade do texto dobrado

Texto vazio com gabarito preenchido é branco. Bloqueio, latência, custo e a taxa de ruído ficam em linhas com `grade` `metrica` e não entram no líquido. Ruído é a fração de linhas curtas que parecem menu ou link, calculada só quando o texto tem pelo menos cinco linhas.

## Prova 3, empresas

Campos determinísticos: `cnpj`, `razao_social`, `cidade`, `uf`, `porte`, `segmento`, `site`, `linkedin_empresa`.

- CNPJ: só os 14 dígitos, e o verificador precisa fechar. Formato de exibição `00.000.000/0000-00`
- razão social, cidade, UF e porte: igualdade do texto dobrado. A cidade do gabarito está sem acento quando veio da Receita
- segmento: o texto dobrado do CNAE contém ou é contido pela resposta
- site: o host, sem `www`
- LinkedIn: URL de `/company/`, sem perfil de pessoa

`cargo_decisor_comercial` e `noticia_recente` esperam o juiz. Nesta versão ficam de fora, salvo a vedação de e-mail e telefone, que já é determinística.

## O que o juiz faria, quando for ligado

O juiz lê `grading_rules.md` e a página citada. Não vê o nome da ferramenta. Um valor certo citado por uma página que diz outra coisa é errado. Página que não abre não torna o valor errado sozinha: se o valor confere com um gabarito lido em outra página, a citação fica sem apoio e o valor não cai para errado por isso.

Um branco honesto num fato que o gabarito marca como não encontrável seria certo. Este repositório ainda não tem fatos marcados assim.
