# Épico: Plataforma de Análise de Comentários e Detecção de Bots no YouTube

Sistema completo de coleta, limpeza, anotação e análise de comentários do YouTube para detecção de bots.

**Labels sugeridas:** `epic` `bot-detection`

### Issues filhas

- [ ] US-00 · Infraestrutura, CI/CD e segurança de dependências
- [ ] US-01 · Autenticação e gestão de usuários
- [ ] US-02 · Coleta de comentários do YouTube
- [ ] US-03 · Limpeza e seleção de dataset
- [ ] US-04 · Anotação de comentários
- [ ] US-05 · Desempate de classificações conflitantes
- [ ] US-06 · Dashboard de análise

---

## US-00 · Infraestrutura, CI/CD e segurança de dependências

> Configuração inicial do repositório, pipelines de qualidade e auditoria de dependências

**Labels:** `infra` `ci-cd` `segurança` `frontend · React.ts` `backend · FastAPI`

### User Story

Como **desenvolvedor do projeto**, quero que o repositório tenha pipelines de qualidade e segurança automatizados desde o início, para que nenhum código com problemas de lint, tipagem ou vulnerabilidades conhecidas chegue à branch principal.

### Tasks

- [ ] `[INFRA]` Criar repositório GitHub com dois projetos Vercel separados: `frontend/` e `backend/`
- [ ] `[INFRA]` Configurar `.github/dependabot.yml` para `pip` (`backend/`) e `npm` (`frontend/`) com frequência semanal e merge automático de patches
- [ ] `[INFRA]` Criar `.pre-commit-config.yaml` com hooks de Ruff, Bandit, ESLint e Prettier
- [ ] `[BE]` Configurar `ruff.toml` com regras de lint e format para o backend
- [ ] `[BE]` Configurar `bandit` para análise estática de segurança do código Python
- [ ] `[BE]` Configurar `pip-audit` para auditoria de dependências com falha em vulnerabilidades conhecidas
- [ ] `[BE]` Fixar todas as dependências do `requirements.txt` com versões exatas (sem `>=`)
- [ ] `[FE]` Configurar ESLint com regras para TypeScript (`@typescript-eslint`)
- [ ] `[FE]` Configurar Prettier integrado ao ESLint
- [ ] `[FE]` Configurar `npm audit` com `--audit-level=high` no CI
- [ ] `[FE]` Garantir `tsc --noEmit` sem erros como gate do CI
- [ ] `[CI]` Criar `.github/workflows/ci.yml` executando em todo push e PR para `main`:
  - Backend: Ruff · Bandit · pip-audit · Pytest (cobertura ≥ 80%)
  - Frontend: ESLint · Prettier · npm audit · tsc · build
- [ ] `[CI]` Configurar proteção de branch `main` — PR obrigatório, CI deve passar antes do merge

### Critérios de aceite

- Push direto na branch `main` é bloqueado — todo código entra via PR
- CI falha se houver erro de lint, tipagem, vulnerabilidade de severidade alta/crítica ou cobertura de testes abaixo de 80%
- Dependabot abre PRs automaticamente para atualizações de segurança
- Pre-commit hooks impedem commit local com código fora do padrão de lint/format
- Todas as dependências do backend têm versões fixas no `requirements.txt`

---

## US-01 · Autenticação e gestão de usuários

> Login pessoal, controle de acesso e criação de usuários pelo master

**Labels:** `backend · FastAPI` `frontend · React.ts` `auth · JWT + bcrypt` `PostgreSQL` `Pytest`

### User Story

Como **pesquisador**, quero autenticar-me com login e senha, para que meu progresso e dados sejam salvos e isolados dos demais usuários. Como **usuário master**, quero criar e gerenciar contas de novos pesquisadores.

### Tasks

- [ ] `[BE]` Endpoint de registro de usuário (apenas master pode criar)
- [ ] `[BE]` Endpoint de login retornando JWT com expiração configurável
- [ ] `[BE]` Endpoint de logout / invalidação de token
- [ ] `[BE]` Middleware de autenticação e autorização por papel (user / master)
- [ ] `[BE]` Hash de senhas com bcrypt
- [ ] `[BE]` Tabelas `users` e `roles` no PostgreSQL
- [ ] `[FE]` Tela de login com validação de campos
- [ ] `[FE]` Tela de gestão de usuários (visível apenas para master)
- [ ] `[FE]` Armazenamento seguro do JWT e redirecionamento em sessão expirada
- [ ] `[TEST]` Testes unitários e de integração com Pytest (cobertura ≥ 80%)

