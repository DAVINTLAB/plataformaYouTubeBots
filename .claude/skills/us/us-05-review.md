# US-05 — Desempate de Classificações Conflitantes

## Objetivo

Permitir que o admin resolva dois tipos de pendências em uma tela dedicada:
1. **Conflitos:** usuários em que dois pesquisadores divergiram
2. **Bots sem conflito:** usuários classificados como `bot` por pelo menos um pesquisador (mesmo sem divergência), para revisão adicional do admin

Toda resolução é explícita, registra autoria e timestamp. Não há resolução automática por maioria.

---

## Regras de negócio

- Acesso exclusivo para `admin`
- A tela tem **duas seções**: conflitos pendentes e todos os classificados como bot
- O admin vê as classificações divergentes **lado a lado**, incluindo justificativas
- O admin escolhe `bot` ou `humano` como decisão final — sempre uma das duas opções (sem terceira via)
- A decisão **não pode ser revertida** após confirmação — operação irreversível
- Decisão registra: qual admin decidiu, label escolhido, timestamp
- Após resolução, o conflito sai da fila de pendentes
- A tela suporta filtro por vídeo e por dataset de origem
- Usuários sem conflito classificados como `bot` por todos os anotadores aparecem na seção de bots, **não** na de conflitos

---

## Contrato de API

### `GET /review/conflicts`
Lista conflitos com filtros opcionais.

**Headers:** `Authorization: Bearer <token>` (role: `admin`)

**Query params:** `status=pending|resolved`, `video_id=string`, `dataset_id=uuid`

**Response 200:**
```json
[
  {
    "conflict_id": "uuid",
    "entry_id": "uuid",
    "dataset_name": "dQw4w9_percentil",
    "author_display_name": "string",
    "label_a": "bot",
    "annotator_a": "João Silva",
    "label_b": "humano",
    "annotator_b": "Maria Souza",
    "status": "pending",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### `GET /review/conflicts/{conflict_id}`
Detalhe completo de um conflito para a tela de decisão.

**Response 200:**
```json
{
  "conflict_id": "uuid",
  "status": "pending",
  "dataset_name": "dQw4w9_percentil",
  "author_channel_id": "UC...",
  "author_display_name": "string",
  "comments": [
    {
      "text_original": "string",
      "like_count": 0,
      "published_at": "2024-01-01T00:00:00Z"
    }
  ],
  "annotation_a": {
    "annotator": "João Silva",
    "label": "bot",
    "justificativa": "Texto repetido em vários comentários.",
    "annotated_at": "2024-01-01T00:00:00Z"
  },
  "annotation_b": {
    "annotator": "Maria Souza",
    "label": "humano",
    "justificativa": null,
    "annotated_at": "2024-01-01T00:10:00Z"
  },
  "resolved_by": null,
  "resolved_label": null,
  "resolved_at": null
}
```

---

### `GET /review/bots`
Lista todos os usuários classificados como `bot` por pelo menos um anotador (incluindo os sem conflito).

**Query params:** `video_id=string`, `dataset_id=uuid`

**Response 200:**
```json
[
  {
    "entry_id": "uuid",
    "dataset_name": "string",
    "author_display_name": "string",
    "bot_annotations": 2,
    "human_annotations": 0,
    "has_conflict": false,
    "conflict_id": null
  }
]
```

---

### `POST /review/resolve`
Registra a decisão do admin para um conflito.

**Request:**
```json
{
  "conflict_id": "uuid",
  "resolved_label": "bot"
}
```

**Response 200:**
```json
{
  "conflict_id": "uuid",
  "status": "resolved",
  "resolved_label": "bot",
  "resolved_by": "Carlos Admin",
  "resolved_at": "2024-01-01T00:20:00Z"
}
```

**Erros:**
- `409` — conflito já resolvido
- `422` — `resolved_label` não é `"bot"` nem `"humano"`
- `403` — usuário não tem papel `admin`

---

### `GET /review/stats`
Resumo de pendências para o painel do admin.

**Response 200:**
```json
{
  "total_conflicts": 27,
  "pending_conflicts": 14,
  "resolved_conflicts": 13,
  "total_bots_flagged": 58
}
```

---

## Schema de banco (SQLAlchemy)

`AnnotationConflict` já definido em US-04. Tabela `resolutions` separada para histórico auditável:

```python
# models/resolution.py
class Resolution(Base):
    """Registro imutável de cada decisão de desempate do admin."""
    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conflict_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotation_conflicts.id"), unique=True)
    resolved_label: Mapped[str] = mapped_column(String(8), nullable=False)
    resolved_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("resolved_label IN ('bot', 'humano')", name="ck_resolution_label"),
    )
