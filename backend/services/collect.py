import logging
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.collection import Collection, Comment
from schemas.collect import CollectNextPageRequest, CollectRequest, ImportRequest
from services.youtube import (
    fetch_channels_info,
    fetch_comments_page,
    fetch_replies_page,
    fetch_video_info,
)

logger = logging.getLogger(__name__)


def _safe_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _parse_youtube_error(exc: httpx.HTTPStatusError) -> HTTPException:
    http_status = exc.response.status_code
    try:
        body = exc.response.json()
        errors = body.get("error", {}).get("errors", [])
        reason = errors[0].get("reason", "") if errors else ""
        message = errors[0].get("message", "") if errors else ""
    except Exception:
        reason = ""
        message = ""
    logger.warning(
        "YouTube API %s reason=%s message=%s",
        http_status,
        reason,
        message,
    )

    if http_status == 400:
        if reason in ("keyInvalid", "keyExpired"):
            return HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="API key inválida ou sem permissão.",
            )
        return HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Requisição inválida. Verifique o ID do vídeo e a API key.",
        )
    if http_status == 403:
        if reason == "commentsDisabled":
            return HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Este vídeo não permite comentários.",
            )
        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            return HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quota da API esgotada. Tente novamente amanhã.",
            )
        if reason in ("forbidden", "videoNotFound"):
            return HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Este vídeo é privado ou não está disponível.",
            )
        return HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="API key inválida ou sem permissão.",
        )
    if http_status == 404:
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="Vídeo não encontrado.")
    return HTTPException(
        status.HTTP_502_BAD_GATEWAY,
        detail=f"Erro na API do YouTube (HTTP {http_status}). Tente novamente.",
    )


def _insert_single_comment(
    db: Session,
    collection_id: uuid.UUID,
    comment_id: str,
    snippet: dict,
    *,
    parent_id: str | None = None,
    total_reply_count: int = 0,
) -> bool:
    """Insere um comentário se não existir. Retorna True se inseriu."""
    exists = (
        db.query(Comment.id)
        .filter(
            Comment.collection_id == collection_id,
            Comment.comment_id == comment_id,
        )
        .first()
    )
    if exists:
        return False

    comment = Comment(
        collection_id=collection_id,
        comment_id=comment_id,
        parent_id=parent_id,
        author_display_name=snippet.get("authorDisplayName", ""),
        author_channel_id=(snippet.get("authorChannelId") or {}).get("value"),
        text_original=snippet.get("textOriginal", snippet.get("textDisplay", "")),
        text_display=snippet.get("textDisplay"),
        author_profile_image_url=snippet.get("authorProfileImageUrl"),
        author_channel_url=snippet.get("authorChannelUrl"),
        like_count=int(snippet.get("likeCount", 0)),
        reply_count=total_reply_count,
        published_at=datetime.fromisoformat(
            snippet["publishedAt"].replace("Z", "+00:00")
        ),
        updated_at=datetime.fromisoformat(snippet["updatedAt"].replace("Z", "+00:00")),
    )
    db.add(comment)
    return True


def _insert_comments(db: Session, collection_id: uuid.UUID, items: list[dict]) -> int:
    """Insere top-level comments + inline replies (até 5 por thread)."""
    inserted = 0
    for item in items:
        top = item["snippet"]["topLevelComment"]
        thread = item["snippet"]

        if _insert_single_comment(
            db,
            collection_id,
            top["id"],
            top["snippet"],
            total_reply_count=int(thread.get("totalReplyCount", 0)),
        ):
            inserted += 1

        # Inline replies (part=snippet,replies retorna até 5 por thread)
        for reply in item.get("replies", {}).get("comments", []):
            if _insert_single_comment(
                db,
                collection_id,
                reply["id"],
                reply["snippet"],
                parent_id=top["id"],
            ):
                inserted += 1

    db.commit()
    return inserted


async def _fetch_remaining_replies(
    db: Session,
    collection_id: uuid.UUID,
    parent_comment_id: str,
    api_key: str,
) -> int:
    """Busca replies restantes (>5) de um thread via comments.list paginado."""
    inserted = 0
    page_token: str | None = None
    while True:
        data = await fetch_replies_page(parent_comment_id, api_key, page_token)
        for reply in data.get("items", []):
            if _insert_single_comment(
                db,
                collection_id,
                reply["id"],
                reply["snippet"],
                parent_id=parent_comment_id,
            ):
                inserted += 1
        db.commit()
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return inserted


