# US-02 — Coleta de Comentários do YouTube

## Objetivo

Coletar comentários de um vídeo do YouTube via YouTube Data API v3, armazenar os dados brutos
no banco e disponibilizá-los para limpeza (US-03). A API key é fornecida por requisição e
**descartada imediatamente após uso** — nunca persiste no sistema.

---

## Regras de negócio

- A API key do YouTube é recebida como `SecretStr` no corpo da requisição
  — nunca logada em nenhum nível (DEBUG, INFO, ERROR), nunca persistida, descartada mesmo que a coleta falhe no meio
- Comentários duplicados de recoletas do mesmo vídeo **não são reinseridos** (idempotência por `comment_id`)
- Uma nova coleta do mesmo vídeo cria um registro separado, sem sobrescrever o anterior
- O endpoint de status permite acompanhar coleta assíncrona
- A requisição deve trafegar obrigatoriamente via HTTPS (Vercel garante isso em produção)
- Timeout de 10s no Vercel — coleta paginada por demanda (ver estratégia abaixo)

---

## Contrato de API

### `POST /collect`
Inicia a coleta de comentários de um vídeo (só comentários, sem enrich).

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "api_key": "AIza..."
}
```

> `video_id`: aceita tanto o ID puro (`dQw4w9WgXcQ`) quanto a URL completa do YouTube.

**Response 202:**
```json
{
  "collection_id": "uuid",
  "video_id": "dQw4w9WgXcQ",
  "status": "running",
  "total_comments": 100,
  "next_page_token": "...",
  "channel_dates_failed": null,
  "enrich_status": null,
  "duration_seconds": null,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### `POST /collect/next-page`
Continua a paginação (frontend-driven polling a cada 2s).

**Request:**
```json
{
  "collection_id": "uuid",
  "api_key": "AIza..."
}
```

---

### `POST /collect/{collection_id}/enrich`
Enriquece uma coleta concluída em 3 fases (video → replies → channels).

**Request:**
```json
{
  "api_key": "AIza..."
}
```

**Response 200:**
```json
{
  "phase": "video" | "replies" | "channels",
  "processed": 100,
  "remaining": 50,
  "done": false
}
```

---

### `GET /collect/status`
Consulta o status de uma coleta.

**Query params:** `collection_id=uuid`

**Response 200:**
```json
{
  "collection_id": "uuid",
  "video_id": "dQw4w9WgXcQ",
  "video_title": "Never Gonna Give You Up",
  "status": "completed",
  "total_comments": 487,
  "channel_dates_failed": false,
  "enrich_status": "done",
  "duration_seconds": 120,
  "collected_at": "2024-01-01T00:01:30Z",
  "collected_by": "username"
}
```

> `status`: `pending` | `running` | `completed` | `failed`
> `enrich_status`: `null` | `pending` | `enriching` | `done`

---

### `GET /collect`
Lista todas as coletas (compartilhadas entre todos os usuários).

**Response 200:**
```json
[
  {
    "collection_id": "uuid",
    "video_id": "string",
    "video_title": "string",
    "status": "completed",
    "total_comments": 487,
    "channel_dates_failed": false,
    "enrich_status": "done",
    "duration_seconds": 120,
    "collected_at": "2024-01-01T00:01:30Z"
  }
]
```

---

## Schema de banco (SQLAlchemy)

```python
# models/collection.py
class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    video_id: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    total_comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    comments: Mapped[list["Comment"]] = relationship(back_populates="collection")

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"))
    comment_id: Mapped[str] = mapped_column(String(64), nullable=False)  # ID original YouTube
    author_display_name: Mapped[str] = mapped_column(String(256))
    author_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    collection: Mapped["Collection"] = relationship(back_populates="comments")

    __table_args__ = (
        # idempotência: mesmo comment_id na mesma coleta não duplica
        UniqueConstraint("collection_id", "comment_id", name="uq_collection_comment"),
    )
```

---

## Schemas Pydantic

```python
# schemas/collect.py
class CollectRequest(BaseModel):
    video_id: str = Field(min_length=1)
    api_key: SecretStr  # nunca serializado, nunca logado
    max_results: int = Field(default=500, ge=1, le=2000)

    @field_validator("video_id")
    @classmethod
    def extract_video_id(cls, v: str) -> str:
        # aceitar URL completa ou ID puro
        if "youtube.com" in v or "youtu.be" in v:
            # extrair o parâmetro v= ou o path do youtu.be
            ...
        return v

class CollectionOut(BaseModel):
    collection_id: uuid.UUID
    video_id: str
    status: Literal["pending", "running", "completed", "failed"]
    total_comments: int | None = None
    collected_at: datetime | None = None
    collected_by: str | None = None
```

---

## Service — estratégia de coleta

Vercel Pro com `maxDuration: 60`. Coleta paginada + enrich separado:

```python
# services/youtube.py
_TIMEOUT = 15.0  # margem confortável dentro de 60s

async def fetch_comments_page(...) -> dict:
    params = {
        "part": "snippet,replies",  # replies inline (até 5 por thread)
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText",
    }
    ...
    timeout=_TIMEOUT

# IMPORTANTE: nunca passar api_key para logger ou mensagens de erro
```

**Fluxo de coleta (3 etapas):**
1. `POST /collect` inicia e coleta a 1ª página (≤ 100 comments) com bulk insert
2. Frontend chama `POST /collect/next-page` em polling até `next_page_token` ser nulo
3. Quando `status=completed`, frontend chama `POST /collect/{id}/enrich` em loop:
   - Fase 1/3: `videos.list` (metadados do vídeo)
   - Fase 2/3: `comments.list` (replies extras >5 por thread, 20 por batch)
   - Fase 3/3: `channels.list` (data de criação do canal, 200 por batch)

**Inserção:** bulk insert com `INSERT ... ON CONFLICT DO NOTHING` (1 query para N rows)

```python
# models/collection.py — adicionar coluna
next_page_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
```

---

## Frontend — componentes sugeridos

```
pages/Collect/
├── CollectPage.tsx          # formulário: video_id + api_key (password) + max_results
├── CollectionList.tsx       # lista de coletas com status (polling enquanto pending/running)
├── CollectionDetail.tsx     # detalhe + progresso + link para limpeza ao completar
└── useCollect.ts            # hook: startCollection(), getStatus(), listCollections()
```

**UX obrigatória:**
- Campo `api_key` com `type="password"` e `autoComplete="off"`
- API key **não** armazenada em `localStorage`, `sessionStorage` ou estado global persistido
- Polling de status enquanto `status === "pending" | "running"` (intervalo de 2s)
- Após `completed`: exibir total de comentários e botão "Ir para Limpeza"

---

## Casos de erro

| Cenário                              | HTTP | Mensagem ao usuário                              |
|--------------------------------------|------|--------------------------------------------------|
| API key inválida (YouTube 403)       | 400  | "API key inválida ou sem permissão."             |
| Vídeo não encontrado                 | 404  | "Vídeo não encontrado."                          |
| Comentários desativados              | 400  | "Este vídeo não permite comentários."            |
| Quota do YouTube esgotada (403)      | 429  | "Quota da API esgotada. Tente novamente amanhã." |
| Vídeo privado                        | 400  | "Este vídeo é privado ou não está disponível."   |

---

## Testes obrigatórios (Pytest)

### Referência de dublês

| Dublê | Quando usar                                                                    |
|-------|--------------------------------------------------------------------------------|
| Stub  | Simular respostas da YouTube API (sucesso, erro 403, quota, vídeo privado)     |
| Mock  | Verificar que a API key nunca aparece em logs ou no payload de erro            |
| Spy   | Observar chamadas ao logger sem substituí-lo completamente                     |
| Dummy | Preencher `collected_by` (user_id) quando o foco do teste é outro             |
| Fake  | Banco SQLite em memória para verificar persistência                            |

### Casos de teste

```python
# conftest.py
@pytest.fixture
def stub_youtube_success(mocker):
    """Stub: httpx retorna página de comentários válida sem chamar a API real."""
    mocker.patch("services.youtube.httpx.AsyncClient.get", return_value=MockResponse(
        status_code=200,
        json={
            "items": [{"snippet": {"topLevelComment": {"snippet": {
                "textOriginal": "comentário", "authorDisplayName": "user1",
                "authorChannelId": {"value": "UC123"}, "likeCount": 0,
                "publishedAt": "2024-01-01T00:00:00Z", "updatedAt": "2024-01-01T00:00:00Z",
            }}}}],
            "nextPageToken": None,
        }
    ))

@pytest.fixture
def dummy_user_id():
    """Dummy: user_id irrelevante para testes que focam na lógica de coleta."""
    return uuid.uuid4()
```

**Coleta bem-sucedida persiste comentários**
- Stub: `httpx.AsyncClient.get` retorna página válida com 3 comentários
- Fake: banco SQLite em memória
- Afirma `db.query(Comment).count() == 3`

**Recoleta do mesmo vídeo não duplica comentários**
- Stub: mesmo stub acima, chamado duas vezes com mesmo `video_id`
- Dummy: `collected_by` (user_id não importa para este cenário)
- Afirma que `COUNT` permanece 3 após a segunda coleta (unicidade por `comment_id`)

**Erros da YouTube API retornam mensagem amigável**
- Stub: `httpx.AsyncClient.get` levanta `httpx.HTTPStatusError` com status 403
  `mocker.patch(..., side_effect=httpx.HTTPStatusError("", request=..., response=...))`
- Afirma HTTP 400 com mensagem sem expor detalhes internos

**Nenhum campo de resposta ou log contém a API key**
- Mock: `logging.Logger.info`, `logging.Logger.error`, `logging.Logger.debug`
  — verifica que nenhuma call recebeu a string da API key como argumento
- Spy alternativo: `mocker.spy(logger, "info")` + `assert api_key not in str(spy.call_args_list)`
- Afirma que o body da response não serializa o campo `api_key`

**API key não aparece no `error_message` se a coleta falhar**
- Stub: `httpx.AsyncClient.get` levanta `Exception("network error")` após primeira página
- Fake: banco em memória
- Afirma `collection.error_message` não contém o valor da API key
- Afirma `collection.status == "failed"`

---

## Melhorias implementadas (pós-spec)

### Import paginado
Arquivos grandes (>4.5MB) são divididos em chunks pelo frontend para respeitar o limite do Vercel:
- `POST /collect/import` — cria a Collection com o primeiro batch (`done: false`)
- `POST /collect/import-chunk` — appenda batches subsequentes (2000 comments/batch)
- Último chunk envia `done: true` → marca `status = "completed"`
- Frontend mostra barra de progresso durante o envio

### Export streaming
Exports usam `yield_per(500)` + `StreamingResponse` com geradores — nunca `.all()`.
O download começa imediatamente, sem carregar todos os comentários na memória.

### Retomada de coleta da lista
Coletas interrompidas (`status = "running"`) exibem botão "Retomar" na tabela, permitindo
restaurar como `active` sem depender do `sessionStorage`.

### Simetria export/import
O JSON exportado por `GET /collect/{id}/export?format=json` pode ser reimportado diretamente
via `POST /collect/import` — formato idêntico, sem modificação.

**Frontend:** tabs "Coletar via API" / "Importar JSON" na CollectPage.

## Dependências com outras USs

- **US-03 (Limpeza):** usa o `collection_id` e os dados dos comentários (especialmente `author_channel_id`, `published_at`, `text_original`) para os algoritmos de seleção