```

---

## Schemas Pydantic

```python
# schemas/review.py
class ResolveRequest(BaseModel):
    conflict_id: uuid.UUID
    resolved_label: Literal["bot", "humano"]

class AnnotationSide(BaseModel):
    annotator: str  # users.name do pesquisador (não username)
    label: str
    justificativa: str | None
    annotated_at: datetime

class ConflictDetail(BaseModel):
    conflict_id: uuid.UUID
    status: Literal["pending", "resolved"]
    dataset_name: str
    author_channel_id: str
    author_display_name: str
    comments: list[dict]
    annotation_a: AnnotationSide
    annotation_b: AnnotationSide
    resolved_by: str | None
    resolved_label: str | None
    resolved_at: datetime | None
```

---

## Service

```python
# services/review.py
def resolve_conflict(db, conflict_id, admin_id, resolved_label) -> Resolution:
    conflict = db.get(AnnotationConflict, conflict_id)

    if not conflict:
        raise NotFoundError()

    if conflict.status == "resolved":
        raise ConflictError("Este conflito já foi resolvido.")

    # Atualizar o conflito
    conflict.status = "resolved"
    conflict.resolved_by = admin_id
    conflict.resolved_label = resolved_label
    conflict.resolved_at = datetime.utcnow()

    # Inserir na tabela de resolutions (imutável)
    resolution = Resolution(
        conflict_id=conflict_id,
        resolved_label=resolved_label,
        resolved_by=admin_id,
    )
    db.add(resolution)
    db.commit()
    return resolution
```

---

## Frontend — componentes sugeridos

```
pages/Review/
├── ReviewPage.tsx               # layout com abas: "Conflitos" | "Classificados como Bot"
├── ConflictList.tsx             # lista de conflitos com filtros de status/vídeo/dataset
├── ConflictDetailPage.tsx       # visão detalhada: comentários + anotações lado a lado
├── SideBySideAnnotations.tsx    # colunas: anotador A vs anotador B com justificativas
├── ResolveButtons.tsx           # botões "Definir como Bot" / "Definir como Humano" + confirmação
├── BotsList.tsx                 # lista de usuários flagados como bot (seção 2)
└── useReview.ts                 # hook: listConflicts(), getConflict(), resolve(), listBots()
```

**UX obrigatória:**
- Botão de decisão abre modal de confirmação — operação irreversível
- Conflitos resolvidos exibem badge colorido com a decisão e quem resolveu
- Badge contador de conflitos pendentes visível no menu de navegação para o admin
- Filtros de vídeo e dataset funcionam nas duas abas
- Exibir todos os comentários do usuário em conflito para dar contexto à decisão

---

## Casos de erro

| Cenário                              | HTTP | Mensagem ao usuário                                       |
|--------------------------------------|------|-----------------------------------------------------------|
| Conflito já resolvido                | 409  | "Este conflito já foi resolvido."                         |
| Usuário sem papel admin              | 403  | "Apenas administradores podem resolver conflitos."        |
| Conflito não encontrado              | 404  | —                                                         |

---

## Testes obrigatórios (Pytest)

### Referência de dublês

| Dublê | Quando usar                                                                   |
|-------|-------------------------------------------------------------------------------|
| Stub  | Controlar `get_current_user` (admin vs user) e estado do conflito no banco    |
| Mock  | Verificar que `Resolution` foi inserida exatamente uma vez                    |
| Dummy | `conflict_id` inválido para testar 404 sem precisar de banco populado         |
| Fake  | Banco SQLite em memória para testar o fluxo completo de resolução             |

### Casos de teste

```python
# conftest.py
@pytest.fixture
def stub_admin(mocker):
    """Stub: get_current_user retorna admin."""
    admin = User(id=uuid.uuid4(), username="carlos.admin", name="Carlos Admin", role="admin")
    mocker.patch("routers.review.get_current_user", return_value=admin)
    return admin