def _extract_new_channel_ids(
    db: Session, collection_id: uuid.UUID, items: list[dict]
) -> list[str]:
    """
    Retorna IDs de canais dos autores (top-level + replies) desta página
    que ainda não têm author_channel_published_at resolvido nesta coleta.
    """
    page_ids: set[str] = set()
    for item in items:
        # Top-level author
        top_cid = (
            item["snippet"]["topLevelComment"]["snippet"].get("authorChannelId") or {}
        ).get("value")
        if top_cid:
            page_ids.add(top_cid)
        # Reply authors
        for reply in item.get("replies", {}).get("comments", []):
            reply_cid = (reply.get("snippet", {}).get("authorChannelId") or {}).get(
                "value"
            )
            if reply_cid:
                page_ids.add(reply_cid)

    if not page_ids:
        return []

    already_resolved = {
        row[0]
        for row in db.query(Comment.author_channel_id)
        .filter(
            Comment.collection_id == collection_id,
            Comment.author_channel_id.in_(page_ids),
            Comment.author_channel_published_at.isnot(None),
        )
        .all()
        if row[0]
    }

    return list(page_ids - already_resolved)


async def _enrich_channel_dates(
    db: Session,
    collection_id: uuid.UUID,
    channel_ids: list[str],
    api_key: str,
) -> bool:
    """
    Busca a data de criação de cada canal e atualiza os comentários.
    Falhas são registradas em log mas não abortam a coleta.
    Retorna True se sucesso, False se falhou.
    """
    if not channel_ids:
        return True
    try:
        channel_dates = await fetch_channels_info(channel_ids, api_key)
        for channel_id, published_at in channel_dates.items():
            db.query(Comment).filter(
                Comment.collection_id == collection_id,
                Comment.author_channel_id == channel_id,
            ).update({"author_channel_published_at": published_at})
        db.commit()
        return True
    except Exception:
        logger.exception(
            "Falha ao buscar datas de criação de canais para coleta %s "
            "(%d canais solicitados)",
            collection_id,
            len(channel_ids),
        )
        return False


async def start_collection(
    db: Session,
    payload: CollectRequest,
    user_id: uuid.UUID,
) -> tuple[Collection, str | None]:
    collection = Collection(
        video_id=payload.video_id,
        status="running",
        collected_by=user_id,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    try:
        api_key = payload.api_key.get_secret_value()

        # Metadados do vídeo (videos.list — 1 quota unit)
        video_info = await fetch_video_info(payload.video_id, api_key)
        if video_info:
            vs = video_info.get("snippet", {})
            st = video_info.get("statistics", {})
            pub = vs.get("publishedAt")
            collection.video_title = vs.get("title")
            collection.video_description = vs.get("description")
            collection.video_channel_id = vs.get("channelId")
            collection.video_channel_title = vs.get("channelTitle")
            collection.video_published_at = (
                datetime.fromisoformat(pub.replace("Z", "+00:00")) if pub else None
            )
            collection.video_view_count = _safe_int(st.get("viewCount"))
            collection.video_like_count = _safe_int(st.get("likeCount"))
            collection.video_comment_count = _safe_int(st.get("commentCount"))
            db.commit()
            db.refresh(collection)

        data = await fetch_comments_page(payload.video_id, api_key, max_results=100)
        items = data.get("items", [])
        next_page_token: str | None = data.get("nextPageToken")

        _insert_comments(db, collection.id, items)

        # Replies extras (threads com >5 replies → comments.list paginado)
        for item in items:
            total_replies = int(item["snippet"].get("totalReplyCount", 0))
            inline_count = len(item.get("replies", {}).get("comments", []))
            if total_replies > inline_count:
                parent_id = item["snippet"]["topLevelComment"]["id"]
                await _fetch_remaining_replies(db, collection.id, parent_id, api_key)

        # Datas de criação dos canais dos autores (channels.list — batches de 50)
        new_channel_ids = _extract_new_channel_ids(db, collection.id, items)
        success = await _enrich_channel_dates(
            db, collection.id, new_channel_ids, api_key
        )
        if not success:
            collection.channel_dates_failed = True
        elif collection.channel_dates_failed is None:
            collection.channel_dates_failed = False

        total = db.query(Comment).filter(Comment.collection_id == collection.id).count()

        if not next_page_token:
            collection.status = "completed"
            collection.total_comments = total
            collection.completed_at = datetime.now(UTC)
            collection.next_page_token = None
        else:
            collection.total_comments = total
            collection.next_page_token = next_page_token

        db.commit()
        db.refresh(collection)
        return collection, next_page_token
    except httpx.HTTPStatusError as exc:
        logger.exception(
            "YouTube API erro HTTP %s para video_id=%s",
            exc.response.status_code,
            payload.video_id,
        )
        collection.status = "failed"
        collection.error_message = str(exc)[:500]
        db.commit()
        raise _parse_youtube_error(exc) from exc
    except Exception as exc:
        logger.exception(
            "Erro inesperado na coleta do video_id=%s",
            payload.video_id,
        )
        collection.status = "failed"
        collection.error_message = str(exc)[:500]
        db.commit()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao coletar comentários: {type(exc).__name__}: {exc}",
        ) from exc


