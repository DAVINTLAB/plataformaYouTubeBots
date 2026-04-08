# US-03 — Limpeza e Seleção de Dataset

## Objetivo

A partir de uma coleta (US-02), aplicar critérios estatísticos e comportamentais para identificar
**usuários do YouTube** com perfil suspeito de bot. Apenas os usuários selecionados são persistidos
como dataset — os não selecionados não são armazenados (a coleta bruta da US-02 serve de referência).

---

## Regras de negócio

### Unidade de análise: usuário, não comentário
A limpeza agrupa comentários por `author_channel_id` e analisa o **comportamento do usuário**,
não o comentário individual.

### Critérios independentes → datasets separados
Cada critério executado individualmente gera **seu próprio dataset**. Múltiplos critérios
selecionados ao mesmo tempo geram **um único dataset de interseção** (usuários que atendem todos).

### Convenção de nomenclatura obrigatória

| Critério ativo          | Sufixo no nome   |
|-------------------------|------------------|
| Percentil top 30%       | `_percentil`     |
| Acima da média (IQR)    | `_media`         |
| Acima da moda (IQR)     | `_moda`          |
| Acima da mediana (IQR)  | `_mediana`       |
| Comentários curtos/rep. | `_curtos`        |
| Intervalo temporal      | `_intervalo`     |
| Comentários idênticos   | `_identicos`     |
| Perfil suspeito         | `_perfil`        |

Exemplos: `dQw4w9_percentil`, `dQw4w9_media`, `dQw4w9_percentil_intervalo_identicos`

### API keys das APIs externas
YouTube Data API v3 e SocialBlade API são recebidas por requisição como `SecretStr` —
mesmo padrão da US-02: nunca persistidas, nunca logadas, descartadas ao fim da requisição.

### Remoção de outliers via IQR
Nos critérios estatísticos (média, moda, mediana), outliers são removidos **apenas para o cálculo
da medida central** — não para excluir usuários do dataset final.

---

## Grupos de critérios

### Grupo 1 — Critérios estatísticos de volume (por nº de comentários do usuário)

- **Percentil:** seleciona usuários no **top 30%** de volume de comentários no vídeo
- **Média:** calcula distribuição de comentários/usuário, remove outliers via IQR, seleciona acima da média resultante
- **Moda:** mesmo processo, threshold pela moda
- **Mediana:** mesmo processo, threshold pela mediana

Cada um é independente e executável isoladamente.

### Grupo 2 — Critérios comportamentais

- **Curtos/repetitivos:** comentários abaixo de N caracteres (configurável) ou com alto índice de repetição entre si para o mesmo usuário
- **Intervalo temporal:** intervalo entre comentários consecutivos do mesmo usuário abaixo de T segundos (configurável)
- **Idênticos em múltiplos vídeos:** comentários iguais ou quase-iguais postados em múltiplos vídeos pelo mesmo usuário (requer cruzar com outras coletas no banco)
- **Perfil suspeito:** sem foto de avatar, data de criação recente ou canal sem vídeos — consultado via YouTube Data API v3 e/ou SocialBlade API

---

## Contrato de API

### `GET /clean/preview`
Retorna contagem estimada por critério **sem persistir nada**. Exibe as três medidas centrais.

**Query params:** `collection_id=uuid&criteria=percentil,media,intervalo&threshold_chars=20&threshold_seconds=30`

**Response 200:**
```json
{
  "collection_id": "uuid",
  "total_users": 312,
  "central_measures": {
    "mean": 4.2,
    "mode": 1.0,
    "median": 2.0,
    "iqr_lower": 1.0,
    "iqr_upper": 6.0
  },
  "by_criteria": {
    "percentil": { "selected_users": 94 },
    "media":     { "selected_users": 51 },
    "moda":      { "selected_users": 78 },
    "mediana":   { "selected_users": 61 },
    "curtos":    { "selected_users": 23, "threshold_chars": 20 },
    "intervalo": { "selected_users": 18, "threshold_seconds": 30 },
    "identicos": { "selected_users": 7 },
    "perfil":    { "selected_users": 12 }
  },
  "intersection_if_combined": 8
}
```

---