@pytest.fixture
def stub_user(mocker):
    """Stub: get_current_user retorna pesquisador sem permissão de admin."""
    user = User(id=uuid.uuid4(), username="joao.silva", name="João Silva", role="user")
    mocker.patch("routers.review.get_current_user", return_value=user)
    return user

@pytest.fixture
def fake_db_with_conflict(fake_db):
    """Fake: banco em memória pré-populado com um conflito pendente."""
    # insere dois comentários, duas anotações divergentes e um AnnotationConflict
    ...
    return fake_db
```

**Resolução cria registro em `resolutions` com admin e timestamp**
- Stub: `get_current_user` retorna admin
- Fake: banco com conflito `pending` pré-inserido
- Mock: `db.add` — verifica que foi chamado com instância de `Resolution`
  `mock_add.assert_called_once()` filtrando por tipo `Resolution`
- Afirma `resolution.resolved_by == admin.id` e `resolution.resolved_at` não é None

**Conflito já resolvido retorna 409**
- Stub: `get_current_user` retorna admin
- Fake: banco com `AnnotationConflict.status = "resolved"`
- Afirma HTTP 409 sem criar novo registro em `resolutions`

**`user` tentando acessar `/review/*` retorna 403**
- Stub: `get_current_user` retorna `User` com `role="user"`
- Dummy: `conflict_id` = `uuid.uuid4()` (não precisa existir — a checagem de role ocorre antes)
- Afirma HTTP 403

**`GET /review/bots` retorna comentários com pelo menos uma anotação `bot`**
- Fake: banco com 3 comentários — (A) dois `bot`, (B) um `bot` + um `humano`, (C) dois `humano`
- Stub: `get_current_user` retorna admin
- Afirma que A e B aparecem no resultado, C não aparece

**Consenso `bot`+`bot` aparece em `/review/bots`, não em `/review/conflicts`**
- Fake: banco com comentário anotado como `bot` por dois pesquisadores (sem `AnnotationConflict`)
- Stub: `get_current_user` retorna admin
- Afirma comentário presente em `GET /review/bots`
- Afirma comentário **ausente** em `GET /review/conflicts`

---

## Import/Export simétrico

### Export — `GET /review/export`

Exporta o dataset final (anotado + desempatado) — resultado final da pesquisa.

**JSON (formato simétrico — aceito pelo import):**
```json
{
  "dataset_name": "dQw4w9_percentil",
  "video_id": "dQw4w9WgXcQ",
  "exported_at": "2024-01-15T10:00:00Z",
  "comments": [
    {
      "comment_db_id": "uuid",
      "author_channel_id": "UC...",
      "author_display_name": "string",
      "text_original": "comentário...",
      "final_label": "bot",
      "annotations": [
        {
          "annotator": "João Silva",
          "label": "bot",
          "justificativa": "Texto repetido."
        },
        {
          "annotator": "Maria Souza",
          "label": "humano",
          "justificativa": null
        }
      ],
      "resolution": {
        "resolved_by": "Carlos Admin",
        "resolved_label": "bot",
        "resolved_at": "2024-01-10T00:20:00Z"
      }
    }
  ]
}
```

O `final_label` é calculado: se há resolução, usa `resolved_label`; se há consenso, usa o label unânime.

### Import — `POST /review/import`

Aceita o **mesmo formato JSON** do export — simetria total.
Reimporta um dataset já revisado (ex: migração entre ambientes ou restauração).
Resolve referências por `video_id` + `dataset_name`.

**Frontend:** aba "Importar JSON" na ReviewPage, separada das abas "Conflitos" / "Classificados como Bot" (padrão de tabs obrigatório).

## Dependências com outras USs

- **US-04:** consome `AnnotationConflict` criados quando dois pesquisadores divergem
- **US-06:** usa `resolutions` para métricas de decisões de desempate no dashboard
