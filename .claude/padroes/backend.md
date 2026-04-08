# Padrões de Backend

## Arquitetura em Camadas

As camadas só se comunicam na direção: `routers → services → repositories → models`.
Nunca pular camadas — um router não acessa repositório diretamente.

```
routers/     → recebe HTTP, valida entrada/saída via schemas Pydantic, chama services
services/    → orquestra regras de negócio, chama repositories
repositories/→ acessa o banco via SQLAlchemy, retorna modelos ou None
models/      → entidades SQLAlchemy puras, sem lógica de negócio
schemas/     → DTOs Pydantic de entrada e saída
core/        → config, segurança, dependências injetáveis compartilhadas
```

## SOLID na prática

### SRP — cada módulo tem uma responsabilidade

```python
# routers/annotate.py — só HTTP
@router.post("/", response_model=AnnotationResponse)
def annotate(payload: AnnotationRequest, svc: AnnotationService = Depends(get_annotation_service)):
    return svc.save(payload)

# services/annotate.py — só lógica
class AnnotationService:
    def save(self, payload: AnnotationRequest) -> Annotation: ...

# repositories/annotation.py — só banco
class AnnotationRepository(RepositoryBase):
    def create(self, annotation: Annotation) -> Annotation: ...
```

### OCP — algoritmos de limpeza extensíveis sem modificação

```python
# services/clean/base.py
from abc import ABC, abstractmethod

class SelectorBase(ABC):
    @abstractmethod
    def select(self, comments: list[Comment]) -> list[Comment]:
        ...

# services/clean/percentile.py
class PercentileSelector(SelectorBase):
    def __init__(self, top_percent: float = 0.30):
        self.top_percent = top_percent

    def select(self, comments: list[Comment]) -> list[Comment]:
        ...

# Adicionar novo critério = nova classe, sem tocar nas existentes
```

### LSP — implementações substituíveis

Qualquer `SelectorBase` pode ser trocado sem quebrar o sistema.
Nos testes, repositórios reais são substituídos por mocks que implementam a mesma interface.

### ISP — interfaces específicas por domínio

```python
# repositories/comment.py
class CommentRepository(RepositoryBase):
    @abstractmethod
    def get_by_video(self, video_id: str) -> list[Comment]: ...
    @abstractmethod
    def bulk_insert(self, comments: list[Comment]) -> None: ...

# repositories/user.py
class UserRepository(RepositoryBase):
    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...
```

### DIP — dependências injetadas, nunca instanciadas

```python
# services/annotate.py
class AnnotationService:
    def __init__(self, repo: AnnotationRepository):
        self.repo = repo  # recebe, não instancia

# core/dependencies.py
def get_annotation_service(db: Session = Depends(get_db)) -> AnnotationService:
    return AnnotationService(repo=AnnotationRepository(db))

# routers/annotate.py
def annotate(svc: AnnotationService = Depends(get_annotation_service)): ...
```

## Estrutura de endpoint

```python
@router.post("/", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: ExampleRequest,
    svc: ExampleService = Depends(get_example_service),
    current_user: User = Depends(get_current_user),
):
    return svc.create(payload, current_user)
```

## Import/Export simétrico

Toda US que produz dados deve ter endpoints de export e import com **formato idêntico**:

```python
# Export — streaming com yield_per para não estourar memória
@router.get("/{id}/download")
def download(id: uuid.UUID, fmt: str = Query(default="json", alias="format"), ...):
    def json_stream():
        yield '{\n  "metadata": ' + json.dumps(meta) + ',\n'
        yield '  "items": [\n'
        first = True
        for item in db.query(Model).filter(...).yield_per(500):
            prefix = "    " if first else ",\n    "
            first = False
            yield prefix + json.dumps(to_dict(item), ensure_ascii=False)
        yield "\n  ]\n}\n"
    return StreamingResponse(json_stream(), media_type="application/json", ...)

# Import — aceita o mesmo JSON do export
@router.post("/import", status_code=201, response_model=ResponseModel)
def import_endpoint(payload: ImportSchema, ...):
    ...
```

