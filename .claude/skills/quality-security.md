# Qualidade de Software, Segurança e Monitoramento

## Objetivo

Elevar a qualidade do projeto para padrão de produção: cobertura de testes 100% no backend,
testes no frontend, testes de segurança (OWASP Top 10), testes E2E e monitoramento em produção.

---

## Estado atual

| Área | Status | Detalhe |
|------|--------|---------|
| Backend — testes unitários | 184 testes, ≥80% cobertura | 8 módulos de teste, PostgreSQL real |
| Backend — lint/format/segurança | Ruff + Bandit + pip-audit | Enforçado no CI |
| Frontend — testes | **Nenhum** | Sem Vitest, sem *.test.tsx |
| Frontend — lint/format/tipos | ESLint + Prettier + tsc | Enforçado no CI |
| Segurança estática | Bandit (backend), npm audit (frontend) | Sem testes dinâmicos |
| Segurança dinâmica | **Nenhuma** | Sem OWASP ZAP, sem testes de injeção |
| Testes E2E | **Nenhum** | Sem Playwright/Cypress |
| Monitoramento produção | **Nenhum** | Sem Sentry, sem logging estruturado |
| Rate limiting | Configurado (slowapi) | **Sem testes** |

---

## Fase 1 — Backend: cobertura 100%

### Meta

Elevar de ≥80% para 100% de cobertura de linhas. Identificar branches não cobertas
e adicionar testes que validem comportamento real (nunca testes triviais para subir %).

### Passos

1. Rodar `pytest --cov=. --cov-report=term-missing` para identificar linhas não cobertas
2. Para cada módulo com linhas descobertas:
   - Identificar se são branches de erro, edge cases ou código morto
   - Código morto → remover em vez de testar
   - Branches de erro → adicionar teste com partição de equivalência
   - Edge cases → adicionar teste com valor limite
3. Atualizar `.coveragerc` para `fail_under = 100`
4. Atualizar CI para enforçar `--cov-fail-under=100`

### Módulos a cobrir

| Módulo | O que provavelmente falta |
|--------|--------------------------|
| `services/collect.py` | Branches de erro da YouTube API (429, 404, timeout), enrich parcial |
| `services/clean/*.py` | Critérios com dados vazios, thresholds edge (0%, 100%) |
| `services/annotate.py` | Justificativa obrigatória para bot, upsert idempotente |
| `services/review.py` | Resolução de conflito já resolvido (409), export sem dataset |
| `services/dashboard.py` | Destaques do vídeo com dados vazios, gráficos com 0 dados |
| `services/data.py` | pg_total_relation_size falhando (try/except), datasets sem collection |
| `routers/*.py` | Validação 422 de payloads malformados |
| `services/auth.py` | Token expirado, token com tipo errado, usuário inativo |
| `core/rate_limit.py` | 429 após exceder limite |

### Stubs para YouTube API

Todos os testes de coleta usam stubs — nunca chamam a API real:

```python
@pytest.fixture
def stub_youtube_success(mocker):
    """Stub: YouTube API retorna 20 comentários + nextPageToken."""
    mocker.patch("services.collect.httpx.get", return_value=MockResponse(
        status_code=200,
        json_data={"items": [...], "nextPageToken": "abc123"}
    ))
```

Não é necessária API key real para nenhum teste.

---

## Fase 2 — Testes de Segurança (OWASP Top 10)

### Meta

Testar as 10 categorias OWASP mais relevantes para esta aplicação. Cada categoria
gera um arquivo `tests/test_security_<categoria>.py`.

### Categorias e testes

#### A01 — Controle de Acesso Quebrado (Broken Access Control)

```python
# tests/test_security_access.py

# IDOR — acessar recurso de outro usuário
def test_user_nao_acessa_anotacao_de_outro_via_uuid_manipulado(): ...
def test_user_comum_nao_acessa_rotas_admin(): ...
def test_user_inativo_nao_consegue_autenticar(): ...

# Escalação de privilégio
def test_user_nao_consegue_se_promover_a_admin(): ...
def test_delete_usuario_exige_role_master(): ...
```

#### A02 — Falhas Criptográficas (Cryptographic Failures)

