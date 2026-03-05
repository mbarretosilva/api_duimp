# Repository Instructions for Copilot Sessions

## Build, test, and lint commands
- **Build/Test/Lint:** ainda não há comandos definidos (nenhum pacote/arquivo de teste está presente). Quando o projeto avançar, execute o `pip install -r requirements.txt` antes de rodar *anything* e use `python -m pytest` para os testes resgatados.
- **Execução inicial:** execute `python main.py` dentro do `.venv` ativado para validar que o esqueleto carga sem erros.

## High-level architecture
- **Objetivo:** Extrair a versão vigente de uma DUIMP, listar todos os itens (paginação obrigatória), buscar os tributos calculados e consolidar os dados em um Excel tipo pandas.DataFrame.
- **Fluxo previsto:** (1) configurar `SiscomexAuth` com `requests.Session`, certificados mTLS e header `Role-Type: IMPEXP`, (2) autenticar e injetar `Authorization: Bearer <JWT>` na sessão, (3) consultar a capa da DUIMP para descobrir a versão atual, (4) percorrer a rota /itens com paginação para montar a lista completa de itens, (5) iterar cada item e colher `/valores-calculados`, (6) achatar os JSONs para registros por tributo e (7) exportar com `pandas.DataFrame.to_excel()`.
- **Documentação de requisitos:** consulte `docs/requisitos.md` para a especificação completa fornecida pelo time (mTLS, headers, dados esperados e diretrizes de documentação).

## Key conventions
- **Modularização:** espalhe responsabilidades entre classes (ex: `SiscomexAuth`, `DuimpExtractor`) e funções utilitárias; evite scripts monolíticos.
- **Docstrings e tipagem:** cada módulo/classe/função precisa de docstring PEP 257/Google Style explicando argumentos, retornos e negócio; use type hints em todas as assinaturas.
- **Comentários:** acrescente breves comentários antes de blocos complexos (paginação, flattening, backoff).
- **Variáveis sensíveis:** leia caminhos e credenciais via `os.getenv` (armazenados em `.env`); não comite `certs/` nem `.env`.
- **Resiliência HTTP:** todas as requisições devem estar em blocos `try/except`, com rate limiting (sleep ou backoff) e retentativas exponenciais para 429/503.
- **Ambiente:** não altere `.venv`; use-o apenas para instalação/execução.

## Project scaffolding
- `main.py` é o ponto de partida sugerido (esqueleto já criado); novos módulos ou pacotes devem ser importados a partir dele.
- `docs/requisitos.md` é o único documento de requisitos. Use este material para entender os dados esperados antes de escrever código.
- `certs/` existe apenas como placeholder para `cert.pem` e `key.pem`. Nunca comite os arquivos reais; mantenha-os fora do controle de versão.
- `.gitignore` já impede que `.venv/`, `certs/` e `.env` sejam versionados.
