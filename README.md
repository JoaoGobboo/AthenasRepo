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
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── vite.config.js
│   └── src/
└── docker-compose.yml
```

## Logs e monitoramento

- O backend utiliza o logger padrao do Python, configurado em `app.py`. Ajuste `LOG_LEVEL` no `.env` conforme necessario.
- Para acompanhar transacoes na blockchain, monitore os hashes retornados pelos endpoints de voto e criacao de eleicao.

## Proximos passos sugeridos

1. Integrar sistema de filas (ex.: Celery) para tratar transacoes de blockchain de forma assincrona.
2. Adicionar testes E2E cobrindo fluxo completo via Playwright ou Cypress.
3. Automatizar pipeline CI/CD para validar testes e builds antes do deploy.
