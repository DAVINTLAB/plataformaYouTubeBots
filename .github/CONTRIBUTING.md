# Guia de Contribuição

## Modelo de branches (Gitflow)

```
main         produção — releases estáveis, marcadas com tag vX.Y.Z
dev          integração — alvo de todo PR de feature concluída
feature/*    desenvolvimento de uma US ou tarefa
fix/*        correção de bug não urgente
hotfix/*     correção urgente direto de main
release/*    preparação de release
chore/*      infra, CI, dependências, documentação
```

## Fluxo padrão

### 1. Criar branch a partir de `dev`

```bash
git checkout dev
git pull origin dev
git checkout -b feature/us-02-collect
```

### 2. Desenvolver e commitar

Mensagens de commit seguem [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(collect): adicionar endpoint POST /collect com paginação
fix(auth): corrigir expiração de token não retornando 401
test(annotate): adicionar testes de conflito com stub de usuário
docs(skills): atualizar contrato de API da US-03
chore(ci): aumentar threshold de cobertura para 85%
```

Formato: `tipo(escopo): descrição curta no imperativo`

| Tipo     | Quando usar                                      |
|----------|--------------------------------------------------|
| `feat`   | Nova funcionalidade                              |
| `fix`    | Correção de bug                                  |
| `test`   | Adição ou correção de testes                     |
| `docs`   | Documentação apenas                              |
| `chore`  | Build, CI, dependências, sem mudança de lógica   |
| `refactor` | Refatoração sem mudança de comportamento       |

### 3. Abrir PR para `dev`

- Título: mesmo formato do commit (`feat(us-02): ...`)
- CI deve estar verde antes do merge
- Ao menos 1 aprovação do time

**Formato do corpo do PR:**

```markdown
## Resumo

- Descrição concisa das mudanças (bullets)

## Como testar

- [ ] Passo a passo para validar as mudanças
- [ ] Cenários de erro ou edge cases relevantes

## Screenshots

(se houver mudanças visuais no frontend)
```

> Escrever em português. Termos técnicos (endpoint, branch, merge) podem ficar em inglês.

### 4. Merge

- Usar **merge commit** (não squash, não rebase) — preserva histórico de feature
- Deletar a branch de feature após o merge

### 5. Release

Quando `dev` estiver pronto para produção:

```bash
git checkout -b release/v1.0.0 dev
# ajustes finais, bump de versão
git checkout main && git merge --no-ff release/v1.0.0
git tag -a v1.0.0 -m "Release v1.0.0"
git checkout dev && git merge --no-ff release/v1.0.0
git branch -d release/v1.0.0
```

### Hotfix (bug urgente em produção)

```bash
git checkout -b hotfix/jwt-expiry-crash main
# corrigir
git checkout main && git merge --no-ff hotfix/jwt-expiry-crash
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git checkout dev && git merge --no-ff hotfix/jwt-expiry-crash
git branch -d hotfix/jwt-expiry-crash
```

## Checklist antes de abrir PR

- [ ] Branch criada a partir de `dev` (não de `main`)
- [ ] `ruff check .` e `ruff format --check .` passando (backend)
- [ ] `bandit -r .` sem issues novas (backend)
- [ ] `eslint` e `prettier --check` passando (frontend)
- [ ] `tsc --noEmit` sem erros (frontend)
- [ ] `pytest` com cobertura ≥ 80% (backend)
- [ ] Nenhum segredo ou API key commitada
- [ ] Migration Alembic gerada se modelo SQLAlchemy foi alterado
