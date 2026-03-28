# US-04 — Anotação de Comentários

## Objetivo

Permitir que pesquisadores classifiquem **cada comentário individualmente** como `bot` ou `humano`,
com contexto: antes de anotar, o pesquisador vê **todos os comentários** do usuário do YouTube no
vídeo, para tomar uma decisão informada sobre cada um. O progresso é salvo automaticamente e pode
ser retomado em sessões futuras.

---

## Regras de negócio

- A unidade de anotação é o **comentário** — cada comentário recebe seu próprio rótulo
- Antes de anotar, o pesquisador vê **todos os comentários do mesmo usuário** agrupados, para ter contexto do padrão de comportamento
- Classificações válidas: `bot` ou `humano` — sem `incerto`
- Anotação `bot` **obrigatoriamente** exige `justificativa` preenchida — validado no backend (HTTP 422) e bloqueado no frontend
- `justificativa` é **opcional** para `humano`
- **Rótulo pode ser alterado após salvo** — a anotação mais recente substitui a anterior
- Dois pesquisadores podem anotar o mesmo conjunto sem sobrescrever os dados um do outro
- Conflito ocorre automaticamente quando dois pesquisadores divergem no **mesmo comentário**
- Progresso de anotação é recuperado após logout/login
- Upload de CSV em lote importa anotações sem duplicar registros existentes
- Download exporta apenas as anotações do pesquisador autenticado
- Atalhos de teclado para anotação rápida

---

## Contrato de API

### `GET /annotate/users`
Lista os usuários do YouTube presentes em um dataset, com progresso de anotação de cada um.

**Query params:** `dataset_id=uuid`

**Response 200:**
```json
{
  "dataset_id": "uuid",
  "dataset_name": "dQw4w9_percentil_intervalo",
  "total_users": 43,
  "total_comments": 187,
  "annotated_comments_by_me": 52,
  "items": [
    {
      "entry_id": "uuid",
      "author_channel_id": "UC...",
      "author_display_name": "string",
      "comment_count": 7,
      "my_annotated_count": 3,
      "my_pending_count": 4
    }
  ]
}
```

---

### `GET /annotate/comments/{entry_id}`
Retorna todos os comentários de um usuário do YouTube no dataset, com as anotações já feitas pelo pesquisador atual.

**Response 200:**
```json
{
  "entry_id": "uuid",
  "author_display_name": "string",
  "author_channel_id": "string",
  "comments": [
    {
      "comment_db_id": "uuid",
      "text_original": "string",
      "like_count": 0,
      "reply_count": 0,
      "published_at": "2024-01-01T00:00:00Z",
      "my_annotation": {
        "label": "bot",
        "justificativa": "Texto repetido.",
        "annotated_at": "2024-01-01T00:05:00Z"
      }
    }
  ]
}
```

> `my_annotation`: `null` se o pesquisador ainda não anotou aquele comentário.

---

### `POST /annotate`
Salva ou atualiza a anotação de um comentário (upsert — permite alterar após salvo).

**Request:**
```json
{
  "comment_db_id": "uuid",
  "label": "bot",
  "justificativa": "Texto idêntico em múltiplos comentários, sem resposta a ninguém."
}
```

**Response 201** (criação) ou **200** (atualização):
```json
{
  "annotation_id": "uuid",
  "comment_db_id": "uuid",
  "label": "bot",
  "conflict_created": false
}
```

> `conflict_created: true` — esta anotação divergiu de outro pesquisador no mesmo comentário.

**Erros:**
- `422` — label `bot` sem `justificativa`

---

### `GET /annotate/my-progress`
Progresso do pesquisador autenticado por dataset.

**Response 200:**
```json
[
  {
    "dataset_id": "uuid",
    "dataset_name": "string",
    "total_comments": 187,
    "annotated": 52,
    "bots": 21,
    "humans": 31,
    "percent_complete": 27.8
  }
]
```

---

### `POST /annotate/import`
Importa anotações em lote via CSV. Faz upsert — não duplica existentes.

**Body:** `multipart/form-data` com campo `file` (CSV)

**Formato CSV esperado:**
```
comment_db_id,label,justificativa
uuid1,bot,"texto da justificativa"
uuid2,humano,
```

**Response 200:**
```json
{ "imported": 40, "updated": 2, "skipped": 1, "errors": [] }
```

---

### `GET /annotate/export`
Exporta as anotações do pesquisador autenticado em CSV.

**Query params:** `dataset_id=uuid` (opcional)

**Response 200:** arquivo CSV para download com `comment_db_id,label,justificativa`.

