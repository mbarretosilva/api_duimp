# Extrator de Tributos DUIMP (API Siscomex)

Pipeline de ETL em Python para extração automatizada de dados fiscais de Declarações Únicas de Importação (DUIMP) via API do Portal Único Siscomex.

## 📌 Objetivo

Este projeto permite consultar a versão vigente de uma DUIMP, listar todos os seus itens (com suporte a paginação) e extrair os valores calculados de tributos (II, IPI, PIS, COFINS, etc.), consolidando tudo em um arquivo Excel (.xlsx) de forma "achatada" (flat).

## 🚀 Funcionalidades

- **Autenticação mTLS + JWT**: Conexão segura utilizando Certificado Digital A1 (e-CNPJ).
- **Descoberta de Versão**: Identifica automaticamente a versão mais recente do documento.
- **Paginação Automática**: Percorre todos os itens da DUIMP, independentemente da quantidade.
- **Flattening de Dados**: Transforma JSONs aninhados da API em registros planares prontos para análise ou importação em ERPs.
- **Resiliência HTTP**: Implementação de *Exponential Backoff* para lidar com limites de taxa (HTTP 429) e instabilidades (HTTP 503).
- **Exportação para Excel**: Gera relatórios detalhados por tributo utilizando `pandas` e `openpyxl`.

## 🛠️ Pré-requisitos

- Python 3.9+
- Certificado Digital A1 (arquivos `cert.pem` e `key.pem`)
- Acesso à API do Portal Único Siscomex (Serpro)

## 📦 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/api_duimp.git
   cd api_duimp
   ```

2. Crie e ative o ambiente virtual:
   ```powershell
   # Windows
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuração

1. **Certificados**:
   Coloque sua chave pública (`cert.pem`) e chave privada (`key.pem`) na pasta `certs/`.
   *Nota: Esta pasta está no .gitignore e nunca deve ser commitada.*

2. **Variáveis de Ambiente**:
   Crie ou edite o arquivo `.env` na raiz do projeto:
   ```env
   SISCOMEX_BASE_URL=https://api.siscomex.gov.br
   CERT_PUB_PATH=certs/cert.pem
   CERT_KEY_PATH=certs/key.pem
   DUIMP_NUMERO=12345678901234
   ```

## 🏃 Como usar

Com o ambiente ativado e as configurações prontas, execute:

```bash
python main.py
```

O script realizará o seguinte fluxo:
1. Autenticação no Portal Único.
2. Consulta da capa da DUIMP para obter a versão.
3. Extração da lista de itens.
4. Consulta individual de tributos por item.
5. Geração do arquivo `duimp_{numero}_tributos.xlsx`.

## 📊 Estrutura do Excel Gerado

O arquivo final contém as seguintes colunas:
- `numero_duimp`: Identificador da DUIMP.
- `versao_duimp`: Versão consultada.
- `numero_item`: Número do item na declaração.
- `ncm_item`: Código NCM do produto.
- `tipo_tributo`: Ex: II, IPI, PIS, COFINS.
- `base_calculo`: Valor base para o imposto.
- `aliquota`: Percentual aplicado.
- `valor_calculado`: Valor apurado pela Receita.
- `valor_a_recolher`: Valor final a ser pago.

## 📄 Requisitos Técnicos

Para detalhes sobre a arquitetura e especificações da API, consulte [docs/requisitos.md](docs/requisitos.md).

---
Desenvolvido para automação de processos de Comércio Exterior.
