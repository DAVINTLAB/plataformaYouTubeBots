"""Orquestrador da US-03 — compõe seletores (DIP) e persiste datasets."""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry

from .identical import IdenticalSelector
from .mean import MeanSelector
from .median import MedianSelector
from .mode import ModeSelector
from .percentile import PercentileSelector
from .profile import ProfileSelector
from .short_comments import ShortCommentsSelector
from .stats import compute_central_measures
from .time_interval import TimeIntervalSelector

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def group_by_user(
    comments: list[Comment],
    exclude_channel_id: str | None = None,
) -> dict[str, list[Comment]]:
    """Agrupa comentários por author_channel_id.

    Exclui o autor do vídeo (video_channel_id) da análise —
    ele responde frequentemente, em rajada e com textos curtos,
    gerando falsos positivos em todos os critérios.
    """
    groups: dict[str, list[Comment]] = {}
    for c in comments:
        key = c.author_channel_id or c.author_display_name
        if key == exclude_channel_id:
            continue
        groups.setdefault(key, []).append(c)
    return groups


def build_dataset_name(video_id: str, criteria: list[str]) -> str:
    """Gera nome canônico: {video_id}_{critérios em ordem fixa}."""
    order = [
        "percentil",
        "media",
        "moda",
        "mediana",
        "curtos",
        "intervalo",
        "identicos",
        "perfil",
    ]
    active = [c for c in order if c in criteria]
    return f"{video_id}_{'_'.join(active)}"


def _get_completed_collection(db: Session, collection_id: uuid.UUID) -> Collection:
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Coleta não encontrada.")
    if collection.status != "completed":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="A coleta ainda não foi finalizada.",
        )
    return collection


def _build_selector(
    criteria_name: str,
    *,
    threshold_chars: int,
    threshold_seconds: int,
    db: Session | None = None,
    collection_id: uuid.UUID | None = None,
):
    """Factory: retorna o seletor adequado para cada critério (OCP)."""
    match criteria_name:
        case "percentil":
            return PercentileSelector()
        case "media":
            return MeanSelector()
        case "moda":
            return ModeSelector()
        case "mediana":
            return MedianSelector()
        case "curtos":
            return ShortCommentsSelector(threshold_chars=threshold_chars)
        case "intervalo":
            return TimeIntervalSelector(threshold_seconds=threshold_seconds)
        case "identicos":
            return IdenticalSelector(db=db, collection_id=str(collection_id))
        case "perfil":
            return ProfileSelector()
        case _:
            raise ValueError(f"Critério desconhecido: {criteria_name}")


# ─── Preview ─────────────────────────────────────────────────────────────────


def preview(
    db: Session,
    collection_id: uuid.UUID,
    criteria: list[str],
    threshold_chars: int = 20,
    threshold_seconds: int = 30,
) -> dict:
    collection = _get_completed_collection(db, collection_id)
    comments = db.query(Comment).filter(Comment.collection_id == collection.id).all()
    user_comments = group_by_user(
        comments, exclude_channel_id=collection.video_channel_id
    )
    user_counts = {uid: len(cs) for uid, cs in user_comments.items()}

    central = compute_central_measures(user_counts)

    by_criteria: dict[str, dict] = {}
    all_sets: list[set[str]] = []

    for name in criteria:
        selector = _build_selector(
            name,
            threshold_chars=threshold_chars,
            threshold_seconds=threshold_seconds,
            db=db,
            collection_id=collection_id,
        )
        selected = selector.select(user_comments)

        entry: dict = {"selected_users": len(selected)}
        if name == "curtos":
            entry["threshold_chars"] = threshold_chars
        if name == "intervalo":
            entry["threshold_seconds"] = threshold_seconds

        by_criteria[name] = entry
        all_sets.append(selected)

    union = set.union(*all_sets) if all_sets else set()

    return {
        "collection_id": collection_id,
        "total_users": len(user_comments),
        "central_measures": central,
        "by_criteria": by_criteria,
        "union_if_combined": len(union),
    }


# ─── Criação de Dataset ─────────────────────────────────────────────────────