---

## Schema de banco (SQLAlchemy)

```python
# models/annotation.py
class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id"))  # comentário individual
    annotator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    label: Mapped[str] = mapped_column(String(8), nullable=False)
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    comment: Mapped["Comment"] = relationship()
    annotator: Mapped["User"] = relationship()

    __table_args__ = (
        # um pesquisador tem exatamente uma anotação por comentário (upsert substitui)
        UniqueConstraint("comment_id", "annotator_id", name="uq_comment_annotator"),
        CheckConstraint("label IN ('bot', 'humano')", name="ck_valid_label"),
    )

class AnnotationConflict(Base):
    __tablename__ = "annotation_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id"), unique=True)
    annotation_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotations.id"))
    annotation_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotations.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | resolved
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # preenchidos em US-05
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_label: Mapped[str | None] = mapped_column(String(8), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

> **Nota:** a FK é para `comments.id` (comentário bruto da US-02), não para `dataset_entries`
> (que representa o usuário). Um comentário pode estar em múltiplos datasets — a anotação
> é do comentário em si, compartilhada entre datasets.

---

## Schemas Pydantic

```python
# schemas/annotate.py
class AnnotationCreate(BaseModel):
    comment_db_id: uuid.UUID
    label: Literal["bot", "humano"]
    justificativa: str | None = None

    @model_validator(mode="after")
    def justificativa_required_for_bot(self):
        if self.label == "bot" and not (self.justificativa or "").strip():
            raise ValueError("justificativa é obrigatória para classificação 'bot'.")
        return self

class AnnotationResult(BaseModel):
    annotation_id: uuid.UUID
    comment_db_id: uuid.UUID
    label: str
    conflict_created: bool
```

---

## Service — upsert e detecção de conflito

```python
# services/annotate.py
def upsert_annotation(db, comment_id, annotator_id, label, justificativa) -> AnnotationResult:
    # Upsert: cria ou atualiza a anotação do pesquisador para este comentário
    existing = db.query(Annotation).filter_by(
        comment_id=comment_id, annotator_id=annotator_id
    ).first()

    if existing:
        existing.label = label
        existing.justificativa = justificativa
        existing.updated_at = datetime.utcnow()
        annotation = existing
    else:
        annotation = Annotation(
            comment_id=comment_id, annotator_id=annotator_id,
            label=label, justificativa=justificativa
        )
        db.add(annotation)

    db.flush()

    # Verificar conflito: outro pesquisador anotou este comentário com label diferente?
    other = db.query(Annotation).filter(
        Annotation.comment_id == comment_id,
        Annotation.annotator_id != annotator_id,
    ).first()

    conflict_created = False

    if other and other.label != label:
        conflict = db.query(AnnotationConflict).filter_by(comment_id=comment_id).first()
        if not conflict:
            conflict = AnnotationConflict(
                comment_id=comment_id,
                annotation_a_id=other.id,
                annotation_b_id=annotation.id,
            )
            db.add(conflict)
            conflict_created = True
        elif conflict.status == "resolved":
            # reanotação após resolução → reabre o conflito
            conflict.status = "pending"
            conflict.resolved_by = None
            conflict.resolved_label = None
            conflict.resolved_at = None
            conflict_created = True

    db.commit()
    return AnnotationResult(
        annotation_id=annotation.id,
        comment_db_id=comment_id,
        label=label,
        conflict_created=conflict_created,
    )
