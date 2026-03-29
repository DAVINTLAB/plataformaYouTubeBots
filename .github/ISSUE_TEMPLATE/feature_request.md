---
name: Feature request (US)
about: Propor uma nova funcionalidade ou user story
title: "feat: "
labels: enhancement
---

## User Story

Como **[papel]**, quero **[ação]**, para **[benefício]**.

<!-- Exemplo:
Como **pesquisador autenticado**, quero informar o ID de um vídeo do YouTube
e acionar a coleta de comentários, para que os dados fiquem disponíveis para
filtragem e anotação.
-->

## Tasks

<!-- Siglas:
  [BE]    — Backend (FastAPI, serviços, repositórios)
  [FE]    — Frontend (React, componentes, hooks)
  [TEST]  — Testes (unitários, integração, cobertura)
  [INFRA] — Infraestrutura (CI/CD, deploy, banco, migrations)
  [DOCS]  — Documentação (skills, CLAUDE.md, README)
-->

- [ ] `[BE]` Endpoint `POST /exemplo` recebendo payload e retornando resultado
- [ ] `[FE]` Página com formulário e feedback de progresso
- [ ] `[TEST]` Testes de contrato, erros e regras de negócio
- [ ] `[INFRA]` Migration Alembic para novos campos
- [ ] `[DOCS]` Atualizar skill com contrato de API

## Critérios de aceite

- Operação conclui com sucesso para o cenário principal
- Erros são exibidos ao usuário com mensagem compreensível
- Dados persistem no banco após encerramento da sessão