### Critérios de aceite

- Usuário comum não consegue acessar rotas protegidas sem JWT válido
- Token expira após intervalo definido e usuário é redirecionado ao login
- Somente usuário master consegue criar novos usuários
- Senhas não são armazenadas em texto plano no banco
- Login com credenciais inválidas retorna erro 401 sem revelar qual campo está errado

---

## US-02 · Coleta de comentários do YouTube

> Extração de comentários de vídeos via YouTube Data API

**Labels:** `backend · FastAPI` `frontend · React.ts` `PostgreSQL` `Pytest`

### User Story

Como **pesquisador autenticado**, quero informar o ID ou URL de um vídeo do YouTube e acionar a coleta de comentários, para que os dados fiquem disponíveis para filtragem e anotação.

### Tasks

- [ ] `[BE]` Endpoint `POST /collect` recebendo URL ou ID de vídeo e `api_key` no corpo da requisição
- [ ] `[BE]` API key tipada como `SecretStr` (Pydantic) — usada apenas em memória durante a coleta e descartada em seguida, nunca gravada em banco, log ou variável de ambiente persistida
- [ ] `[BE]` Integração com YouTube Data API v3 (paginação, cota)
- [ ] `[BE]` Tratamento de erros: vídeo privado, inexistente, cota excedida
- [ ] `[BE]` Persistência dos comentários coletados no PostgreSQL (sem persistir a API key)
- [ ] `[BE]` Endpoint `GET /collect/status` para acompanhar coleta assíncrona
- [ ] `[BE]` Requisição trafega obrigatoriamente via HTTPS para evitar exposição da chave em trânsito
- [ ] `[FE]` Formulário de entrada de URL com feedback de progresso
- [ ] `[FE]` Campo de entrada da API key do tipo `password` (mascarado) com `autocomplete="off"`
- [ ] `[FE]` API key não armazenada em `localStorage`, `sessionStorage` nem em estado global persistido
- [ ] `[FE]` Listagem dos vídeos já coletados com contagem de comentários
- [ ] `[TEST]` Testes com mock da YouTube API e cenários de erro
- [ ] `[TEST]` Teste verificando que nenhum campo de API key aparece nos logs da aplicação nem no payload de resposta

### Critérios de aceite

- Coleta conclui com sucesso para vídeo público com comentários habilitados
- Erros da API do YouTube são exibidos ao usuário com mensagem compreensível
- Comentários duplicados de coletas repetidas não são inseridos novamente
- Dados persistem no banco após encerramento da sessão
- Inspecionando o banco após uma coleta, nenhuma tabela contém o valor da chave
- Logs da aplicação não registram a API key em nenhum nível (DEBUG, INFO, ERROR)
- Se a requisição falhar no meio da coleta, a chave é descartada mesmo assim

---

## US-03 · Limpeza e seleção de dataset

> Seleção estatística de usuários com comportamento suspeito de bot para encaminhamento à anotação

**Labels:** `backend · FastAPI` `frontend · React.ts` `PostgreSQL` `Pytest`

### User Story

Como **pesquisador autenticado**, quero executar uma limpeza estatística e comportamental sobre os comentários coletados, para que apenas usuários com perfil suspeito de bot sejam encaminhados à anotação — mantendo os demais visíveis para revisão manual se necessário.

### Lógica de seleção

Cada critério é **independente** e gera seu próprio dataset nomeado. O pesquisador pode executar um, vários ou todos — cada execução produz um artefato separado no banco. Os datasets podem ser combinados posteriormente na anotação.

**Convenção de nomenclatura dos datasets gerados:**
- `{idVideo}_percentil` — top 30% por volume de comentários
- `{idVideo}_media` — usuários acima da média (sem outliers)
- `{idVideo}_moda` — usuários acima da moda (sem outliers)
- `{idVideo}_mediana` — usuários acima da mediana (sem outliers)
- `{idVideo}_curtos` — comentários muito curtos ou repetitivos
- `{idVideo}_intervalo` — intervalo de tempo muito curto entre postagens
- `{idVideo}_identicos` — comentários idênticos em múltiplos vídeos
- `{idVideo}_perfil` — perfis sem foto ou recém-criados
- `{idVideo}_percentil_media` — interseção de múltiplos critérios combinados (exemplo)