async def collect_next_page(
    db: Session,
    payload: CollectNextPageRequest,
    user_id: uuid.UUID,
) -> tuple[Collection, str | None]:
    collection = (
        db.query(Collection)
        .filter(
            Collection.id == payload.collection_id,
            Collection.collected_by == user_id,
        )
        .first()
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Coleta não encontrada.")
    if collection.status == "completed":
        return collection, None
    if collection.status == "failed":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Coleta falhou e não pode continuar.",
        )
    if not collection.next_page_token:
        collection.status = "completed"
        collection.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(collection)
        return collection, None

    try:
        api_key = payload.api_key.get_secret_value()

        data = await fetch_comments_page(
            collection.video_id,
            api_key,
            page_token=collection.next_page_token,
        )

        items = data.get("items", [])
        next_page_token: str | None = data.get("nextPageToken")

        _insert_comments(db, collection.id, items)

        # Replies extras (threads com >5 replies)
        for item in items:
            total_replies = int(item["snippet"].get("totalReplyCount", 0))
            inline_count = len(item.get("replies", {}).get("comments", []))
            if total_replies > inline_count:
                parent_id = item["snippet"]["topLevelComment"]["id"]
                await _fetch_remaining_replies(db, collection.id, parent_id, api_key)

        # Datas de criação apenas para autores não resolvidos ainda
        new_channel_ids = _extract_new_channel_ids(db, collection.id, items)
        success = await _enrich_channel_dates(
            db, collection.id, new_channel_ids, api_key
        )
        if not success:
            collection.channel_dates_failed = True

        total = db.query(Comment).filter(Comment.collection_id == collection.id).count()
        collection.total_comments = total

        if not next_page_token:
            collection.status = "completed"
            collection.completed_at = datetime.now(UTC)
            collection.next_page_token = None
        else:
            collection.next_page_token = next_page_token

        db.commit()
        db.refresh(collection)
        return collection, next_page_token
    except httpx.HTTPStatusError as exc:
        logger.exception(
            "YouTube API erro HTTP %s na next-page collection_id=%s",
            exc.response.status_code,
            payload.collection_id,
        )
        collection.status = "failed"
        collection.error_message = str(exc)[:500]
        db.commit()
        raise _parse_youtube_error(exc) from exc
    except Exception as exc:
        logger.exception(
            "Erro inesperado em next-page collection_id=%s",
            payload.collection_id,
        )
        collection.status = "failed"
        collection.error_message = str(exc)[:500]
        db.commit()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao continuar coleta: {type(exc).__name__}: {exc}",
        ) from exc


def get_collection_status(
    db: Session, collection_id: uuid.UUID, user_id: uuid.UUID
) -> Collection:
    collection = (
        db.query(Collection)
        .filter(
            Collection.id == collection_id,
            Collection.collected_by == user_id,
        )
        .first()
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Coleta não encontrada.")
    return collection


def list_collections(db: Session, user_id: uuid.UUID) -> list[Collection]:
    return (
        db.query(Collection)
        .filter(Collection.collected_by == user_id)
        .order_by(Collection.created_at.desc())
        .all()
    )


def import_collection(
    db: Session, payload: ImportRequest, user_id: uuid.UUID
) -> Collection:
    v = payload.video
    collection = Collection(
        video_id=v.id,
        status="completed",
        collected_by=user_id,
        completed_at=datetime.now(UTC),
        video_title=v.title,
        video_channel_id=v.channel_id,
        video_channel_title=v.channel_title,
        video_published_at=v.published_at,
        video_view_count=v.view_count,
        video_like_count=v.like_count,
        video_comment_count=v.comment_count,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    for c in payload.comments:
        comment = Comment(
            collection_id=collection.id,
            comment_id=c.comment_id,
            parent_id=c.parent_id,
            author_display_name=c.author_display_name,
            author_channel_id=c.author_channel_id,
            author_channel_published_at=c.author_channel_published_at,
            author_profile_image_url=c.author_profile_image_url,
            author_channel_url=c.author_channel_url,
            text_original=c.text_original,
            text_display=c.text_display,
            like_count=c.like_count,
            reply_count=c.reply_count,
            published_at=c.published_at,
            updated_at=c.updated_at,
        )
        db.add(comment)

    db.commit()
    collection.total_comments = len(payload.comments)
    db.commit()
    db.refresh(collection)
    return collection


def delete_collection(
    db: Session, collection_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    collection = (
        db.query(Collection)
        .filter(
            Collection.id == collection_id,
            Collection.collected_by == user_id,
        )
        .first()
    )
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Coleta não encontrada.")
    if collection.status == "running":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Não é possível deletar uma coleta em andamento.",
        )
    db.query(Comment).filter(Comment.collection_id == collection_id).delete(
        synchronize_session=False
    )
    db.delete(collection)
    db.commit()


def export_comments(db: Session, collection_id: uuid.UUID) -> list[Comment]:
    return (
        db.query(Comment)
        .filter(Comment.collection_id == collection_id)
        .order_by(Comment.published_at)
        .all()
    )
