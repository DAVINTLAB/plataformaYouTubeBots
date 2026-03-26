# US-00 — Infraestrutura, CI/CD e Segurança de Dependências

## Objetivo

Configurar o repositório com pipelines de qualidade e segurança automatizados desde o início,
garantindo que nenhum código com problemas de lint, tipagem ou vulnerabilidades conhecidas
chegue à branch principal.

---

## Critérios de aceite

- Push direto na branch `main` é bloqueado — todo código entra via PR
- CI falha se houver erro de lint, tipagem, vulnerabilidade de severidade alta/crítica ou cobertura abaixo de 80%
- Dependabot abre PRs automáticos para atualizações de segurança
- Pre-commit hooks impedem commit local com código fora do padrão
- Todas as dependências do backend têm versões **fixas** no `requirements.txt` (sem `>=`)

---

## Arquivos a criar

### `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: /backend
    schedule:
      interval: weekly
    open-pull-requests-limit: 10
    groups:
      security-updates:
        patterns: ["*"]
        update-types: ["patch"]
    automerge: true  # merge automático para patches

  - package-ecosystem: npm
    directory: /frontend
    schedule:
      interval: weekly
    open-pull-requests-limit: 10
    groups:
      security-updates:
        patterns: ["*"]
        update-types: ["patch"]
    automerge: true
```

---

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint (ruff)
        run: ruff check .

      - name: Format check (ruff)
        run: ruff format --check .

      - name: Security analysis (bandit)
        run: bandit -r . -x tests/

      - name: Dependency audit (pip-audit)
        run: pip-audit

      - name: Tests with coverage
        run: pytest --cov=. --cov-fail-under=80
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL_TEST }}
          SECRET_KEY: test-secret-key-for-ci

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint (eslint)
        run: npx eslint . --ext .ts,.tsx

      - name: Format check (prettier)
        run: npx prettier --check .

      - name: Type check (tsc)
        run: npx tsc --noEmit

      - name: Dependency audit
        run: npm audit --audit-level=high

      - name: Build
        run: npm run build
        env:
          VITE_API_URL: https://placeholder.vercel.app
```

---

### `.pre-commit-config.yaml` (raiz)

```yaml
repos:
  - repo: local
    hooks:
      # Backend
      - id: ruff-lint
        name: Ruff lint
        entry: ruff check
        language: python
        types: [python]
        files: ^backend/

      - id: ruff-format
        name: Ruff format
        entry: ruff format --check
        language: python
        types: [python]
        files: ^backend/

      - id: bandit
        name: Bandit security
        entry: bandit -r
        language: python
        types: [python]
        files: ^backend/
        exclude: ^backend/tests/

      # Frontend
      - id: eslint
        name: ESLint
        entry: bash -c 'cd frontend && npx eslint --ext .ts,.tsx'
        language: system
        files: ^frontend/.*\.(ts|tsx)$
        pass_filenames: false

      - id: prettier
        name: Prettier
        entry: bash -c 'cd frontend && npx prettier --check'
        language: system
        files: ^frontend/.*\.(ts|tsx|json|css)$
        pass_filenames: false
```

---

### `backend/ruff.toml`

```toml
target-version = "py311"
line-length = 88

[lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "S",   # flake8-bandit (security)
    "UP",  # pyupgrade
]
ignore = [
    "S101", # assert em testes é ok
]

[lint.per-file-ignores]
"tests/**" = ["S", "B"]

[format]
quote-style = "double"
indent-style = "space"
```

---

### `frontend/.eslintrc.json`

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unused-vars": "error",
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  },
  "env": { "browser": true, "es2022": true }
}
```

---

### `frontend/.prettierrc`

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

---

## Proteção de branch `main`

Configurar via GitHub > Settings > Branches > Branch protection rules:

- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - Status checks obrigatórios: `backend`, `frontend`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

---

## `requirements.txt` — convenção obrigatória

Todas as dependências com versão **exata** (sem `>=`, `~=` ou `^`):

```
fastapi==0.115.0
uvicorn==0.30.6
sqlalchemy==2.0.35
alembic==1.13.3
pydantic==2.9.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.2
pytest==8.3.3
pytest-cov==5.0.0
ruff==0.6.9
bandit==1.7.10
pip-audit==2.7.3
```

---

## Testes obrigatórios

A US-00 não tem lógica de aplicação — seus "testes" são as próprias verificações do CI.
Não há dublês de teste aqui: tudo é integração real contra arquivos de configuração.

| Verificação                          | Como testar                                           |
|--------------------------------------|-------------------------------------------------------|
| Ruff detecta erro de lint            | Introduzir linha com erro (`x=1+1` sem espaços) e rodar `ruff check` — deve falhar |
| Ruff detecta erro de formato         | Introduzir indentação errada e rodar `ruff format --check` — deve falhar |
| Bandit detecta vulnerabilidade       | Adicionar `subprocess.call(user_input, shell=True)` e rodar `bandit` — deve falhar |
| ESLint detecta erro TypeScript       | Adicionar variável `any` explícita e rodar `eslint` — deve falhar |
| `tsc --noEmit` detecta tipo errado   | Atribuir `string` a campo `number` e rodar `tsc` — deve falhar |
| CI passa com código limpo            | PR com código válido — todos os jobs devem ficar verdes |
| Push direto em `main` é bloqueado    | Verificar branch protection rules no GitHub após configuração |
| Dependabot abre PR para patch        | Aguardar primeira varredura semanal ou acionar via GitHub |

> Nota: estes são testes manuais de validação da configuração — não entram no `pytest`.
> O pipeline de CI em si é o artefato testável desta US.

## Dependências com outras USs

- Esta US não depende de nenhuma outra
- Todas as outras USs dependem desta — o CI deve estar verde antes de qualquer merge