**Grupo 1 — Critérios estatísticos de volume (independentes entre si):**
- **Percentil:** seleciona usuários no top 30% de volume de comentários no vídeo
- **Média:** calcula distribuição de comentários por usuário, remove outliers via IQR, seleciona usuários acima da média resultante
- **Moda:** mesmo processo, threshold pela moda
- **Mediana:** mesmo processo, threshold pela mediana

O pesquisador escolhe quais medidas executar. Cada uma gera um dataset separado. É possível executar todas as quatro ao mesmo tempo, gerando quatro datasets distintos.

**Grupo 2 — Critérios comportamentais (independentes entre si):**
- Comentários muito curtos (abaixo de N caracteres configurável) ou com alto índice de repetição entre si
- Intervalo de tempo muito curto entre comentários consecutivos do mesmo usuário (abaixo de T segundos configurável)
- Comentários idênticos ou quase idênticos postados em múltiplos vídeos pelo mesmo usuário
- Perfil sem foto de avatar ou com data de criação recente (quando disponível via API)

**Combinação de critérios:**
O pesquisador pode marcar múltiplos critérios de grupos diferentes para gerar um dataset de interseção, nomeado automaticamente com os sufixos dos critérios ativos (ex: `{idVideo}_percentil_intervalo_identicos`).

**Resultado por execução:** apenas o dataset selecionado (suspeitos) é persistido e nomeado. Os comentários não selecionados não são armazenados — o dataset original coletado na US-02 já serve como referência completa caso o pesquisador queira consultar os excluídos.

**Fontes de dados para critérios de perfil:**
- **YouTube Data API v3** — data de criação do canal, contagem de vídeos, avatar, descrição
- **SocialBlade API** — histórico de crescimento do canal, padrões de atividade ao longo do tempo

### Tasks

- [ ] `[BE]` Endpoint `POST /clean` recebendo ID do vídeo, lista de critérios ativos e thresholds configuráveis
- [ ] `[BE]` Algoritmo de cálculo de distribuição por usuário com remoção de outliers via IQR
- [ ] `[BE]` Algoritmo de seleção por percentil (top 30%)
- [ ] `[BE]` Algoritmos de seleção por média, moda e mediana (cada um separado, executáveis individualmente)
- [ ] `[BE]` Algoritmo de detecção de comentários curtos/repetitivos (threshold N configurável)
- [ ] `[BE]` Algoritmo de detecção de intervalo temporal curto entre postagens (threshold T configurável)
- [ ] `[BE]` Algoritmo de detecção de comentários idênticos em múltiplos vídeos
- [ ] `[BE]` Algoritmo de detecção de perfis suspeitos consultando YouTube Data API v3 (data de criação, avatar, contagem de vídeos)
- [ ] `[BE]` Algoritmo de detecção de perfis suspeitos consultando SocialBlade API (histórico de crescimento, padrões de atividade)
- [ ] `[BE]` Chaves da YouTube API e SocialBlade API recebidas por requisição via `SecretStr` — nunca persistidas (mesmo padrão da US-02)
- [ ] `[BE]` Lógica de combinação de critérios gerando dataset de interseção
- [ ] `[BE]` Geração automática do nome do dataset conforme convenção `{idVideo}_{critérios}`
- [ ] `[BE]` Persistência apenas do dataset selecionado — excluídos não são armazenados
- [ ] `[BE]` Endpoint `GET /clean/preview` retornando contagem estimada por critério antes de confirmar
- [ ] `[BE]` Endpoint `GET /clean/datasets` listando todos os datasets gerados para um vídeo
- [ ] `[BE]` Endpoint de download de qualquer dataset gerado em CSV/JSON por nome
- [ ] `[FE]` Interface exibindo os dois grupos de critérios com checkboxes independentes
- [ ] `[FE]` Campos de threshold configurável para critérios comportamentais (N caracteres, T segundos)
- [ ] `[FE]` Exibição das três medidas centrais calculadas (média, moda, mediana) antes de confirmar
- [ ] `[FE]` Prévia de quantidade de usuários selecionados por critério antes de confirmar
- [ ] `[FE]` Nome do dataset gerado exibido previamente conforme critérios selecionados
- [ ] `[FE]` Listagem de todos os datasets gerados para o vídeo com link para uso na anotação
- [ ] `[FE]` Botão de download individual por dataset selecionado
- [ ] `[TEST]` Testes unitários de cada algoritmo estatístico e comportamental com datasets de referência
- [ ] `[TEST]` Testes de combinação de critérios e geração correta do nome do dataset
- [ ] `[TEST]` Testes de borda: vídeo com poucos comentários, todos do mesmo usuário, outliers extremos