### `POST /clean`
Cria um dataset persistindo os usuários selecionados.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "collection_id": "uuid",
  "criteria": ["percentil", "intervalo"],
  "thresholds": {
    "threshold_chars": 20,
    "threshold_seconds": 30
  },
  "youtube_api_key": "AIza...",
  "socialblade_api_key": "sb_..."
}
```

> `youtube_api_key` e `socialblade_api_key`: obrigatórios apenas se o critério `perfil` estiver ativo.
> Ambos como `SecretStr`.

**Response 201:**
```json
{
  "dataset_id": "uuid",
  "name": "dQw4w9_percentil_intervalo",
  "collection_id": "uuid",
  "video_id": "dQw4w9WgXcQ",
  "total_users_original": 312,
  "total_users_selected": 18,
  "criteria_applied": ["percentil", "intervalo"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### `GET /clean/datasets`
Lista todos os datasets gerados para um vídeo.

**Query params:** `video_id=dQw4w9WgXcQ` (opcional)

**Response 200:**
```json
[
  {
    "dataset_id": "uuid",
    "name": "dQw4w9_percentil_intervalo",
    "video_id": "string",
    "total_users_selected": 18,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### `GET /clean/datasets/{dataset_id}/download`
Baixa o dataset em CSV ou JSON.

**Query params:** `format=csv` | `format=json`

**Response 200:** arquivo para download com os usuários selecionados e seus comentários.

---

## Schema de banco (SQLAlchemy)

```python
# models/dataset.py
class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"))
    criteria_applied: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    total_users_original: Mapped[int] = mapped_column(Integer, nullable=False)
    total_users_selected: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    entries: Mapped[list["DatasetEntry"]] = relationship(back_populates="dataset")

class DatasetEntry(Base):
    """Um usuário do YouTube selecionado como suspeito."""
    __tablename__ = "dataset_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"))
    author_channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_display_name: Mapped[str] = mapped_column(String(256))
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False)  # nº de comentários do usuário nesta coleta
    matched_criteria: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    dataset: Mapped["Dataset"] = relationship(back_populates="entries")

    __table_args__ = (
        UniqueConstraint("dataset_id", "author_channel_id", name="uq_dataset_user"),
    )
```

---

## Schemas Pydantic

```python
# schemas/clean.py
VALID_CRITERIA = Literal[
    "percentil", "media", "moda", "mediana",
    "curtos", "intervalo", "identicos", "perfil"
]

class CleanThresholds(BaseModel):
    threshold_chars: int = Field(default=20, ge=1, le=500)      # para critério "curtos"
    threshold_seconds: int = Field(default=30, ge=1, le=3600)   # para critério "intervalo"

class DatasetCreate(BaseModel):
    collection_id: uuid.UUID
    criteria: list[VALID_CRITERIA] = Field(min_length=1)
    thresholds: CleanThresholds = CleanThresholds()
    youtube_api_key: SecretStr | None = None
    socialblade_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def api_keys_required_for_perfil(self):
        if "perfil" in self.criteria and not self.youtube_api_key:
            raise ValueError("youtube_api_key é obrigatória para o critério 'perfil'.")
        return self
```

---

## Service — algoritmos

```python
# services/clean.py
import statistics
from collections import Counter

def group_by_user(comments: list[Comment]) -> dict[str, list[Comment]]:
    """Agrupa comentários por author_channel_id."""
    groups: dict[str, list[Comment]] = {}
    for c in comments:
        groups.setdefault(c.author_channel_id or c.author_display_name, []).append(c)
    return groups

