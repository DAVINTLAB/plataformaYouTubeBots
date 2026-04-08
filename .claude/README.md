# .claude/ — Documentação do Projeto

## Estrutura

```
.claude/
├── padroes/                     # Guias de desenvolvimento por camada
│   ├── backend.md               # Arquitetura, SOLID, testes, import/export
│   ├── frontend.md              # Layout, componentes, hooks, Tailwind v3
│   └── ux-ui.md                 # 10 heurísticas de Nielsen, cores, tabelas
│
├── skills/                      # Specs de implementação
│   ├── README.md                # Índice com fluxo entre USs
│   ├── us/                      # Uma spec por User Story (US-00 a US-07)
│   ├── qualidade/               # Qualidade e segurança (OWASP, testes, monitoramento)
│   └── readme-gen.md            # Geração de READMEs
│
├── requisitos.md                # Épico + User Stories originais
├── backlog.md                   # Tarefas futuras (fases 2-5 de qualidade)
└── README.md                    # Este arquivo
```

## Como contribuir

Seguir rigorosamente o [CONTRIBUTING.md](../.github/CONTRIBUTING.md):

- **Branch**: criar a partir de `dev` (`feature/*`, `fix/*`, `chore/*`)
- **Commits**: `tipo(escopo): descrição` — Conventional Commits
- **PR**: título no mesmo formato, corpo com `## Resumo` + `## Como testar`
- **Merge**: merge commit (não squash), deletar branch após merge
- **Nunca** push direto em `dev` ou `main`

## Referência rápida

| Preciso de... | Onde encontrar |
|---------------|----------------|
| Padrões de backend | [padroes/backend.md](padroes/backend.md) |
| Padrões de frontend | [padroes/frontend.md](padroes/frontend.md) |
| Padrões de UX/UI | [padroes/ux-ui.md](padroes/ux-ui.md) |
| Como fazer commits e PRs | [padroes/commits-e-prs.md](padroes/commits-e-prs.md) |
| Spec de uma US | [skills/us/](skills/us/) |
| Roadmap de qualidade | [skills/qualidade/quality-security.md](skills/qualidade/quality-security.md) |
| Backlog de tarefas | [backlog.md](backlog.md) |
| Requisitos originais | [requisitos.md](requisitos.md) |
| Como fazer PR | [../.github/CONTRIBUTING.md](../.github/CONTRIBUTING.md) |