```

---

## Frontend — componentes sugeridos

```
pages/Annotate/
├── AnnotatePage.tsx           # seleção de dataset → lista de usuários do YouTube
├── UserCommentsList.tsx       # exibe TODOS os comentários do usuário agrupados
│                              # cada comentário tem seus próprios botões bot/humano
├── CommentAnnotationRow.tsx   # linha de comentário + badge de anotação atual + botões
├── JustificativaField.tsx     # campo de texto — aparece e é obrigatório ao selecionar "bot"
├── ProgressBar.tsx            # barra X/Y comentários anotados neste dataset
├── ImportExportPanel.tsx      # upload CSV + botão download
└── useAnnotate.ts             # hook: listUsers(), getComments(), submitAnnotation(), import/export
```

**UX obrigatória:**
- Ao abrir um usuário: exibir todos os seus comentários em sequência cronológica
- Cada comentário tem seus próprios botões "Bot" / "Humano" — anotação independente por comentário
- Campo `justificativa` aparece inline no comentário ao selecionar "bot", não em modal separado
- Botão de confirmação desabilitado enquanto `justificativa` vazio no modo bot
- Comentários já anotados exibem badge colorido (editável via clique)
- Atalhos de teclado: `B` → bot, `H` → humano para o comentário em foco; `Tab` navega entre comentários
- Ao receber `conflict_created: true`, exibir toast informativo discreto

---

## Casos de erro

| Cenário                        | HTTP | Mensagem ao usuário                              |
|--------------------------------|------|--------------------------------------------------|
| `bot` sem `justificativa`      | 422  | "Informe a justificativa para classificar como bot." |
| Dataset não encontrado         | 404  | —                                                |
| Comentário não encontrado      | 404  | —                                                |
| CSV com formato inválido       | 422  | "Arquivo CSV inválido. Verifique o formato."     |

---

## Testes obrigatórios (Pytest)

### Referência de dublês

| Dublê | Quando usar                                                                        |
|-------|------------------------------------------------------------------------------------|
| Stub  | Controlar `get_current_user` (retornar pesquisador A ou B conforme o cenário)      |
| Mock  | Verificar que o conflito foi criado exatamente uma vez (sem criar duplicatas)      |
| Spy   | Observar se `db.add` foi chamado com um `AnnotationConflict` (sem substituir o DB) |
| Dummy | `entry_id` / `comment_db_id` irrelevante quando o teste foca na validação Pydantic |
| Fake  | Banco SQLite em memória para testar upsert e detecção de conflito end-to-end       |

### Casos de teste

```python
# conftest.py
@pytest.fixture
def fake_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def stub_user_a(mocker):
    """Stub: get_current_user retorna pesquisador A."""
    user = User(id=uuid.uuid4(), username="joao.silva", name="João Silva", role="user")
    mocker.patch("routers.annotate.get_current_user", return_value=user)
    return user

@pytest.fixture
def stub_user_b(mocker):
    """Stub: get_current_user retorna pesquisador B (para simular segundo anotador)."""
    user = User(id=uuid.uuid4(), username="maria.souza", name="Maria Souza", role="user")
    mocker.patch("routers.annotate.get_current_user", return_value=user)
    return user
```

**`bot` sem `justificativa` retorna 422**
- Dummy: `comment_db_id` = `uuid.uuid4()` (não precisa existir no banco — a validação é Pydantic)
- Sem dublê de banco (erro ocorre antes de chegar ao service)
- Afirma HTTP 422 com mensagem sobre `justificativa`

**Dois pesquisadores com labels iguais → sem conflito**
- Stub: `get_current_user` alternado entre `stub_user_a` e `stub_user_b`
- Fake: banco em memória com comentário pré-inserido
- Afirma `db.query(AnnotationConflict).count() == 0`

**Dois pesquisadores com labels diferentes → `AnnotationConflict` criado**
- Stub: `get_current_user` alterna entre usuário A (label `bot`) e usuário B (label `humano`)
- Fake: banco em memória
- Spy: `mocker.spy(db, "add")` — verifica que `add` foi chamado com instância de `AnnotationConflict`
- Afirma `conflict_created == True` na resposta e `db.query(AnnotationConflict).count() == 1`

**Reannotation altera label e `updated_at`, mantém `annotation_id`**
- Stub: `get_current_user` retorna mesmo usuário nas duas chamadas
- Fake: banco em memória
- Guarda `annotation_id` da primeira chamada; afirma que é o mesmo após a segunda
- Afirma `label` e `updated_at` foram alterados

**Segundo conflito no mesmo comentário não cria duplicata**
- Stub: dois usuários divergem, depois um reanota mantendo divergência
- Mock: `db.add` — verifica que foi chamado com `AnnotationConflict` apenas uma vez no total
  `mock_add.assert_called_once()` para instâncias de `AnnotationConflict`

**Importação CSV faz upsert sem duplicar**
- Fake: banco em memória com algumas anotações pré-existentes
- Stub: `get_current_user` retorna usuário autenticado
- Afirma que `COUNT(annotations)` não aumenta para linhas já existentes

**Export retorna apenas anotações do pesquisador autenticado**
- Stub: `get_current_user` retorna usuário A
- Fake: banco com anotações de usuário A e usuário B
- Afirma que todas as linhas do CSV têm `annotator_id == user_a.id`

---

## Dependências com outras USs

- **US-03:** requer `dataset_id` para listar os usuários (`dataset_entries`) cujos comentários serão anotados
- **US-05:** consome os `AnnotationConflict` com `status = "pending"` por comentário
- **US-06:** usa contagem de anotações, conflitos e agreement rate por comentário