```python
# tests/test_security_crypto.py

def test_senha_nunca_aparece_em_resposta_json(): ...
def test_api_key_nunca_aparece_em_log_ou_resposta(): ...
def test_jwt_usa_algoritmo_seguro_hs256(): ...
def test_jwt_expirado_retorna_401(): ...
def test_jwt_com_assinatura_invalida_retorna_401(): ...
def test_jwt_sem_campo_sub_retorna_401(): ...
```

#### A03 — Injeção (Injection)

```python
# tests/test_security_injection.py

# SQL Injection — SQLAlchemy parametriza por padrão, mas validar
SQLI_PAYLOADS = ["'; DROP TABLE users;--", "1 OR 1=1", "' UNION SELECT * FROM users--"]

def test_sqli_no_campo_search_bots(payload): ...
def test_sqli_no_video_id(payload): ...
def test_sqli_no_campo_author(payload): ...
def test_sqli_no_username_login(payload): ...

# XSS — React escapa por padrão, mas validar no backend
XSS_PAYLOADS = ["<script>alert(1)</script>", "<img onerror=alert(1)>", "javascript:alert(1)"]

def test_xss_no_nome_de_usuario_nao_executa(): ...
def test_comentario_importado_com_xss_armazenado_sem_executar(): ...
```

#### A04 — Design Inseguro (Insecure Design)

```python
# tests/test_security_design.py

def test_rate_limiting_login_bloqueia_apos_5_tentativas(): ...
def test_rate_limiting_refresh_bloqueia_apos_10_tentativas(): ...
def test_conflito_resolvido_nao_pode_ser_revertido(): ...
def test_soft_delete_preserva_dados_relacionados(): ...
```

#### A05 — Configuração Incorreta (Security Misconfiguration)

```python
# tests/test_security_config.py

def test_cors_nao_permite_origin_qualquer_em_producao(): ...
def test_debug_mode_desativado(): ...
def test_stacktrace_nao_exposto_em_erro_500(): ...
def test_health_endpoint_nao_expoe_versao_detalhada(): ...
```

#### A07 — Falhas de Autenticação (Authentication Failures)

```python
# tests/test_security_auth.py

def test_brute_force_bloqueado_por_rate_limit(): ...
def test_token_refresh_com_access_token_retorna_401(): ...
def test_logout_invalida_sessao(): ...
def test_password_minimo_8_caracteres(): ...
def test_username_formato_valido_apenas_alfanumerico(): ...
```

#### A08 — Falhas de Integridade (Software and Data Integrity)

```python
# tests/test_security_integrity.py

def test_import_json_malformado_retorna_422(): ...
def test_import_com_campos_extras_ignora_campos(): ...
def test_import_com_video_id_inexistente_retorna_erro(): ...
def test_bulk_insert_on_conflict_nao_duplica(): ...
```

#### A09 — Falhas de Logging e Monitoramento

Coberto na Fase 4 (Monitoramento em Produção).

#### A10 — Server-Side Request Forgery (SSRF)

```python
# tests/test_security_ssrf.py

def test_video_url_so_aceita_youtube_domain(): ...
def test_api_key_nao_enviada_para_dominio_externo(): ...
```

---

## Fase 3 — Testes Frontend (Vitest + Testing Library)

### Setup

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Configurar `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
```

### Estrutura

```
src/
├── test/
│   └── setup.ts              # import @testing-library/jest-dom
├── hooks/
│   ├── useAnnotate.test.ts
│   ├── useClean.test.ts
│   ├── useDashboard.test.ts
│   ├── useData.test.ts
│   └── useReview.test.ts
├── components/
│   ├── PageHeader.test.tsx
│   ├── StatusBadge.test.tsx
│   ├── ProgressBar.test.tsx
│   ├── StepsCard.test.tsx
│   └── ProtectedRoute.test.tsx
├── pages/
│   ├── Dashboard/
│   │   ├── KpiCards.test.tsx
│   │   ├── CriteriaFilterBar.test.tsx
│   │   └── BotCommentsTable.test.tsx
│   └── NotFound/
│       └── NotFoundPage.test.tsx
└── contexts/
    └── AuthContext.test.tsx
```

### Prioridade de testes

