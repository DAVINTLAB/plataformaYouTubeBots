# Backlog — Qualidade, Segurança e Evolução

## Qualidade de Software

| Fase | Descrição | Esforço | Skill |
|------|-----------|---------|-------|
| ~~1~~ | ~~Backend 100% cobertura~~ | ~~Médio~~ | ~~Concluída (PR #89) — 342 testes, 99%~~ |
| 2 | Testes de segurança OWASP Top 10 | Médio | `quality-security.md` § Fase 2 |
| 3 | Testes frontend (Vitest + Testing Library) | Alto | `quality-security.md` § Fase 3 |
| 4 | Testes E2E (Playwright) | Alto | `quality-security.md` § Fase 4 |
| 5 | Monitoramento produção (Sentry + logging + headers) | Baixo | `quality-security.md` § Fase 5 |

## Segurança (OWASP Top 10)

| Categoria | O que testar | Status |
|-----------|-------------|--------|
| A01 — Controle de Acesso | IDOR, escalação de privilégio, usuário inativo | Pendente |
| A02 — Falhas Criptográficas | Senhas em resposta, API key em logs, JWT seguro | Pendente |
| A03 — Injeção | SQL injection, XSS armazenado | Pendente |
| A04 — Design Inseguro | Rate limiting, conflito irreversível, soft-delete | Pendente |
| A05 — Configuração Incorreta | CORS, debug mode, stacktrace exposto | Pendente |
| A07 — Autenticação | Brute force, token refresh, senha mínima | Pendente |
| A08 — Integridade | JSON malformado, campos extras, idempotência | Pendente |
| A09 — Logging | Coberto na Fase 5 (monitoramento) | Pendente |
| A10 — SSRF | Validação de domínio YouTube, API key scope | Pendente |

## Monitoramento Produção

| Item | Ferramenta | Status |
|------|-----------|--------|
| Error tracking | Sentry free tier (5K erros/mês) | Pendente |
| Logging estruturado | python-json-logger ou stdlib | Pendente |
| Request logging | Middleware Starlette | Pendente |
| Headers de segurança | X-Content-Type-Options, X-Frame-Options, etc. | Pendente |
| Visualização de logs | Vercel Logs (já incluso no Pro) | Pendente |

## Evolução do Produto (fora do escopo atual)

| Item | Descrição |
|------|-----------|
| Export ML-ready | CSV com features prontas para treinamento de modelo |
| Classificação automática | Integrar modelo para sugerir bot/humano ao anotador |
| Inter-annotator agreement | Cohen's Kappa, Fleiss' Kappa |
| Multi-idioma | Suporte a vídeos em inglês/espanhol |
