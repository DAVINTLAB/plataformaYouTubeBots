# US-07 — Catálogo Centralizado de Dados

## Objetivo

Página centralizada para gestão de todos os dados da plataforma, organizada por estágio do pipeline. Permite visualizar o estado de coletas, datasets e anotações, monitorar o uso do banco e gerenciar exports e deleções sem navegar entre etapas.

---

## Regras de negócio

- Todos os usuários autenticados acessam o catálogo (leitura)
- Qualquer pesquisador pode exportar e deletar coletas (dados são compartilhados)
- Coletas em andamento (status `running`) não podem ser deletadas
- Seções de datasets (US-03) e anotações (US-04/US-05) aparecem como placeholder enquanto as US não estiverem implementadas
- Resumo de uso deve refletir o estado real do banco (relevante para Neon free tier — 0.5 GB)

---

## Contrato de API

### `GET /data/summary`
Retorna contagem de registros e estimativa de uso do banco.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "collections_count": 12,
  "comments_count": 8450,
  "datasets_count": 3,
  "annotations_count": 1200,
  "estimated_size_mb": 42.5
}
```

---

### `GET /data/collections`
Lista todas as coletas com metadados do vídeo.

**Response 200:**
```json
[
  {
    "collection_id": "uuid",
    "video_id": "dQw4w9WgXcQ",
    "video_title": "Never Gonna Give You Up",
    "total_comments": 657,
    "status": "completed",
    "enrich_status": "done",
    "channel_dates_failed": false,
    "collected_by": "admin",
    "created_at": "2026-03-28T10:00:00Z",
    "completed_at": "2026-03-28T10:05:00Z"
  }
]
```

---

### `GET /data/datasets`
Lista datasets gerados pela limpeza (US-03).

**Response 200:**
```json
[
  {
    "dataset_id": "uuid",
    "name": "dQw4w9WgXcQ_percentil_media",
    "collection_id": "uuid",
    "criteria": ["percentil", "media"],
    "total_selected": 120,
    "created_at": "2026-03-29T14:00:00Z"
  }
]
```

> Retorna lista vazia enquanto US-03 não estiver implementada.

---

### `GET /data/annotations`
Retorna progresso de anotação por dataset (US-04/US-05).

**Response 200:**
```json
[
  {
    "dataset_id": "uuid",
    "dataset_name": "dQw4w9WgXcQ_percentil_media",
    "total": 120,
    "annotated": 85,
    "pending": 35,
    "conflicts": 8,
    "conflicts_resolved": 5
  }
]
```

> Retorna lista vazia enquanto US-04 não estiver implementada.

---

## Schema de banco

Não cria tabelas novas — consulta as existentes:
- `collections` (US-02)
- `comments` (US-02)
- `datasets` (US-03, futuro)
- `annotations` (US-04, futuro)
- `resolutions` (US-05, futuro)

Para a estimativa de tamanho, usa `pg_total_relation_size()` do PostgreSQL.

---

## Schemas Pydantic

```python
# schemas/data.py
class DataSummary(BaseModel):
    collections_count: int
    comments_count: int
    datasets_count: int
    annotations_count: int
    estimated_size_mb: float

class DataCollection(BaseModel):
    collection_id: uuid.UUID
    video_id: str
    video_title: str | None = None
    total_comments: int | None = None
    status: str
    enrich_status: str | None = None
    channel_dates_failed: bool | None = None
    collected_by: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class DataDataset(BaseModel):
    dataset_id: uuid.UUID
    name: str
    collection_id: uuid.UUID
    criteria: list[str]
    total_selected: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DataAnnotationProgress(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    total: int
    annotated: int
    pending: int
    conflicts: int
    conflicts_resolved: int
```

---

## Service

```python
# services/data.py
def get_summary(db: Session) -> dict:
    """Contagem de registros + estimativa de tamanho via pg_total_relation_size."""
    ...

def list_all_collections(db: Session) -> list[Collection]:
    """Todas as coletas, sem filtro por usuário."""
    ...

def list_all_datasets(db: Session) -> list:
    """Todos os datasets limpos. Retorna [] se tabela não existe."""
    ...

def get_annotation_progress(db: Session) -> list[dict]:
    """Progresso de anotação por dataset. Retorna [] se tabela não existe."""
    ...
```

---

## Frontend — componentes sugeridos

```
pages/Data/
├── DataPage.tsx             # página principal com seções colapsáveis
├── SummaryCard.tsx          # card com contadores e barra de uso
├── CollectionsTable.tsx     # tabela de coletas com export/delete
├── DatasetsTable.tsx        # tabela de datasets (placeholder)
├── AnnotationsTable.tsx     # tabela de anotações (placeholder)
└── useData.ts               # hook: getSummary(), listCollections(), etc.
```

**UX obrigatória:**
- Seções colapsáveis por estágio do pipeline
- Card de resumo no topo com contadores e barra visual de uso do banco
- Tabela de coletas com StatusBadge, export JSON/CSV e coluna destrutiva isolada
- Placeholder com mensagem informativa para seções não implementadas
- Seguir padrões de `ux-ui.md` (max-w-6xl, cores semânticas, Nielsen)

---

## Card na HomePage

```python
{
    step: 0,  # não é etapa do pipeline
    title: "Catálogo de Dados",
    description: "Visualize e gerencie todas as coletas, datasets e anotações da plataforma.",
    route: "/data",
    adminOnly: false,
    available: true,
    icon: <IconDatabase />,
}
```

Posição: seção separada "Ferramentas" abaixo do pipeline, ao lado do card de "Gerenciar Usuários" (admin).

---

## Casos de erro

| Cenário | HTTP | Mensagem ao usuário |
|---|---|---|
| Sem autenticação | 401 | "Token de acesso inválido ou expirado." |
| Deletar coleta em andamento | 409 | "Não é possível deletar uma coleta em andamento." |
| Coleta não encontrada | 404 | "Coleta não encontrada." |

---

## Testes obrigatórios (Pytest)

| Dublê | Quando usar |
|---|---|
| Fake | PostgreSQL via Docker (nunca SQLite) |
| Stub | Dados pré-inseridos para verificar contagem e listagem |

### Casos de teste

**Summary retorna contadores corretos**
- Inserir 2 coletas com 5 comentários cada
- Afirma `collections_count == 2`, `comments_count == 10`
- Afirma `estimated_size_mb > 0`

**Listagem de coletas é compartilhada**
- Inserir coleta como user A, consultar como user B
- Afirma que user B vê a coleta de user A

**Deleção compartilhada**
- Inserir coleta como user A, deletar como user B
- Afirma que a coleta foi removida

**Datasets e anotações retornam vazio quando tabelas não existem**
- Afirma que `GET /data/datasets` retorna `[]`
- Afirma que `GET /data/annotations` retorna `[]`

---

## Dependências com outras USs

- **US-02 (Coleta):** fonte de dados para a seção de coletas
- **US-03 (Limpeza):** fonte de dados para a seção de datasets (quando implementada)
- **US-04 (Anotação):** fonte de dados para a seção de anotações (quando implementada)
- **US-05 (Revisão):** progresso de conflitos resolvidos (quando implementada)