### Regras
- O JSON de import deve ser aceito sem modificação a partir do export
- Exports usam `yield_per(500)` + `StreamingResponse` com gerador — nunca `.all()`
- Import de arquivos grandes usa chunks paginados (`/import-chunk`) para respeitar o limite de 4.5MB do Vercel
- Import de etapas posteriores (US-03+) localiza dados relacionados por `video_id`, sem exigir IDs internos

## API keys externas

```python
class CollectRequest(BaseModel):
    video_url: str
    api_key: SecretStr  # mascara em repr() e logs

# extrair apenas no momento de uso
result = youtube_client.fetch(api_key=payload.api_key.get_secret_value())
```

## Segurança

- Nunca usar `print()` — sempre `logging.getLogger(__name__)`
- Nunca logar `SecretStr`, tokens JWT ou senhas
- Bandit e Ruff devem passar sem warnings antes de qualquer commit

## Tratamento de erros

Toda HTTPException deve ter `detail` descritivo para o usuário final. Mensagens genéricas como "Erro inesperado" são proibidas — sempre incluir o contexto do que falhou.

### Regras

1. **detail descritivo**: toda HTTPException deve explicar **o que** falhou e **o que o usuário pode fazer**
2. **Logar antes de lançar**: exceções inesperadas devem ser logadas com `logger.exception()` antes de virar HTTPException
3. **Não engolir exceções**: `except Exception` sem log é proibido — no mínimo `logger.warning()` ou `logger.exception()`
4. **Erros de APIs externas**: parsear a resposta e traduzir para mensagem amigável em português
5. **Incluir contexto**: quando possível, incluir IDs e valores relevantes no log (nunca secrets)

### Padrão

```python
# ✅ Correto — descritivo, com log
try:
    result = await external_api_call()
except httpx.HTTPStatusError as exc:
    logger.exception("Falha na API externa para video_id=%s", video_id)
    raise HTTPException(
        status.HTTP_502_BAD_GATEWAY,
        detail="Falha ao comunicar com a API do YouTube. Tente novamente.",
    ) from exc
except Exception as exc:
    logger.exception("Erro inesperado ao coletar video_id=%s", video_id)
    raise HTTPException(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Erro interno ao processar a coleta. Tente novamente ou contate o administrador.",
    ) from exc

# ❌ Errado — genérico, sem log
except Exception:
    raise HTTPException(500, detail="Erro inesperado.")
```

## Padrões de teste Pytest

### Regra de cobertura

- **Mínimo 80% de cobertura de linhas** — enforçado pelo CI (`--cov-fail-under=80`)
- Cobertura deve vir de **testes úteis** que validem lógica de negócio, não de testes triviais escritos apenas para subir percentual
- Se um teste não valida nenhum comportamento de negócio, ele não deve existir

### Técnicas obrigatórias

#### Testes unitários

| Técnica | Quando usar | Exemplo |
|---|---|---|
| **Partição de equivalência** | Inputs com comportamento distinto | `video_id` válido vs URL completa vs URL curta vs string vazia |
| **Valor limite** | Limites numéricos e de string | `reply_count = 0`, `reply_count = 5` (inline), `reply_count = 6` (extra fetch) |
| **Teste estrutural** | Cobrir branches de `if/else`, `try/except` | YouTube API retorna 400 vs 403 vs 404 vs 429 |
| **Teste de propriedades** | Invariantes que devem sempre valer | `comment_id` nunca duplica na mesma coleta (idempotência) |
| **Teste de contrato** | Garantir formato de resposta da API | Response contém `collection_id`, `status`, `total_comments` |
| **Teste de regressão** | Bug corrigido não volta | Erro 403 forbidden não retorna mais "vídeo privado" |
| **Teste de estado** | Transições de estado válidas | Collection: `running` → `completed` → enrich `pending` → `done` |
| **Teste de idempotência** | Operação repetida não duplica dados | Recoleta do mesmo vídeo não duplica comentários |

#### Testes de integração

