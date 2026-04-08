# Skills — Guias de Implementação

## User Stories (`us/`)

Cada arquivo detalha o contrato de API, schemas, lógica de service, componentes React e testes.

| Arquivo | US | Status |
|---------|-----|--------|
| [us-00-infra.md](us/us-00-infra.md) | US-00 · Infraestrutura e CI/CD | Concluída |
| [us-01-auth.md](us/us-01-auth.md) | US-01 · Autenticação e gestão de usuários | Concluída |
| [us-02-collect.md](us/us-02-collect.md) | US-02 · Coleta de comentários YouTube | Concluída |
| [us-03-clean.md](us/us-03-clean.md) | US-03 · Limpeza e seleção de dataset | Concluída |
| [us-04-annotate.md](us/us-04-annotate.md) | US-04 · Anotação de comentários | Concluída |
| [us-05-review.md](us/us-05-review.md) | US-05 · Revisão de conflitos | Concluída |
| [us-06-dashboard.md](us/us-06-dashboard.md) | US-06 · Dashboard de análise | Concluída |
| [us-07-data-catalog.md](us/us-07-data-catalog.md) | US-07 · Catálogo de dados | Concluída |

## Qualidade e Segurança (`qualidade/`)

| Arquivo | Escopo |
|---------|--------|
| [quality-security.md](qualidade/quality-security.md) | 5 fases: cobertura, OWASP, frontend, E2E, monitoramento |

## Utilitários

| Arquivo | Escopo |
|---------|--------|
| [readme-gen.md](readme-gen.md) | Geração de READMEs (raiz, backend, frontend) |

## Fluxo entre USs

```
US-00 (Infra) — base para todas

US-01 (Auth) — JWT necessário em todas

US-02 (Coleta) → US-03 (Limpeza) → US-04 (Anotação) → US-05 (Revisão)
                                           └──────────────────────→ US-06 (Dashboard)
                                                                    US-07 (Catálogo)
```
