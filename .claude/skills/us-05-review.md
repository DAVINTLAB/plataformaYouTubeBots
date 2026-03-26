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
    "annotator_a": "user_joao",
    "label_b": "humano",
    "annotator_b": "user_maria",
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
    "annotator": "user_joao",
    "label": "bot",
    "justificativa": "Texto repetido em vários comentários.",
    "annotated_at": "2024-01-01T00:00:00Z"
  },
  "annotation_b": {
    "annotator": "user_maria",
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
  "resolved_by": "admin_carlos",
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
    annotator: str
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

- Resolução de conflito cria registro em `resolutions` com admin e timestamp
- Tentativa de resolver conflito já resolvido retorna 409
- `user` tentando acessar `/review/*` retorna 403
- `GET /review/bots` retorna usuários com pelo menos uma anotação `bot`
- Usuário com consenso `bot`+`bot` aparece em `/review/bots`, não em `/review/conflicts`

---

## Dependências com outras USs

- **US-04:** consome `AnnotationConflict` criados quando dois pesquisadores divergem
- **US-06:** usa `resolutions` para métricas de decisões de desempate no dashboard
