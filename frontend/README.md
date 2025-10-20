# Athenas Frontend

Aplicação React responsável pela interface do Sistema de Votação em Blockchain.

## Requisitos

- Node.js 18+
- npm

## Scripts

- `npm install` para instalar dependências
- `npm run dev` para iniciar o servidor de desenvolvimento em `http://localhost:3000`
- `npm run build` para gerar build de produção

## Variáveis de ambiente

Crie um arquivo `.env` (ou `.env.local`) com:

```
VITE_API_URL=http://localhost:5000/api/v1
VITE_CONTRACT_ADDRESS=<endereco_do_contrato>
VITE_CONTRACT_ABI=<json_abi_em_string>
```

## Tailwind CSS

O projeto já está configurado com Tailwind via PostCSS. As classes utilitárias podem ser utilizadas nos componentes React.
