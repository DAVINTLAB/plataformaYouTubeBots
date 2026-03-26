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
Inicia a coleta de comentários de um vídeo.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "api_key": "AIza...",
  "max_results": 500
}
```

> `video_id`: aceita tanto o ID puro (`dQw4w9WgXcQ`) quanto a URL completa do YouTube.
> `max_results`: opcional, padrão 500, máximo 2000.

**Response 202:**
```json
{
  "collection_id": "uuid",
  "video_id": "dQw4w9WgXcQ",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### `GET /collect/status`
Consulta o status de uma coleta em andamento ou concluída.

**Query params:** `collection_id=uuid`

**Response 200:**
```json
{
  "collection_id": "uuid",
  "video_id": "dQw4w9WgXcQ",
  "status": "completed",
  "total_comments": 487,
  "collected_at": "2024-01-01T00:01:30Z",
  "collected_by": "username"
}
```

> `status`: `pending` | `running` | `completed` | `failed`

---

### `GET /collect`
Lista coletas realizadas pelo usuário autenticado.

**Response 200:**
```json
[
  {
    "collection_id": "uuid",
    "video_id": "string",
    "status": "completed",
    "total_comments": 487,
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

## Service — estratégia de coleta (MVP)

Devido ao timeout de 10s no Vercel, usar **coleta paginada por demanda**:

```python
# services/youtube.py
import httpx

async def fetch_comments_page(
    video_id: str,
    api_key: str,  # valor extraído do SecretStr — nunca logar esta variável
    page_token: str | None = None,
) -> dict:
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText",
    }
    if page_token:
        params["pageToken"] = page_token

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            params=params,
            timeout=8.0,  # margem para o timeout do Vercel
        )
        response.raise_for_status()
        return response.json()

# IMPORTANTE: nunca passar api_key para logger, nunca incluir em mensagens de erro
# Exemplo do que NÃO fazer:
#   logger.info(f"Coletando com key={api_key}")  ← ERRADO
#   raise Exception(f"Falha com key {api_key}")  ← ERRADO
```

**Estratégia de paginação sob demanda:**
1. `POST /collect` inicia e coleta apenas a 1ª página (≤ 100 comentários) de forma síncrona
2. Retorna `collection_id` + `next_page_token` se houver mais páginas
3. Frontend chama `POST /collect/next-page` repetidamente até `next_page_token` ser nulo
4. Cada chamada retorna progresso acumulado

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

- Coleta bem-sucedida persiste comentários corretamente
- Recoleta do mesmo vídeo não duplica comentários (unicidade por `comment_id`)
- Erros da YouTube API retornam mensagem amigável ao usuário
- Nenhum campo de resposta ou log contém o valor da API key
- Se a coleta falhar no meio, a API key não aparece no `error_message`

---

## Dependências com outras USs

- **US-03 (Limpeza):** usa o `collection_id` e os dados dos comentários (especialmente `author_channel_id`, `published_at`, `text_original`) para os algoritmos de seleção
