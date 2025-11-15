# AthenasRepo - Sistema de Votacao em Blockchain

Projeto de TCC que implementa um sistema completo de votacao digital utilizando blockchain para garantir transparencia, auditabilidade e imutabilidade dos votos. O monorepo reune backend em Flask, frontend em React e infraestrutura de execucao com Docker Compose.

## Arquitetura

- **Backend (`backend/`)**: API REST em Flask com autenticacao via MetaMask, persistencia em MySQL e integracao com Ethereum (Goerli ou Sepolia) via Web3.py.
- **Frontend (`frontend/`)**: SPA React + Vite com Tailwind CSS, conectada ao backend e a MetaMask para interacao com o usuario.
- **Blockchain (`backend/src/blockchain/`)**: Contrato inteligente `Voting.sol`, script de deploy (`deploy_contract.py`) e utilitario (`contract_interaction.py`).
- **Infraestrutura**: `docker-compose.yml` orquestra backend, frontend e MySQL. Variaveis centralizadas em `.env`.

## Requisitos

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose (opcional, recomendado)

## Configuracao de ambiente

1. Copie o arquivo `.env.example` para `.env` na raiz do projeto e ajuste os valores.
2. Defina os dados sensiveis:
   - `SECRET_KEY` para emissao de JWT.
   - `RPC_URL`, `PRIVATE_KEY` e `ACCOUNT_ADDRESS` para acesso a rede Ethereum.
   - `CONTRACT_ADDRESS` apos o deploy do contrato.
3. Para desenvolvimento local sem blockchain, mantenha esses campos vazios: o backend opera em modo degradado.

## Execucao local

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app app.py --debug run
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Por padrao, o frontend espera o backend em `http://localhost:5000/api/v1`. Ajuste `VITE_API_URL` em `.env.local` se necessario.

## Execucao com Docker

```bash
docker-compose up --build
```

- Backend acessivel em `http://localhost:5000`.
- Frontend acessivel em `http://localhost:3000`.
- MySQL disponivel na rede interna Docker em `db:3306`.

## Contrato inteligente

1. Ajuste `RPC_URL`, `PRIVATE_KEY` e `ACCOUNT_ADDRESS` no `.env`.
2. Opcional: atualize a versao do compilador utilizando `SOLC_VERSION`.
3. Execute o script de deploy:

```bash
cd backend
python -m src.blockchain.deploy_contract
```

4. Copie o endereco exibido para `CONTRACT_ADDRESS` no `.env`.
5. Utilize `python -m src.blockchain.contract_interaction --help` para votar ou ler resultados direto da blockchain.

## Testes

No backend:

```bash
cd backend
pytest
```

Os testes utilizam SQLite em disco para executar sem dependencias externas.

## Resultados de testes de carga

Os arquivos abaixo em `backend/tests/results` foram gerados automaticamente pelo script `backend/tests/voting_load_test.py`:

| Teste | Data (UTC) | Votos | Carteiras | Blockchain | Requisições | Tempo (s) | Sucesso (%) | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `load_test_summary_20251110_181418.json` | 2025-11-10 18:14:18 | 10 | 12 | Não | 29 | 40.49 | 3.45 | Parcial |
| `load_test_summary_20251110_192950.json` | 2025-11-10 19:29:50 | 3 | 3 | Sim | 3 | 1.79 | 33.33 | Parcial |
| `load_test_summary_20251110_194125.json` | 2025-11-10 19:41:25 | 12 | 3 | Sim | 12 | 180.65 | 100.0 | Sucesso |
| `load_test_summary_20251110_210149.json` | 2025-11-10 21:01:49 | 100 | 8 | Sim | 100 | 1632.19 | 100.0 | Sucesso |

O campo "Tempo (s)" representa a duracao aproximada do teste (do primeiro ao ultimo voto registrado).

### Votos por carteira (testes de carga)

A tabela abaixo resume, para cada execucao de carga, quantos votos bem-sucedidos foram registrados por carteira (considerando apenas registros com `operation_status == "success"` nos arquivos `load_test_results_*.json`):

