# Documento de Especificação: Extrator de Tributos DUIMP (API Siscomex) para Excel

## 1. Visão Geral e Objetivo
O objetivo deste projeto é construir um pipeline de extração de dados (ETL) em Python que consuma a API Pública do Portal Único Siscomex. A aplicação deve autenticar-se via mTLS, consultar uma Declaração Única de Importação (DUIMP), descobrir sua versão vigente, extrair os dados fiscais (valores calculados/tributos) de **todos os itens** que a compõem e consolidar essas informações de forma "achatada" (flattened) em uma planilha Excel (`.xlsx`).

Os dados de saída devem ser rigorosamente tipados para facilitar futura ingestão em sistemas de retaguarda e ERPs.

## 2. Requisitos de Conexão e Autenticação (Segurança)
A comunicação com o Serpro exige autenticação mútua (mTLS) aliada a um Token JWT. O Copilot deve configurar as requisições HTTP respeitando os seguintes critérios:

- **Certificado Digital A1:** A aplicação utilizará um e-CNPJ. O certificado original `.pfx` já terá sido previamente desmembrado em dois arquivos que devem ser parametrizados nas chamadas do módulo `requests`:
  - `cert.pem` (Chave Pública / Certificado)
  - `key.pem` (Chave Privada, descriptografada)
- **Parâmetro no Python:** A biblioteca `requests` deve usar o argumento `cert=('caminho/cert.pem', 'caminho/key.pem')` na sessão HTTP.
- **Headers Obrigatórios:**
  - Na chamada de autenticação: enviar o header `Role-Type: IMPEXP`.
  - Nas chamadas de dados subsequentes: enviar o header `Authorization: Bearer <TOKEN_JWT_RECEBIDO>`.
- Todas as credenciais e caminhos de arquivos devem ser lidos via variáveis de ambiente (`os.getenv`).

## 3. Endpoints Mapeados
**Base URL:** `https://api.siscomex.gov.br` *(Atenção: Usar o API Gateway, não o portal web).*

1. **Autenticação:** `POST /portal/api/autenticar`
2. **Capa da DUIMP (Descoberta de Versão):** `GET /duimp-api/api/ext/duimp/{numero_duimp}`
3. **Lista de Itens (Paginado):** `GET /duimp-api/api/ext/duimp/{numero_duimp}/{versao}/itens`
4. **Tributos por Item:** `GET /duimp-api/api/ext/duimp/{numero_duimp}/{versao}/itens/{numero_item}/valores-calculados`

## 4. Fluxo de Execução Lógica (Algoritmo)
O assistente deve construir o fluxo na exata ordem abaixo:

1. **Setup de Sessão:** Instanciar um objeto `requests.Session()` configurado com os certificados mTLS para reaproveitamento de conexão.
2. **Autenticação:** Realizar o POST para obter o Token JWT e injetá-lo nos *default headers* da sessão.
3. **Busca da Versão Atual:** Fazer a requisição à Capa da DUIMP usando apenas o número fornecido. Fazer o parse do JSON de retorno para extrair o inteiro que representa a versão atual do documento.
4. **Extração de Itens (Com Paginação):** Fazer um loop consultando a rota de itens. Como a DUIMP pode ter milhares de itens, o código **deve** lidar com a paginação da API do Serpro (verificando *query params* como `page` e `limit`, ou interpretando os metadados da resposta) até que o array completo de itens seja armazenado em memória.
5. **Loop de Tributação:** Iterar sobre a lista completa de números de itens. Para cada item, fazer a requisição na rota de `valores-calculados`.
6. **Transformação (Flattening):** Mapear a estrutura aninhada do JSON de tributos e achatar os dados em uma lista de dicionários padrão.
7. **Carga (Excel):** Converter a lista em um `pandas.DataFrame` e exportar via `to_excel()`.

## 5. Estrutura de Dados Desejada (Modelo Pandas/Excel)
O DataFrame final deve prever a granularidade por tributo. Exemplo de colunas necessárias:
- `numero_duimp` (String)
- `versao_duimp` (Int)
- `numero_item` (Int)
- `ncm_item` (String - se disponível na rota de itens ou tributos)
- `tipo_tributo` (String - Ex: II, IPI, PIS, COFINS)
- `base_calculo` (Float - converter para numérico, descartando símbolos monetários se houver)
- `aliquota` (Float)
- `valor_calculado` (Float)
- `valor_a_recolher` (Float)

## 6. Diretrizes de Código e Documentação Obrigatória
O assistente de IA deve aderir estritamente às seguintes regras durante a geração do código:

* **Documentação Explícita:** Todo módulo, classe e função gerada DEVE conter *docstrings* (padrão PEP 257 / Google Style) detalhando os argumentos, tipos de retorno e a regra de negócio aplicada.
* **Comentários Inline:** Inserir comentários explicativos acima de blocos de lógica complexa, especialmente no tratamento da paginação, no flattening do JSON e na configuração do mTLS.
* **Tratamento de Exceções e Resiliência:** * Implementar blocos `try/except` ao redor de cada chamada HTTP.
  * O Siscomex possui limites rígidos de requisição. É obrigatório implementar uma lógica de *rate limiting* (ex: `time.sleep` entre as chamadas no loop de itens) e/ou um mecanismo de *retry* (*exponential backoff* em caso de erro HTTP 429 ou 503).
* **Tipagem (Type Hints):** Utilizar type hints do Python em todas as assinaturas de funções (ex: `def get_duimp_version(session: requests.Session, duimp: str) -> int:`).
* **Modularidade:** Não criar um script monolítico. Separar as responsabilidades (ex: Classe `SiscomexAuth`, Classe `DuimpExtractor`, Função `export_to_excel`).

## 7. Instrução de Início para o Assistente
Por favor, analise as instruções acima. Inicie o desenvolvimento criando o esqueleto do projeto, definindo os *imports* necessários (`requests`, `pandas`, `os`, etc.) e implementando a classe responsável por configurar a sessão mTLS e realizar a autenticação. Lembre-se de documentar o código conforme a seção 6.