### Critérios de aceite

- Cada critério pode ser executado de forma completamente independente, gerando seu próprio dataset
- Múltiplos critérios selecionados ao mesmo tempo geram um único dataset de interseção com nome combinado
- Remoção de outliers afeta apenas o cálculo da medida central, não exclui usuários do dataset final
- As três medidas centrais são exibidas ao pesquisador antes da confirmação da seleção
- Apenas o dataset selecionado é persistido — comentários não selecionados não são armazenados
- Nomes dos datasets seguem a convenção `{idVideo}_{critérios}` sem exceção
- Chaves da YouTube API e SocialBlade são recebidas por requisição, usadas em memória e descartadas — nunca gravadas em banco ou logs
- Pesquisador consegue baixar qualquer dataset selecionado em CSV ou JSON
- Todos os datasets de um vídeo ficam listados e acessíveis para uso na anotação (US-04)

---

## US-04 · Anotação de comentários

> Classificação individual de comentários por pesquisador com salvamento de progresso

**Labels:** `backend · FastAPI` `frontend · React.ts` `PostgreSQL` `Pytest`

### User Story

Como **pesquisador autenticado**, quero visualizar todos os comentários de um usuário do YouTube e classificar cada um individualmente como bot ou humano, com meu progresso salvo automaticamente, para que eu possa retomar a anotação em sessões futuras.

### Tasks

- [ ] `[BE]` Endpoint `GET /annotate/users` listando usuários do YouTube a anotar
- [ ] `[BE]` Endpoint `GET /annotate/comments/{user_id}` retornando comentários por usuário
- [ ] `[BE]` Endpoint `POST /annotate` salvando rótulo (bot / humano) e campo de justificativa por comentário
- [ ] `[BE]` Validação: campo de justificativa obrigatório quando rótulo for `bot`, opcional para `humano`
- [ ] `[BE]` Lógica de progresso: percentual anotado por pesquisador e por vídeo
- [ ] `[BE]` Endpoint de upload de anotações em CSV (importação em lote)
- [ ] `[BE]` Endpoint de download das anotações do pesquisador
- [ ] `[FE]` Interface de anotação mostrando histórico do usuário do YouTube
- [ ] `[FE]` Barra de progresso por vídeo / por sessão
- [ ] `[FE]` Botões de ação rápida (bot / humano) com atalho de teclado
- [ ] `[FE]` Campo de justificativa exibido e obrigatório ao selecionar `bot`, opcional para `humano`
- [ ] `[FE]` Botão de upload/download de anotações em CSV
- [ ] `[TEST]` Testes de persistência e recuperação de progresso

### Critérios de aceite

- Progresso de anotação é recuperado corretamente após logout e novo login
- Dois pesquisadores podem anotar o mesmo conjunto sem sobrescrever os dados um do outro
- Rótulo `bot` não pode ser salvo sem justificativa preenchida — frontend bloqueia envio e backend rejeita com erro 422
- Justificativa é opcional para o rótulo `humano`
- Rótulo pode ser alterado após salvo
- Upload de CSV em lote importa anotações sem duplicar registros existentes
- Download exporta apenas as anotações do pesquisador autenticado

---

## US-05 · Desempate de classificações conflitantes

> Resolução de conflitos entre anotadores pelo admin em tela dedicada

**Labels:** `backend · FastAPI` `frontend · React.ts` `PostgreSQL` `Pytest`

### User Story

Como **admin**, quero acessar uma tela dedicada que liste todos os comentários classificados como bot por pelo menos um anotador e todos os conflitos gerados por divergência entre dois anotadores, para que eu possa analisar cada caso e definir a classificação final.

