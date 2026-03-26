# Frontend — Guia para Agentes de IA

Contexto específico do frontend para desenvolvimento assistido por IA.
As regras gerais do projeto estão em `CLAUDE.md` na raiz — leia-o primeiro.

## Stack e tooling

- **React 18** com **TypeScript**, bundler **Vite**
- Visualizações: **Plotly.js** (dashboard US-06)
- Qualidade: ESLint + Prettier
- Auditoria de dependências: `npm audit`

## Estrutura de diretórios

```
frontend/src/
├── pages/        # Uma pasta/arquivo por User Story (US-01 a US-06)
├── components/   # Componentes reutilizáveis entre páginas
└── api/          # Funções de chamada ao backend (fetch/axios)
```

Cada página mapeia para um User Story. Não misture lógica de múltiplos USs em uma mesma página.

## Comunicação com o backend

- URL base configurada via variável de ambiente: `VITE_API_URL`
- Em produção: `VITE_API_URL=https://<backend-projeto>.vercel.app`
- Toda chamada HTTP deve passar pelos módulos em `src/api/` — nunca `fetch` inline em componentes
- Autenticação: header `Authorization: Bearer <token>` em todas as requisições protegidas
- Token JWT armazenado no cliente (localStorage ou context — definir padrão ao implementar)

## Regras de negócio no frontend

- **Anotação `bot`:** campo `justificativa` obrigatório — bloquear envio no frontend antes de chegar ao backend
- Classificações válidas para exibição/seleção: `bot` ou `humano` (sem `incerto`)
- Erros HTTP 422 do backend devem exibir mensagem amigável ao usuário

## Qualidade e segurança

```bash
cd frontend

# Lint
npx eslint . --ext .ts,.tsx

# Formatação
npx prettier --check .

# Checagem de tipos TypeScript
npx tsc --noEmit

# Auditoria de dependências (falha em severidade alta ou crítica)
npm audit --audit-level=high
```

Nunca commitar código que falhe em qualquer um desses checks.

## Comandos de desenvolvimento

```bash
cd frontend

# Servidor local
npm run dev

# Build de produção
npm run build

# Preview do build
npm run preview
```

## Convenções de código

- TypeScript estrito — sem `any` implícito
- Props de componentes tipadas com `interface` ou `type`
- Funções de API em `src/api/` devem retornar tipos explícitos, não `any`
- Variáveis de ambiente acessadas apenas via `import.meta.env.VITE_*`
- Nunca expor tokens, chaves ou dados sensíveis em logs de console em produção

## Deploy

- Deploy automático via Vercel a cada push na branch principal
- Variável `VITE_API_URL` configurada no Vercel Dashboard > Environment Variables
- Build command: `npm run build` | Output directory: `dist`
