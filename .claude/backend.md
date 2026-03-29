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

```python
# todo endpoint deve cobrir:
def test_happy_path(client, auth_headers): ...
def test_sem_token_retorna_401(client): ...
def test_papel_insuficiente_retorna_403(client, auth_headers): ...
def test_payload_invalido_retorna_422(client, auth_headers): ...
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