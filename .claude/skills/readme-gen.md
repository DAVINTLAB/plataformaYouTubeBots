# Skill: Geração de README

## Objetivo

Guia para agentes de IA gerarem READMEs consistentes para qualquer escopo do projeto
(raiz, `backend/`, `frontend/`, ou subpacotes futuros).

**Antes de gerar qualquer README:** leia os arquivos existentes no diretório alvo para
extrair informações reais — nunca invente versões, comandos ou dependências.

---

## Arquivos a ler antes de gerar

### Para `backend/README.md`
```
backend/requirements.txt          → dependências e versões exatas
backend/main.py                    → entrypoint, título da API, routers registrados
backend/vercel.json                → configuração de runtime
backend/alembic.ini                → presença de migrations
backend/.env.example               → variáveis de ambiente necessárias
.claude/backend.md                 → contexto de arquitetura
.claude/skills/us-*.md             → endpoints implementados (verificar o que já existe)
```

### Para `frontend/README.md`
```
frontend/package.json              → scripts disponíveis, dependências, versão do Node
frontend/vite.config.ts            → porta de dev, aliases
frontend/.env.example              → variáveis de ambiente necessárias
frontend/src/pages/                → telas implementadas (listar diretórios)
.claude/frontend.md                → contexto de arquitetura
```

### Para `README.md` raiz
```
CLAUDE.md                          → stack, estrutura, comandos
AGENTS.md                          → branches e convenções
.github/CONTRIBUTING.md            → fluxo de contribuição
backend/requirements.txt + frontend/package.json → versões reais
```

---

## Estrutura padrão por escopo

### README raiz

```markdown
# Nome do Projeto
Descrição de 1-2 linhas.

## Visão geral
## Stack (tabela)
## Estrutura do repositório (árvore)
## User Stories (tabela US → rota)
## Desenvolvimento local (pré-requisitos + comandos backend + frontend)
## Variáveis de ambiente (tabela)
## Branches (diagrama Gitflow resumido)
## Qualidade e segurança
## Licença
```

### `backend/README.md`

```markdown
# Backend — Nome do Projeto
Descrição da API.

## Stack
## Estrutura de diretórios
## Instalação e execução local
## Migrations
## Endpoints (tabela: método + rota + descrição + role exigida)
## Variáveis de ambiente
## Testes
## Deploy (Vercel)
```

### `frontend/README.md`

```markdown
# Frontend — Nome do Projeto
Descrição da SPA.

## Stack
## Estrutura de diretórios
## Instalação e execução local
## Páginas implementadas (tabela: página → US → rota)
## Variáveis de ambiente
## Build e deploy (Vercel)
## Qualidade (lint, format, tsc)
```

---

## Regras de geração

### O que SEMPRE incluir
- Comandos copiáveis e funcionais — verificar que existem nos scripts/arquivos reais
- Tabela de variáveis de ambiente extraída do `.env.example` real
- Versões reais (Python, Node, dependências principais) — não escrever "X.Y+" sem verificar

### O que NUNCA fazer
- Inventar endpoints, comandos ou variáveis que não existem no código
- Copiar comandos do skill de US sem verificar se já foram implementados
- Incluir seções vazias com "em breve" ou "TODO" — omitir seções ainda não implementadas
- Adicionar badges de CI/cobertura antes do CI estar configurado e verde

### Tom e formato
- Português para projetos em PT-BR (este projeto)
- Títulos em sentence case: "Desenvolvimento local", não "DESENVOLVIMENTO LOCAL"
- Tabelas para listas com mais de 3 itens que têm estrutura (variáveis, endpoints, USs)
- Blocos de código com linguagem especificada (\`\`\`bash, \`\`\`python, etc.)
- Máximo 1 nível de subseção abaixo do `##` principal (evitar `####`)

---

## Checklist pós-geração

Antes de commitar o README gerado, verificar:

- [ ] Todos os comandos foram testados ou verificados nos arquivos fonte
- [ ] Variáveis de ambiente batem com o `.env.example` atual
- [ ] Versões de runtime (Python, Node) batem com `requirements.txt` / `package.json`
- [ ] Endpoints listados existem nos routers implementados
- [ ] Nenhuma seção com conteúdo placeholder ("a implementar", "em breve")
- [ ] Links internos (ex: `[CONTRIBUTING.md](.github/CONTRIBUTING.md)`) estão corretos

---

## Quando atualizar o README

| Evento                                      | README a atualizar          |
|---------------------------------------------|-----------------------------|
| Nova US implementada                        | `backend/` e/ou `frontend/` |
| Novo endpoint ou variável de ambiente       | `backend/` ou raiz          |
| Nova página ou componente de rota           | `frontend/`                 |
| Mudança de stack (dependência principal)    | Raiz + escopo afetado       |
| Mudança no fluxo de deploy                  | Raiz + escopo afetado       |
| Mudança nas branches ou convenções          | Raiz                        |