| Teste | Carteira | Votos bem-sucedidos |
| --- | --- | --- |
| `load_test_summary_20251110_181418.json` | `0xc4D0E9fFDF77c18ba0A2903c96BE004d76Bd221D` | 1 |
| `load_test_summary_20251110_192950.json` | `0x0B64bFCd4201276e1c7fcd77a214D0a0a538eA3f` | 1 |
| `load_test_summary_20251110_194125.json` | `0xcC8bD677e34F3121458d920b23c1309f39d538cB` | 4 |
| `load_test_summary_20251110_194125.json` | `0x0B64bFCd4201276e1c7fcd77a214D0a0a538eA3f` | 4 |
| `load_test_summary_20251110_194125.json` | `0x6F6C505ae08f7bB7Da6E38A898c7Bb824717a30D` | 4 |
| `load_test_summary_20251110_210149.json` | `0x69918BA35fAd5E5Fd8DCf5464D0d07a9d7519199` | 13 |
| `load_test_summary_20251110_210149.json` | `0xcC8bD677e34F3121458d920b23c1309f39d538cB` | 12 |
| `load_test_summary_20251110_210149.json` | `0x3224aA453cBd2d4746596462eA1f9C91a3656813` | 12 |
| `load_test_summary_20251110_210149.json` | `0x0B64bFCd4201276e1c7fcd77a214D0a0a538eA3f` | 13 |
| `load_test_summary_20251110_210149.json` | `0x0357C66D4e0136ABe64613CEE4d42515cDE034F1` | 13 |
| `load_test_summary_20251110_210149.json` | `0x6904AfC867c22294b1AaA24a5Dc6fda3dA374cb6` | 12 |
| `load_test_summary_20251110_210149.json` | `0x6F6C505ae08f7bB7Da6E38A898c7Bb824717a30D` | 13 |
| `load_test_summary_20251110_210149.json` | `0x6b9F6cddAaa5cEC5a91aEE6fCA3B5B19175bA885` | 12 |

## Reproduzindo os testes de carga

1. Garanta que o backend esteja rodando e acessivel (ex.: `docker-compose up --build` ou `flask --app app.py run`).
2. Configure no `.env` as variaveis de blockchain (`RPC_URL`, `CONTRACT_ADDRESS`, `PRIVATE_KEY`, `ACCOUNT_ADDRESS` e, se necessario, `CHAIN_ID`) e faca o deploy do contrato `Voting.sol` conforme a secao anterior.
3. Opcional: use o arquivo de exemplo `backend/tests/wallet.example.json` (ou copie-o para outro caminho) com `--wallet-file` para reutilizar enderecos de teste.
4. A partir da raiz do projeto, execute:

```bash
python backend/tests/voting_load_test.py \
  --votes 100 \
  --wallets 8 \
  --candidates Alice Bob Carol
```

5. Os arquivos `load_test_results_<timestamp>.json` e `load_test_summary_<timestamp>.json` serao criados automaticamente em `backend/tests/results`, podendo ser usados para atualizar a tabela acima.

## Estrutura do repositorio

```
AthenasRepo/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── src/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── blockchain/
│   │   └── utils/
│   └── tests/
│       ├── test_endpoints.py
│       ├── voting_load_test.py
│       ├── wallet.example.json
│       └── results/
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── vite.config.js
│   ├── .env.example
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── pages/
│       ├── components/
│       ├── services/
│       └── store/
├── docker-compose.yml
└── README.md
```

## Logs e monitoramento

- O backend utiliza o logger padrao do Python, configurado em `app.py`. Ajuste `LOG_LEVEL` no `.env` conforme necessario.
- Para acompanhar transacoes na blockchain, monitore os hashes retornados pelos endpoints de voto e criacao de eleicao.

## Proximos passos sugeridos

1. Integrar sistema de filas (ex.: Celery) para tratar transacoes de blockchain de forma assincrona.
2. Adicionar testes E2E cobrindo fluxo completo via Playwright ou Cypress.
3. Automatizar pipeline CI/CD para validar testes e builds antes do deploy.
