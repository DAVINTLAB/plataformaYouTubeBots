# Padrão de Commits e PRs

Referência rápida baseada no [CONTRIBUTING.md](../../.github/CONTRIBUTING.md).
Este arquivo deve ser lido **antes de criar qualquer commit ou PR**.

---

## Commits

### Formato

```
tipo(escopo): descrição curta no imperativo
```

### Tipos

| Tipo | Quando usar |
|------|-------------|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `test` | Adição ou correção de testes |
| `docs` | Documentação apenas |
| `chore` | Build, CI, dependências, sem mudança de lógica |
| `refactor` | Refatoração sem mudança de comportamento |
| `style` | Formatação, espaços, ponto e vírgula |

### Regras

- **Separar commits por camada**: backend e frontend em commits distintos
- **Escopo obrigatório**: `feat(dashboard)`, `test(collect)`, `chore(ci)`
- **Descrição com corpo**: se houver mais de 3 mudanças, listar no corpo do commit
- **Co-Authored-By**: usar apenas `Co-Authored-By: Claude <noreply@anthropic.com>` — sem nome de modelo, sem contexto
- **Nunca** usar `--no-verify` ou `--amend` em commits já pushados

### Exemplo

```
feat(dashboard): adicionar endpoints e service da US-06

- 5 endpoints: /dashboard/global, /dashboard/video, /dashboard/user,
  /dashboard/bots, /dashboard/criteria-effectiveness
- Schemas Pydantic para request/response
- Service com agregações SQL batch e gráficos Plotly

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## PRs

### Branch

- Criar a partir de `dev` (nunca de `main`)
- Naming: `feature/*`, `fix/*`, `test/*`, `chore/*`, `quality/*`
- **Nunca** push direto em `dev` ou `main` — sempre branch → PR → merge

### Título

Mesmo formato do commit principal:

```
feat(dashboard): implementar US-06 — Dashboard de Análise
```

### Corpo (obrigatório, em português)

```markdown
## Resumo

- Descrição concisa das mudanças (bullets)

## Como testar

- [ ] Passo a passo para validar
- [ ] Cenários de erro ou edge cases

## Screenshots

(se houver mudanças visuais no frontend)
```

### Merge

- Usar **merge commit** (não squash, não rebase)
- Deletar branch após merge
- Para PR `dev → main`: sincronizar dev com main antes (`git pull origin main`)

---

## Checklist antes de abrir PR

- [ ] Branch criada a partir de `dev`
- [ ] `ruff check . && ruff format --check .` passando (backend)
- [ ] `bandit -r . --exclude tests` sem issues (backend)
- [ ] `pytest` com cobertura ≥ 90% (backend)
- [ ] `eslint . && prettier --check . && tsc --noEmit` passando (frontend)
- [ ] Nenhum segredo ou API key commitada
- [ ] Commits separados por camada (backend / frontend / docs)