def remove_outliers_iqr(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values
    q1 = statistics.quantiles(values, n=4)[0]
    q3 = statistics.quantiles(values, n=4)[2]
    iqr = q3 - q1
    return [v for v in values if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]

def select_percentil(user_counts: dict[str, int]) -> set[str]:
    """Top 30% por volume de comentários."""
    threshold_idx = int(len(user_counts) * 0.70)
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
    return {uid for uid, _ in sorted_users[:max(1, len(sorted_users) - threshold_idx)]}

def select_by_central_measure(user_counts: dict[str, int], measure: str) -> set[str]:
    counts = list(user_counts.values())
    clean_counts = remove_outliers_iqr(counts)  # remove outliers só para calcular o threshold

    if measure == "media":
        threshold = statistics.mean(clean_counts)
    elif measure == "moda":
        threshold = statistics.mode(clean_counts)
    elif measure == "mediana":
        threshold = statistics.median(clean_counts)
    else:
        raise ValueError(f"Medida desconhecida: {measure}")

    return {uid for uid, count in user_counts.items() if count > threshold}

def select_curtos(user_comments: dict[str, list[Comment]], threshold_chars: int) -> set[str]:
    suspicious = set()
    for uid, comments in user_comments.items():
        short = [c for c in comments if len(c.text_original.strip()) < threshold_chars]
        texts = [c.text_original.strip().lower() for c in comments]
        repetition_rate = 1 - len(set(texts)) / len(texts) if texts else 0
        if len(short) / len(comments) > 0.7 or repetition_rate > 0.5:
            suspicious.add(uid)
    return suspicious

def select_intervalo(user_comments: dict[str, list[Comment]], threshold_seconds: int) -> set[str]:
    suspicious = set()
    for uid, comments in user_comments.items():
        if len(comments) < 2:
            continue
        sorted_comments = sorted(comments, key=lambda c: c.published_at)
        for a, b in zip(sorted_comments, sorted_comments[1:]):
            delta = (b.published_at - a.published_at).total_seconds()
            if 0 <= delta < threshold_seconds:
                suspicious.add(uid)
                break
    return suspicious

def build_dataset_name(video_id: str, criteria: list[str]) -> str:
    order = ["percentil", "media", "moda", "mediana", "curtos", "intervalo", "identicos", "perfil"]
    active = [c for c in order if c in criteria]
    return f"{video_id}_{'_'.join(active)}"
```

---

## Frontend — componentes sugeridos

```
pages/Clean/
├── CleanPage.tsx              # seleção de coleta + dois grupos de critérios com checkboxes
├── CriteriaGroup1.tsx         # checkboxes: percentil, média, moda, mediana
├── CriteriaGroup2.tsx         # checkboxes + inputs de threshold: curtos, intervalo, idênticos, perfil
├── MeasuresPreview.tsx        # exibe média, moda, mediana calculadas antes de confirmar
├── PreviewPanel.tsx           # contagem de usuários por critério + interseção + nome gerado
├── DatasetList.tsx            # lista de datasets com botão download (CSV/JSON)
└── useClean.ts                # hook: preview(), createDataset(), listDatasets(), downloadDataset()
```

**UX obrigatória:**
- Exibir as três medidas centrais (média, moda, mediana) no preview antes de confirmar
- Nome do dataset gerado automaticamente e exibido em tempo real conforme critérios são marcados
- Campos de API key com `type="password"` — aparecem apenas se critério `perfil` for selecionado
- Botão "Criar Dataset" desabilitado se preview retornar 0 usuários selecionados

---

## Casos de erro

| Cenário                               | HTTP | Mensagem ao usuário                                   |
|---------------------------------------|------|-------------------------------------------------------|
| Nenhum critério selecionado           | 422  | "Selecione ao menos um critério."                     |
| Coleta não concluída                  | 409  | "A coleta ainda não foi finalizada."                  |
| Nenhum usuário selecionado            | 422  | "Os critérios não selecionaram nenhum usuário."       |
| Nome de dataset duplicado             | 409  | "Já existe um dataset com esses critérios."           |
| `perfil` sem `youtube_api_key`        | 422  | "API key do YouTube obrigatória para critério 'perfil'." |

---

## Testes obrigatórios (Pytest)

### Referência de dublês

| Dublê | Quando usar                                                                          |
|-------|--------------------------------------------------------------------------------------|
| Stub  | Simular retorno de APIs externas (YouTube, SocialBlade) e status de coleta           |
| Mock  | Verificar que API keys não são logadas ou persistidas pelo critério `perfil`         |
| Dummy | Dados de comentários irrelevantes para testar apenas a função de nomeação do dataset |
| Fake  | Banco SQLite em memória para testar persistência do dataset                          |

### Casos de teste

```python
# conftest.py
def make_comments(users: dict[str, int]) -> list[Comment]:
    """Factory de Dummy comments: gera N comentários por user_id para testar algoritmos."""
    comments = []
    for channel_id, count in users.items():
        for i in range(count):
            comments.append(Comment(
                author_channel_id=channel_id,
                author_display_name=f"User {channel_id}",
                text_original=f"comentário {i}",
                like_count=0,
                published_at=datetime(2024, 1, 1, 0, i, 0),
                updated_at=datetime(2024, 1, 1),
            ))
    return comments
```

**Critério `percentil`: seleciona top 30% por volume de comentários**
- Dummy: `make_comments({"A": 10, "B": 5, "C": 3, "B2": 1, ...})` com distribuição conhecida
- Sem dublê de banco (função pura)
- Afirma que apenas os usuários com volume no top 30% estão no resultado

**Critério `media` com remoção de outliers via IQR**
- Dummy: comentários com distribuição que inclui outlier extremo (ex: um usuário com 1000 comentários)
- Afirma que o outlier não distorce o threshold (média calculada sem ele)
- Afirma que o outlier ainda pode ser selecionado se estiver acima do threshold resultante

**Critério `curtos`: detecta comentários abaixo de N caracteres**
- Dummy: comentários com `text_original` de 5, 15, 50 caracteres para o mesmo usuário
- Sem dublê — função pura com `threshold_chars=20`
- Afirma que usuário com maioria abaixo de 20 chars é selecionado

**Critério `intervalo`: detecta postagens em rafada**
- Dummy: comentários com `published_at` espaçados por 5s (dentro do threshold de 30s)
- Afirma que o usuário é selecionado

**Critério `perfil`: consulta YouTube API e SocialBlade**
- Stub: `httpx.AsyncClient.get` retorna perfil sem avatar e canal recém-criado
  `mocker.patch("services.clean.httpx.AsyncClient.get", return_value=...)`
- Mock: `logger.info` — verifica que a API key não aparece em nenhum log
- Afirma que o usuário com perfil suspeito é selecionado

**Combinação de critérios gera dataset de interseção**
- Dummy: comentários onde apenas 2 usuários atendem **ambos** os critérios `percentil` e `intervalo`
- Afirma `len(selected_users) == 2`
- Afirma nome gerado = `{video_id}_percentil_intervalo` (ordem canônica)

**Nomeação de dataset segue convenção obrigatória**
- Dummy: lista de critérios em ordem embaralhada (`["intervalo", "percentil"]`)
- Sem dublê — função pura `build_dataset_name`
- Afirma resultado = `"{video_id}_percentil_intervalo"` (ordem canônica, não a da entrada)

**Dataset duplicado retorna 409**
- Fake: banco em memória com dataset pré-existente de mesmo nome
- Stub: `get_collection` retorna coleta com `status="completed"`
- Afirma HTTP 409

**Coleta não concluída retorna 409**
- Stub: `db.get(Collection, id)` retorna objeto com `status="running"`
- Dummy: critérios e thresholds (irrelevantes — a validação ocorre antes)
- Afirma HTTP 409

## Melhorias implementadas (pós-spec)

### Exclusão do autor do vídeo
O `video_channel_id` da coleta é excluído automaticamente da análise — o autor do vídeo
responde frequentemente, em rajada e com textos curtos, gerando falsos positivos em todos os critérios.

### Critério `perfil` sem API key
O critério `perfil` usa dados já coletados (`author_profile_image_url`, `author_channel_published_at`)
em vez de chamar a YouTube API — sem necessidade de API key adicional.

### União em vez de interseção
Múltiplos critérios selecionados geram **união** (qualquer critério atendido), não interseção.
Cada `DatasetEntry` registra em `matched_criteria` quais critérios específicos o usuário atendeu.

### Streaming no download
Exports CSV/JSON usam `yield_per(500)` + geradores streaming — sem carregar todos os comentários
na memória. Compatível com o limite de 60s do Vercel Pro.

### Import de dataset

**Endpoint:** `POST /clean/import`

Permite importar um dataset pré-curado. Aceita o **mesmo formato JSON** gerado pelo export
(`GET /clean/datasets/{id}/download?format=json`) — simetria total:

```json
{
  "dataset": {
    "name": "nome_do_dataset",
    "video_id": "dQw4w9WgXcQ",
    "criteria_applied": ["percentil", "intervalo"]
  },
  "users": [
    {
      "author_channel_id": "UCxxx",
      "author_display_name": "User",
      "comment_count": 5,
      "matched_criteria": ["percentil"]
    }
  ],
  "comments": []
}
```

- `video_id` resolve automaticamente para a coleta mais recente concluída desse vídeo
- `comments` é aceito mas ignorado (os comentários já estão na coleta)
- O nome do dataset deve ser único
- Se não existir coleta para o `video_id`, retorna 404 com instrução para importar a coleta primeiro

**Frontend:** aba "Importar JSON" na CleanPage, separada de "Criar via critérios" (padrão de tabs).

## Dependências com outras USs

- **US-02:** requer `collection_id` com `status = "completed"`
- **US-04 (Anotação):** recebe o `dataset_id` e acessa `dataset_entries` para listar os usuários a anotar
- **US-06 (Dashboard):** usa `total_users_original` vs `total_users_selected` para métricas de cobertura
