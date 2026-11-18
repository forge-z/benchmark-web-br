# Regras de correção

Publicadas antes da rodada. O que não está aqui não entra na nota.

Há três desfechos para cada fato graduado:

- **certo**: a resposta confere com a regra abaixo
- **errado**: a resposta afirma um valor que a regra rejeita
- **branco**: o gabarito existe e a resposta veio vazia

Célula sem gabarito não entra no denominador, com uma exceção: CNPJ com dígito verificador inválido é errado mesmo sem gabarito, porque o dígito é uma regra pública, não um fato escondido.

O líquido é `100 * (certos − errados) / (certos + errados + brancos)`. Branco não soma e não subtrai. O intervalo de 95% é um bootstrap por item (consulta, URL ou empresa), 2000 reamostras, semente `20261118`.

A correção é só automática. Não há juiz de LLM no caminho padrão, e o código não chama modelo. Cargo e notícia recente não entram na nota. A revisão humana é uma amostra: `python -m grade.amostra --out amostra.csv --seed 20261118`. A população é ordenada antes do sorteio, então a mesma semente devolve as mesmas linhas. Com `--cells`, a amostra sai das células já graduadas.

## O que não pode aparecer

Se a resposta de qualquer campo trouxer e-mail ou telefone, o campo é errado. O cargo no gabarito, quando existe, é só o cargo, sem nome de pessoa.

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

- CNPJ: só os 14 dígitos, e o verificador precisa fechar. Formato de exibição `00.000.000/0000-00`. O valor esperado é o da matriz, regra abaixo
- razão social, cidade, UF e porte: igualdade do texto dobrado. A cidade do gabarito está sem acento quando veio da Receita. O porte gravado é o texto da BrasilAPI (`DEMAIS` ou `EMPRESA DE PEQUENO PORTE`), não a sigla `EPP`
- segmento: o texto dobrado do CNAE da matriz contém ou é contido pela resposta
- site: o host, sem `www`
- LinkedIn: URL de `/company/`, sem perfil de pessoa

O CNPJ do gabarito é sempre o da matriz. Confere-se o campo `descricao_identificador_matriz_filial` na BrasilAPI. Se a linha tiver uma filial, troca-se pelo CNPJ da matriz (mesma raiz de 8 dígitos). O sufixo `/0001-xx` nem sempre é a matriz: busca-se o estabelecimento com identificador MATRIZ (pode ser `/0002-xx`, `/0003-xx`, `/0011-xx`, `/0014-xx` etc.). Cidade, UF, porte e segmento passam a ser os da matriz. Responder com CNPJ de filial é errado, mesmo que os 14 dígitos e o verificador fechem.

Cidade, UF, porte e segmento vêm do estabelecimento matriz na BrasilAPI. Quando o município ou a UF da CVM divergem da BrasilAPI, o gabarito usa a BrasilAPI (cadastro da Receita). A divergência fica na coluna `notas` e não entra na comparação. O segmento do gabarito é o CNAE principal da matriz na BrasilAPI, não o da CVM nem o de uma filial.

`cargo_decisor_comercial` e `noticia_recente` não têm regra automática. Ficam fora do líquido, salvo a vedação de e-mail e telefone, que já marca o campo como errado. Quem quiser olhá-los usa a amostra humana, não um modelo.