### Lógica de conflito

- Conflito ocorre automaticamente quando **dois anotadores divergem** na classificação de um mesmo comentário, independentemente de maioria ou minoria — qualquer divergência gera conflito
- Não há resolução automática por votação: toda divergência exige decisão explícita do admin
- A classificação final definida pelo admin substitui o estado de conflito e é registrada com autoria e timestamp

### Tasks

- [ ] `[BE]` Detecção automática de conflito ao salvar anotação: se dois anotadores divergirem no mesmo comentário, o registro é marcado como `conflito`
- [ ] `[BE]` Endpoint `GET /review/conflicts` listando todos os comentários em estado de conflito com as classificações divergentes e justificativas de cada anotador
- [ ] `[BE]` Endpoint `GET /review/bots` listando todos os comentários classificados como `bot` por ao menos um anotador (incluindo os sem conflito)
- [ ] `[BE]` Endpoint `POST /review/resolve` recebendo ID do comentário e classificação final do admin
- [ ] `[BE]` Registro da decisão do admin com autoria e timestamp
- [ ] `[BE]` Restrição de acesso: endpoints de revisão acessíveis apenas por usuário com papel `admin`
- [ ] `[BE]` Tabela `resolutions` no PostgreSQL registrando decisão final, admin responsável e timestamp
- [ ] `[FE]` Tela de revisão acessível apenas ao admin com duas seções: conflitos e classificados como bot
- [ ] `[FE]` Para cada conflito: exibir o comentário, o usuário do YouTube, as classificações divergentes e as justificativas de cada anotador lado a lado
- [ ] `[FE]` Botões de decisão final (bot / humano) com confirmação antes de salvar
- [ ] `[FE]` Indicação visual de comentários já desempatados vs. pendentes
- [ ] `[FE]` Filtros por vídeo e por dataset de origem (US-03)
- [ ] `[TEST]` Teste de detecção automática de conflito ao divergir dois anotadores
- [ ] `[TEST]` Teste de restrição de acesso: usuário comum não acessa endpoints de revisão
- [ ] `[TEST]` Teste de registro correto da decisão final com autoria e timestamp

### Critérios de aceite

- Qualquer divergência entre dois anotadores gera conflito automaticamente, sem considerar maioria
- Comentários sem divergência classificados como `bot` por todos os anotadores aparecem na seção de bots, não na de conflitos
- Admin não consegue salvar desempate sem selecionar explicitamente `bot` ou `humano`
- Decisão final registra o admin responsável e o timestamp da resolução
- Usuário sem papel `admin` recebe erro 403 ao tentar acessar qualquer endpoint de revisão
- Após desempate, o comentário sai da fila de conflitos pendentes
- Filtro por vídeo e por dataset funciona nas duas seções da tela

---

## US-06 · Dashboard de análise

> Visualização global e específica dos dados anotados com Plotly

**Labels:** `backend · FastAPI` `frontend · React.ts` `Plotly` `PostgreSQL` `Pytest`

### User Story

Como **pesquisador autenticado**, quero visualizar gráficos e métricas sobre os comentários anotados — globais (todo o dataset) e específicos (meu progresso individual) — para que eu possa acompanhar a qualidade e o andamento da pesquisa.

### Tasks

- [ ] `[BE]` Endpoint `GET /dashboard/global` com agregações do dataset completo
- [ ] `[BE]` Endpoint `GET /dashboard/user` com métricas do pesquisador autenticado
- [ ] `[BE]` Geração de gráficos com Plotly (distribuição de rótulos, progresso por vídeo, inter-annotator agreement)
- [ ] `[FE]` Dashboard com gráficos Plotly.js integrados via React
- [ ] `[FE]` Alternância entre visão global e visão individual
- [ ] `[FE]` Filtros por vídeo e período no dashboard
- [ ] `[TEST]` Testes dos endpoints de agregação com dados de fixture

### Critérios de aceite

- Dashboard global exibe métricas de todos os pesquisadores sem expor dados individuais nominalmente
- Gráficos refletem em tempo real as anotações mais recentes
- Pesquisador consegue filtrar visualização por vídeo específico
- Dados do dashboard são consistentes com os registros do banco