def create_dataset(
    db: Session,
    collection_id: uuid.UUID,
    criteria: list[str],
    threshold_chars: int,
    threshold_seconds: int,
    user_id: uuid.UUID,
) -> Dataset:
    collection = _get_completed_collection(db, collection_id)

    dataset_name = build_dataset_name(collection.video_id, criteria)

    existing = db.query(Dataset).filter(Dataset.name == dataset_name).first()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Já existe um dataset com esses critérios para este vídeo.",
        )

    comments = db.query(Comment).filter(Comment.collection_id == collection.id).all()
    user_comments = group_by_user(
        comments, exclude_channel_id=collection.video_channel_id
    )

    # Executar cada seletor e rastrear quais critérios cada usuário atende
    user_matched: dict[str, list[str]] = {}
    all_sets: list[set[str]] = []

    for name in criteria:
        selector = _build_selector(
            name,
            threshold_chars=threshold_chars,
            threshold_seconds=threshold_seconds,
            db=db,
            collection_id=collection_id,
        )
        selected = selector.select(user_comments)

        all_sets.append(selected)
        for uid in selected:
            user_matched.setdefault(uid, []).append(name)

    # União: usuários que atendem QUALQUER critério
    union = set.union(*all_sets) if all_sets else set()

    if not union:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Os critérios não selecionaram nenhum usuário.",
        )

    thresholds = {
        "threshold_chars": threshold_chars,
        "threshold_seconds": threshold_seconds,
    }

    dataset = Dataset(
        name=dataset_name,
        collection_id=collection.id,
        criteria_applied=criteria,
        thresholds=thresholds,
        total_users_original=len(user_comments),
        total_users_selected=len(union),
        created_by=user_id,
    )
    db.add(dataset)
    db.flush()

    entries = [
        DatasetEntry(
            dataset_id=dataset.id,
            author_channel_id=uid,
            author_display_name=_get_display_name(user_comments, uid),
            comment_count=len(user_comments.get(uid, [])),
            matched_criteria=user_matched.get(uid, []),
        )
        for uid in union
    ]
    db.add_all(entries)
    db.commit()
    db.refresh(dataset)

    logger.info(
        "Dataset criado: name=%s, collection_id=%s, selected=%d/%d",
        dataset.name,
        collection_id,
        len(union),
        len(user_comments),
    )
    return dataset


def _get_display_name(user_comments: dict[str, list[Comment]], uid: str) -> str:
    comments = user_comments.get(uid, [])
    return comments[0].author_display_name if comments else uid


# ─── Import de dataset ───────────────────────────────────────────────────────


def import_dataset(
    db: Session,
    video_id: str,
    name: str,
    criteria_applied: list[str],
    users: list,
    user_id: uuid.UUID,
) -> Dataset:
    """Importa um dataset pré-curado com usuários já selecionados.

    Encontra a coleta pelo video_id — a coleta deve existir e estar concluída.
    """
    collection = (
        db.query(Collection)
        .filter(
            Collection.video_id == video_id,
            Collection.status == "completed",
        )
        .order_by(Collection.created_at.desc())
        .first()
    )
    if collection is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma coleta concluída encontrada para o vídeo '{video_id}'. "
            "Importe a coleta primeiro na Etapa 1.",
        )

    existing = db.query(Dataset).filter(Dataset.name == name).first()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Já existe um dataset com esse nome.",
        )

    # Contar usuários únicos na coleta para total_users_original
    total_original = (
        db.query(Comment.author_channel_id)
        .filter(
            Comment.collection_id == collection.id,
            Comment.author_channel_id.isnot(None),
        )
        .distinct()
        .count()
    )

    dataset = Dataset(
        name=name,
        collection_id=collection.id,
        criteria_applied=criteria_applied,
        thresholds={},
        total_users_original=total_original,
        total_users_selected=len(users),
        created_by=user_id,
    )
    db.add(dataset)
    db.flush()

    entries = [
        DatasetEntry(
            dataset_id=dataset.id,
            author_channel_id=u.author_channel_id,
            author_display_name=u.author_display_name,
            comment_count=u.comment_count,
            matched_criteria=u.matched_criteria,
        )
        for u in users
    ]
    db.add_all(entries)
    db.commit()
    db.refresh(dataset)

    logger.info(
        "Dataset importado: name=%s, video_id=%s, users=%d",
        dataset.name,
        video_id,
        len(users),
    )
    return dataset


# ─── Listagem e download ────────────────────────────────────────────────────


def list_datasets(db: Session, video_id: str | None = None) -> list[Dataset]:
    query = db.query(Dataset)
    if video_id:
        query = query.join(Collection).filter(Collection.video_id == video_id)
    return query.order_by(Dataset.created_at.desc()).all()


def get_dataset_with_entries(db: Session, dataset_id: uuid.UUID) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset não encontrado.")
    return dataset


def delete_dataset(db: Session, dataset_id: uuid.UUID) -> None:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset não encontrado.")
    db.delete(dataset)
    db.commit()