| Técnica | Quando usar | Exemplo |
|---|---|---|
| **Fluxo entre endpoints** | Validar pipeline completo | `POST /collect` → `POST /collect/next-page` → `GET /collect/{id}/export` |
| **Integração com banco** | Persistência e consultas complexas | Import JSON → verificar dados no banco → exportar e comparar |
| **Tratamento de erros entre camadas** | Erros propagam corretamente | YouTube API falha → service marca `failed` → router retorna HTTP correto |
| **Concorrência e compartilhamento** | Dados compartilhados entre usuários | User A coleta → User B lista e vê a coleta de A |
| **Cascata de deleção** | Delete remove dados relacionados | Deletar coleta remove todos os comentários associados |

### Estrutura por endpoint

Todo endpoint deve ter no mínimo:

```python
# 1. Contrato — happy path retorna formato esperado
def test_coleta_retorna_collection_id_e_status(client, auth_as_user, stub): ...

# 2. Autenticação — sem token retorna 401
def test_coleta_sem_token_retorna_401(client): ...

# 3. Validação — payload inválido retorna 422
def test_coleta_payload_invalido_retorna_422(client, auth_as_user): ...

# 4. Regras de negócio — lógica específica da funcionalidade
def test_recoleta_nao_duplica_comentarios(client, db, auth_as_user, stub): ...

# 5. Erros externos — APIs externas retornam erros traduzidos
def test_youtube_403_retorna_mensagem_amigavel(client, auth_as_user, stub): ...

# 6. Segurança — dados sensíveis nunca vazam
def test_api_key_nao_aparece_na_resposta(client, auth_as_user, stub): ...
```

### Testes de integração

Fluxos que cruzam múltiplas camadas e endpoints devem ser testados de ponta a ponta:

```python
def test_fluxo_completo_coleta_export(client, db, auth_as_user, stub):
    """Integração: coleta → status → export JSON → verificar formato."""
    # 1. Iniciar coleta
    resp = client.post("/collect", json={...})
    assert resp.status_code == 202
    collection_id = resp.json()["collection_id"]

    # 2. Verificar status
    status = client.get(f"/collect/status?collection_id={collection_id}")
    assert status.json()["status"] == "completed"

    # 3. Exportar e verificar formato
    export = client.get(f"/collect/{collection_id}/export?format=json")
    data = export.json()
    assert "video" in data
    assert "comments" in data
    assert len(data["comments"]) > 0
```

### Dublês de teste

| Dublê | Quando usar |
|---|---|
| **Stub** | Simular respostas de APIs externas (YouTube API) |
| **Mock** | Verificar que algo NÃO aconteceu (API key não aparece em logs) |
| **Spy** | Observar chamadas sem substituir comportamento |
| **Fake** | PostgreSQL via Docker (nunca SQLite) |

### O que NÃO fazer

```python
# ❌ Teste que só sobe cobertura sem validar nada útil
def test_safe_int():
    assert _safe_int("42") == 42  # trivial, sem valor de negócio

# ❌ Teste que repete o que o framework já garante
def test_endpoint_existe():
    assert hasattr(router, "post")

# ❌ Teste que testa a implementação em vez do comportamento
def test_usa_bcrypt():
    assert "bcrypt" in str(get_password_hash("x"))
```

## Soft-delete

Remoção de entidades que possuem dados associados (ex: `User` com anotações) usa soft-delete em vez de `DELETE` físico.

```python
# service: desativar
def deactivate_user(db, user_id, requesting_user_id):
    user.is_active = False
    db.commit()

# service: reativar
def reactivate_user(db, user_id):
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user

# router: DELETE semântico + endpoint dedicado para reativação
@router.delete("/{id}", status_code=204)       # desativa
@router.post("/{id}/reactivate", response_model=UserOut)  # reativa
```

- `GET /users/` retorna todos (ativos e inativos) — filtragem fica no frontend
- Testes devem cobrir: desativar, reativar, ciclo completo e idempotência (reativar já ativo → 409)

## Migrations

```bash
alembic revision --autogenerate -m "descricao_curta"
alembic upgrade head
alembic downgrade -1
```

Nunca editar migrations já aplicadas em produção.