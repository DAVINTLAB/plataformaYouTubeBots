# Skills — Guias de Implementação por User Story

Cada arquivo detalha o contrato de API, schemas de banco, lógica de service,
componentes React sugeridos, casos de erro e dependências com outras USs.

| Arquivo                       | US    | Escopo                                          |
|-------------------------------|-------|-------------------------------------------------|
| [us-00-infra.md](us-00-infra.md)           | US-00 | CI/CD, pre-commit hooks, Dependabot, proteção de branch |
| [us-01-auth.md](us-01-auth.md)             | US-01 | Login, logout, gestão de usuários (admin/user)  |
| [us-02-collect.md](us-02-collect.md)       | US-02 | Coleta de comentários via YouTube Data API      |
| [us-03-clean.md](us-03-clean.md)           | US-03 | Seleção estatística/comportamental de usuários suspeitos |
| [us-04-annotate.md](us-04-annotate.md)     | US-04 | Anotação de comentários por usuário do YouTube  |
| [us-05-review.md](us-05-review.md)         | US-05 | Desempate de conflitos e revisão de bots (admin)|
| [us-06-dashboard.md](us-06-dashboard.md)   | US-06 | Dashboard global e individual com Plotly        |

## Fluxo entre USs

```
US-00 (Infra) — base para todas as outras

US-01 (Auth)  — JWT necessário em todas as outras

US-02 (Coleta) → US-03 (Limpeza) → US-04 (Anotação) → US-05 (Desempate)
                                            └─────────────────────────→ US-06 (Dashboard)
```

## Papéis

| Role    | Acesso                                                        |
|---------|---------------------------------------------------------------|
| `admin` | Tudo: gestão de usuários, coleta, limpeza, anotação, desempate, dashboard |
| `user`  | Coleta, limpeza, anotação, dashboard                          |