| Prioridade | Componente/Hook | O que testar |
|------------|-----------------|-------------|
| Alta | AuthContext | Login, logout, token refresh, estado persistido |
| Alta | ProtectedRoute | Redirect sem token, redirect sem admin, renderiza com token |
| Alta | Hooks (useAnnotate, etc.) | Fetch, loading, error states, transformação de dados |
| Média | PageHeader | Renderiza nome, role badge, breadcrumb, botão sair |
| Média | KpiCards | Renderiza todos os cards com cores corretas |
| Média | CriteriaFilterBar | Toggle checkboxes, limpar filtros |
| Média | BotCommentsTable | Paginação, busca, filtro por critério |
| Baixa | StatusBadge | Cores por status |
| Baixa | ProgressBar | Determinado vs indeterminado |

### CI

Adicionar ao `.github/workflows/ci.yml` no job `frontend`:

```yaml
- name: Test
  run: npx vitest run --coverage --coverage.thresholds.lines=80
```

---

## Fase 4 — Testes E2E (Playwright)

### Setup

```bash
cd frontend
npm install -D @playwright/test
npx playwright install
```

### Fluxos a testar

```
tests/e2e/
├── auth.spec.ts          # Login, logout, redirect sem token, token refresh
├── collect.spec.ts       # Coleta mockada (stub API), status, export
├── clean.spec.ts         # Preview, criar dataset, download
├── annotate.spec.ts      # Navegar usuários, anotar bot/humano, progresso
├── review.spec.ts        # Listar conflitos, resolver, stats
├── dashboard.spec.ts     # 3 abas, filtro critério, tabela de bots
├── data.spec.ts          # Catálogo, painéis de detalhe
├── not-found.spec.ts     # URL inexistente → página 404
└── security.spec.ts      # XSS no DOM, CSRF headers
```

### Estratégia de dados

- E2E usa o endpoint `POST /seed` para popular dados mockados antes dos testes
- `DELETE /seed` limpa após os testes
- Não depende de YouTube API real — seed gera dados completos

---

## Fase 5 — Monitoramento em Produção

### Logging estruturado

```python
# core/logging.py
import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        })
```

Aplicar em `main.py`:

```python
import logging
from core.logging import JSONFormatter

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

### Middleware de request logging

```python
# core/middleware.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("http")

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
```

### Sentry (error tracking)

```python
# main.py
import sentry_sdk

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=0.1,
        environment=os.getenv("VERCEL_ENV", "development"),
    )
```

Dependência: `sentry-sdk[fastapi]` no requirements.txt.

### Health check expandido

```python
@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "checks": {
            "database": "connected",
        },
    }
```

### Headers de segurança

```python
# core/middleware.py
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=()"
        return response
```

### Métricas de performance (opcional)

Se quiser dashboard de métricas:
- `prometheus-fastapi-instrumentator` para métricas Prometheus
- Grafana Cloud free tier para visualização

---

## Ordem de execução

| Fase | Descrição | Esforço |
|------|-----------|---------|
| 1 | Backend 100% cobertura | Médio — identificar gaps e adicionar testes |
| 2 | Testes de segurança OWASP | Médio — ~40 testes novos |
| 3 | Testes frontend (Vitest) | Alto — setup + ~50 testes |
| 4 | Testes E2E (Playwright) | Alto — setup + ~30 fluxos |
| 5 | Monitoramento produção | Baixo — logging + Sentry + headers |

Fases 1 e 2 podem rodar em paralelo. Fase 5 pode ser feita a qualquer momento.

---

## Dependências novas

### Backend
```
sentry-sdk[fastapi]   # error tracking (Fase 5)
```

### Frontend
```
vitest                              # test runner (Fase 3)
@testing-library/react              # component testing (Fase 3)
@testing-library/jest-dom           # DOM matchers (Fase 3)
@testing-library/user-event         # user interaction simulation (Fase 3)
jsdom                               # browser environment (Fase 3)
@playwright/test                    # E2E testing (Fase 4)
```

---

## CI atualizado (meta final)

```yaml
backend:
  - ruff check + ruff format --check
  - bandit -r backend/ --exclude tests
  - pip-audit
  - pytest --cov=. --cov-fail-under=100   # Fase 1: 80 → 100
  - pytest tests/test_security_*.py        # Fase 2: OWASP

frontend:
  - eslint + prettier --check
  - tsc --noEmit
  - npm audit --audit-level=high
  - vitest run --coverage --coverage.thresholds.lines=80  # Fase 3
  - npx playwright test                                    # Fase 4
```
