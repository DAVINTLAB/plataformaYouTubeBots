# AGENTS.md — Instruções para Agentes de IA

Este arquivo define como agentes de IA devem se comportar neste repositório.
Leia também `CLAUDE.md` (regras gerais) e os arquivos em `.claude/` (contexto por camada).

## Visão geral do projeto

Sistema de detecção de bots em comentários do YouTube para pesquisa científica.
Desenvolvido no DaVint Lab / PUCRS como projeto de Iniciação Científica.

**Documentação de referência por escopo:**

| Escopo                  | Arquivo                              |
|-------------------------|--------------------------------------|
| Geral                   | `CLAUDE.md`                          |
| Backend                 | `.claude/backend.md`                 |
| Frontend                | `.claude/frontend.md`                |
| US-01 — Auth            | `.claude/skills/us-01-auth.md`       |
| US-02 — Coleta          | `.claude/skills/us-02-collect.md`    |
| US-03 — Limpeza         | `.claude/skills/us-03-clean.md`      |
| US-04 — Anotação        | `.claude/skills/us-04-annotate.md`   |
| US-05 — Desempate       | `.claude/skills/us-05-review.md`     |
| US-06 — Dashboard       | `.claude/skills/us-06-dashboard.md`  |

Ao implementar uma US, leia o arquivo de skill correspondente — ele contém o contrato de API,
schemas de banco, lógica de service, componentes React sugeridos e casos de erro.

## Regras gerais para agentes

### Antes de qualquer mudança

1. Leia o arquivo relevante em `.claude/` para o escopo da tarefa
2. Verifique o código existente antes de propor alterações
3. Não crie arquivos desnecessários — prefira editar o que já existe

### Qualidade obrigatória

Todo código gerado deve passar nos checks de qualidade da camada correspondente:

- **Backend:** `ruff check`, `ruff format --check`, `bandit`, `pip-audit`, `pytest` (≥80% cobertura)
- **Frontend:** `eslint`, `prettier --check`, `tsc --noEmit`, `npm audit --audit-level=high`

Nunca sugira ou gere código que ignore esses checks (`--no-verify`, `// eslint-disable`, `# noqa` sem justificativa).

### Segurança — regras inegociáveis

- Senhas sempre com bcrypt via `passlib` — nunca texto plano
- API keys recebidas como `SecretStr` por requisição — nunca persistidas em banco, log ou variável de ambiente
- Sem SQL raw com interpolação de strings — usar ORM (SQLAlchemy) ou parâmetros vinculados
- Sem `eval()`, `exec()`, ou deserialização de dados não confiáveis
- Sem segredos hardcoded em código ou arquivos de configuração commitados

### Arquitetura — não violar

- Lógica de negócio fica em `services/` — nunca inline em routers ou componentes
- Chamadas HTTP do frontend ficam em `src/api/` — nunca inline em componentes
- Validação de entrada no backend via schemas Pydantic
- Toda divergência de anotação exige resolução explícita do admin — não implementar resolução automática por maioria

### Tamanho e escopo das mudanças

- Não adicione funcionalidades além do que foi pedido
- Não refatore código que não faz parte da tarefa
- Não adicione docstrings, comentários ou type annotations em código que não foi alterado
- Três linhas similares são melhores que uma abstração prematura

## Convenção de branches (Gitflow)

```
main         produção — código estável, releases marcadas com tag
dev          integração — alvo de todo PR de feature concluída
feature/*    desenvolvimento de uma US ou tarefa específica
hotfix/*     correção urgente direto de main
release/*    preparação de release (bump de versão, changelog)
```

### Regras

- **Nunca commitar direto em `main` ou `dev`** — todo código entra via PR
- Branch de feature criada a partir de `dev`: `git checkout -b feature/us-02-collect dev`
- PR de feature sempre aponta para `dev` — nunca para `main`
- Após conclusão e revisão da feature, merge em `dev` com **merge commit** (não squash) para preservar histórico
- Quando `dev` estiver estável para release: PR de `dev` → `main` + tag `vX.Y.Z`
- Hotfix: branch a partir de `main`, PR para `main` **e** cherry-pick ou PR para `dev`

### Nomenclatura de branches

| Tipo      | Padrão                        | Exemplos                          |
|-----------|-------------------------------|-----------------------------------|
| Feature   | `feature/us-NN-descricao`     | `feature/us-02-collect`           |
| Fix       | `fix/descricao-curta`         | `fix/api-key-leak-log`            |
| Hotfix    | `hotfix/descricao-curta`      | `hotfix/jwt-expiry-crash`         |
| Release   | `release/vX.Y.Z`              | `release/v1.0.0`                  |
| Infra/CI  | `chore/descricao-curta`       | `chore/ci-coverage-threshold`     |

### Para agentes de IA

Ao iniciar uma tarefa, verifique em qual branch está antes de criar arquivos ou commitar:

```bash
git branch --show-current   # deve ser uma branch feature/* ou fix/*
git log --oneline -5        # confirmar ponto de partida
```

Nunca crie commits diretamente em `main` ou `dev`.
Se a branch atual for `main` ou `dev`, crie uma nova branch antes de qualquer alteração:
```bash
git checkout -b feature/us-XX-descricao dev
```

## Fluxo de User Stories (US)

```
US-01: Auth          → routers/auth.py      + pages/Auth
US-02: Coleta        → routers/collect.py   + pages/Collect
US-03: Limpeza       → routers/clean.py     + pages/Clean
US-04: Anotação      → routers/annotate.py  + pages/Annotate
US-05: Desempate     → routers/review.py    + pages/Review     [role: admin]
US-06: Dashboard     → routers/dashboard.py + pages/Dashboard
```

Ao trabalhar em uma US, mantenha backend e frontend alinhados ao mesmo contrato de API.

## Banco de dados e migrations

- Nunca altere modelos SQLAlchemy sem gerar uma migration Alembic correspondente
- Nunca edite migrations já aplicadas em produção — crie uma nova
- Teste migrations localmente com `alembic upgrade head` antes de propor o código

## Variáveis de ambiente

Variáveis necessárias — nunca hardcode, nunca commite valores reais:

| Variável                    | Onde usar       | Como obter                        |
|-----------------------------|-----------------|-----------------------------------|
| `DATABASE_URL`              | Backend         | Injetada pelo Vercel/Neon          |
| `SECRET_KEY`                | Backend         | Vercel Dashboard > Env Vars        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend       | Vercel Dashboard > Env Vars        |
| `VITE_API_URL`              | Frontend        | Vercel Dashboard > Env Vars        |

## Constraints de infraestrutura

- Timeout de **10 segundos** por request no Vercel free tier
- Operações longas (coleta de comentários, limpeza de dataset) devem ser assíncronas ou paginadas
- Banco Neon: **0.5 GB** de armazenamento, scale-to-zero — evitar queries ineficientes ou dados redundantes
