# Índice de snapshots

O índice guarda, por página buscada pelo baseline, a URL, o SHA-256 dos bytes, a data, o tamanho, a ferramenta, a prova e o `item_id`. Uma linha JSON por captura, em `index.jsonl`, criado na hora da execução.

O corpo fica em `snapshots/`, na raiz do repositório, e o `.gitignore` deixa essa pasta de fora. Não redistribuímos HTML, PDF nem página de marketplace.

Nesta versão só o baseline de leitura grava snapshot, porque é o único runner que baixa a página ele mesmo. Os outros devolvem extrato do fornecedor, e o extrato não é tratado como cópia da página.
