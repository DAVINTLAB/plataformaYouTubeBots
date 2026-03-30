"""Serviço de seed — gera dados mockados para teste local."""

import logging
import random
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry
from models.user import User
from services.auth import get_password_hash

logger = logging.getLogger(__name__)

SEED_VIDEO_ID = "mockSeedV1"

# ─── Dados mockados ─────────────────────────────────────────────────────────

_SPAM = [
    "Confira meu canal! Link na bio!!! 🔥🔥🔥",
    "Ganhe dinheiro fácil clicando aqui: bit.ly/easy-money",
    "Visite meu perfil para conteúdo EXCLUSIVO!!!",
    "👉👉👉 Inscreva-se no meu canal AGORA 👈👈👈",
    "Quer ganhar um iPhone? Acesse meu canal!",
    "Se inscreve no meu canal que inscrevo no seu!!!",
    "Melhor site de apostas: bit.ly/bet-win-2024",
    "PROMOÇÃO! Acesse o link na minha bio!",
    "Clique no meu perfil — conteúdo grátis todos os dias!",
    "🚀 Meu canal vai te ensinar a ficar rico! 🚀",
]

_COPY = [
    "Primeiro! Like se você também chegou cedo!",
    "Quem tá assistindo em 2024? Deixa o like!",
    "Esse vídeo merece 1 milhão de likes!",
    "Alguém mais veio pelo TikTok?",
    "Ninguém: ... Absolutamente ninguém: ... Eu: assistindo",
]

_ENGAGE = [
    "Que vídeo INCRÍVEL!! Amei DEMAIS!! 😍😍😍",
    "Melhor canal do YouTube INTEIRO!! Recomendo!!",
    "Parabéns pelo conteúdo!! MARAVILHOSO!! 👏👏👏",
    "Simplesmente PERFEITO!! Nota 10!! ⭐⭐⭐⭐⭐",
    "Assisti 3 vezes!! Cada vez melhor!! SENSACIONAL!!",
    "MELHOR vídeo que já vi na VIDA!! Sério mesmo!!",
]

_BURST = [
    "kkkkkk muito bom",
    "kkk real",
    "verdade kkk",
    "sim sim concordo",
    "exatamente isso",
    "boa boa",
    "top top top",
]

_HUMAN = [
    "Muito bom o vídeo, explicou bem o conceito de detecção de bots.",
    "Discordo do ponto sobre falsos positivos. A taxa é menor com features de perfil.",
    "Poderia indicar algum artigo sobre o tema? Estudo NLP aplicado a redes sociais.",
    "Excelente conteúdo! Compartilhei com meu grupo de pesquisa.",
    "Sugiro incluir análise de sentimento como feature adicional.",
    "Como vocês lidam com bots que usam variações de texto?",
    "Trabalho com moderação há 5 anos. Intervalo temporal é mais eficaz.",
    "Obrigado pela resposta! Vou conferir o paper indicado.",
    "Interessante a abordagem de união de critérios.",
    "O percentil sozinho gera falsos positivos com power users legítimos.",
    "Ótima explicação sobre a API do YouTube. A documentação oficial é confusa.",
    "Já testaram com vídeos de música? O padrão de bots é diferente.",
    "As features de perfil (data de criação do canal) são muito discriminativas.",
    "Parabéns! Estou usando a mesma abordagem no meu projeto de IC.",
    "A parte sobre canais recentes é crucial. Bots usam contas descartáveis.",
    "Qual o tamanho mínimo de dataset recomendado?",
    "Seria possível adaptar para comentários do Instagram?",
    "Uma feature útil seria exportar em formato compatível com scikit-learn.",
    "O critério de comentários curtos precisa de cuidado em vídeos de humor.",
    "Gostei da ferramenta! Vou usar na minha dissertação.",
]

BOTS = [
    ("UCbot_spam01", "SpamMaster3000", "spam"),
    ("UCbot_spam02", "PromoBot_BR", "spam"),
    ("UCbot_spam03", "LinkDrop99", "spam"),
    ("UCbot_spam04", "CopyPasteKing", "copy"),
    ("UCbot_spam05", "FakeEngager", "engage"),
    ("UCbot_spam06", "SubForSub_YT", "spam"),
    ("UCbot_spam07", "ClickBaitQueen", "spam"),
    ("UCbot_spam08", "ViewBot2024", "engage"),
    ("UCbot_spam09", "AutoComment_X", "spam"),
    ("UCbot_copy01", "EchoBot_Alpha", "copy"),
    ("UCbot_copy02", "MirrorText_99", "copy"),
    ("UCbot_copy03", "RepeatAfterMe", "copy"),
    ("UCbot_engag01", "LikeHunter_BR", "engage"),
    ("UCbot_engag02", "EngageFarm", "engage"),
    ("UCbot_engag03", "ReactionBot_X", "engage"),
    ("UCbot_burst01", "RapidFire_YT", "burst"),
    ("UCbot_burst02", "FloodComment", "burst"),
    ("UCbot_burst03", "BurstPoster99", "burst"),
]

HUMANS = [
    ("UChum_maria", "Maria Silva"),
    ("UChum_joao", "João Santos"),
    ("UChum_ana", "Ana Oliveira"),
    ("UChum_pedro", "Pedro Costa"),
    ("UChum_lucia", "Lúcia Fernandes"),
    ("UChum_carlos", "Carlos Mendes"),
    ("UChum_julia", "Júlia Rocha"),
    ("UChum_rafael", "Rafael Almeida"),
    ("UChum_camila", "Camila Souza"),
    ("UChum_bruno", "Bruno Lima"),
    ("UChum_leticia", "Letícia Martins"),
    ("UChum_diego", "Diego Araújo"),
]


def _bot_texts(kind: str) -> list[str]:
    return {"spam": _SPAM, "copy": _COPY, "engage": _ENGAGE, "burst": _BURST}[kind]


def _bot_criteria(kind: str) -> list[str]:
    return {
        "spam": ["percentil", "intervalo", "perfil"],
        "copy": ["identicos", "intervalo"],
        "engage": ["curtos", "percentil"],
        "burst": ["intervalo", "curtos"],
    }[kind]


# ─── Deletar seed ───────────────────────────────────────────────────────────


def delete_seed(db: Session) -> dict:
    """Remove todos os dados criados pelo seed (coleta, dataset, anotações)."""
    collection = (
        db.query(Collection).filter(Collection.video_id == SEED_VIDEO_ID).first()
    )
    if not collection:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Nenhum dado mockado encontrado.",
        )

    # Deletar anotações e conflitos dos comentários desta coleta
    comment_ids = (
        db.query(Comment.id).filter(Comment.collection_id == collection.id).subquery()
    )

    db.query(AnnotationConflict).filter(
        AnnotationConflict.comment_id.in_(comment_ids)
    ).delete(synchronize_session=False)

    db.query(Annotation).filter(Annotation.comment_id.in_(comment_ids)).delete(
        synchronize_session=False
    )

    # Deletar datasets e entries
    datasets = db.query(Dataset).filter(Dataset.collection_id == collection.id).all()
    for ds in datasets:
        db.query(DatasetEntry).filter(DatasetEntry.dataset_id == ds.id).delete(
            synchronize_session=False
        )
        db.delete(ds)

    # Deletar comentários e coleta
    db.query(Comment).filter(Comment.collection_id == collection.id).delete(
        synchronize_session=False
    )
    db.delete(collection)

    db.commit()
    logger.info("Seed deletado: video_id=%s", SEED_VIDEO_ID)

    return {"message": "Dados mockados deletados com sucesso."}


# ─── Lógica de seed ─────────────────────────────────────────────────────────


def run_seed(db: Session) -> dict:
    """Cria coleta mockada + dataset com bots para teste de anotação."""
    random.seed(42)

    existing = (
        db.query(Collection)
        .filter(
            Collection.video_id == SEED_VIDEO_ID,
            Collection.status == "completed",
        )
        .first()
    )
    if existing:
        ds = db.query(Dataset).filter(Dataset.collection_id == existing.id).first()
        if ds:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Seed já foi executado. Dados mockados já existem.",
            )

    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nenhum usuário admin encontrado.",
        )

    # ─── Coleta ──────────────────────────────────────────────────────────
    col = Collection(
        video_id=SEED_VIDEO_ID,
        status="completed",
        total_comments=0,
        collected_by=admin.id,
        completed_at=datetime.utcnow(),
        enrich_status="done",
        video_title="Detectando Bots no YouTube — Metodologia DaVint",
        video_channel_id="UC_davintlab",
        video_channel_title="DaVint Lab PUCRS",
        video_published_at=datetime(2024, 1, 10),
        video_view_count=45_000,
        video_like_count=1_200,
        video_comment_count=150,
    )
    db.add(col)
    db.flush()

    base = datetime(2024, 1, 15, 8, 0, 0)
    total = 0

    # ─── Comentários de bots ─────────────────────────────────────────────
    for i, (cid, name, kind) in enumerate(BOTS):
        texts = _bot_texts(kind)
        n = random.randint(4, 8)
        for j in range(n):
            t = texts[0] if kind == "copy" else texts[j % len(texts)]
            pub = base + timedelta(hours=i * 3, minutes=j * random.randint(2, 5))
            db.add(
                Comment(
                    collection_id=col.id,
                    comment_id=f"{cid}_c{j}",
                    parent_id=None,
                    author_channel_id=cid,
                    author_display_name=name,
                    text_original=t,
                    text_display=t,
                    like_count=0,
                    reply_count=0,
                    published_at=pub,
                    updated_at=pub,
                    author_profile_image_url="https://yt3.ggpht.com/default",
                    author_channel_url=f"https://youtube.com/channel/{cid}",
                    author_channel_published_at=datetime(
                        2024, 1, random.randint(1, 14)
                    ),
                )
            )
            total += 1

    # ─── Comentários de humanos ──────────────────────────────────────────
    for cid, name in HUMANS:
        n = random.randint(2, 4)
        for j in range(n):
            pub = base + timedelta(
                days=random.randint(0, 10),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            db.add(
                Comment(
                    collection_id=col.id,
                    comment_id=f"{cid}_c{j}",
                    parent_id=None,
                    author_channel_id=cid,
                    author_display_name=name,
                    text_original=_HUMAN[j % len(_HUMAN)],
                    text_display=_HUMAN[j % len(_HUMAN)],
                    like_count=random.randint(1, 30),
                    reply_count=random.randint(0, 5),
                    published_at=pub,
                    updated_at=pub,
                    author_profile_image_url=f"https://yt3.ggpht.com/{cid}",
                    author_channel_url=f"https://youtube.com/channel/{cid}",
                    author_channel_published_at=datetime(
                        random.randint(2015, 2019),
                        random.randint(1, 12),
                        random.randint(1, 28),
                    ),
                )
            )
            total += 1

    col.total_comments = total
    db.flush()

    # ─── Dataset ─────────────────────────────────────────────────────────
    ds = Dataset(
        name=f"{SEED_VIDEO_ID}_percentil_intervalo_perfil",
        collection_id=col.id,
        criteria_applied=["percentil", "intervalo", "perfil"],
        thresholds={"threshold_chars": 20, "threshold_seconds": 30},
        total_users_original=len(BOTS) + len(HUMANS),
        total_users_selected=len(BOTS),
        created_by=admin.id,
    )
    db.add(ds)
    db.flush()

    for cid, name, kind in BOTS:
        cnt = (
            db.query(Comment)
            .filter(
                Comment.collection_id == col.id,
                Comment.author_channel_id == cid,
            )
            .count()
        )
        db.add(
            DatasetEntry(
                dataset_id=ds.id,
                author_channel_id=cid,
                author_display_name=name,
                comment_count=cnt,
                matched_criteria=_bot_criteria(kind),
            )
        )

    db.flush()

    # ─── Garantir segundo pesquisador ────────────────────────────────────
    user_a = (
        db.query(User).filter(User.role == "user", User.is_active.is_(True)).first()
    )
    if not user_a:
        user_a = User(
            username="pesquisador1",
            name="Pesquisador Um",
            hashed_password=get_password_hash("pesq1234!"),
            role="user",
        )
        db.add(user_a)
        db.flush()

    user_b = (
        db.query(User)
        .filter(User.role == "user", User.is_active.is_(True), User.id != user_a.id)
        .first()
    )
    if not user_b:
        user_b = User(
            username="pesquisador2",
            name="Pesquisador Dois",
            hashed_password=get_password_hash("pesq5678!"),
            role="user",
        )
        db.add(user_b)
        db.flush()

    # ─── Anotações pré-existentes ────────────────────────────────────────
    # Pegar todos os comentários dos bots no dataset
    bot_channel_ids = [cid for cid, _, _ in BOTS]
    all_bot_comments = (
        db.query(Comment)
        .filter(
            Comment.collection_id == col.id,
            Comment.author_channel_id.in_(bot_channel_ids),
        )
        .order_by(Comment.published_at)
        .all()
    )

    annotations_created = 0
    conflicts_created = 0

    for idx, comment in enumerate(all_bot_comments):
        # Primeiros 40%: ambos concordam → bot (sem conflito)
        # Próximos 20%: ambos concordam → humano (sem conflito)
        # Próximos 20%: divergem → conflito (A=bot, B=humano)
        # Últimos 20%: sem anotação (pendentes)
        ratio = idx / len(all_bot_comments)

        if ratio < 0.4:
            # Concordância: ambos dizem bot
            ann_a = Annotation(
                comment_id=comment.id,
                annotator_id=user_a.id,
                label="bot",
                justificativa="Texto de spam/promoção.",
            )
            ann_b = Annotation(
                comment_id=comment.id,
                annotator_id=user_b.id,
                label="bot",
                justificativa="Comentário promocional repetido.",
            )
            db.add(ann_a)
            db.add(ann_b)
            annotations_created += 2

        elif ratio < 0.6:
            # Concordância: ambos dizem humano
            ann_a = Annotation(
                comment_id=comment.id,
                annotator_id=user_a.id,
                label="humano",
            )
            ann_b = Annotation(
                comment_id=comment.id,
                annotator_id=user_b.id,
                label="humano",
            )
            db.add(ann_a)
            db.add(ann_b)
            annotations_created += 2

        elif ratio < 0.8:
            # Divergência → conflito
            ann_a = Annotation(
                comment_id=comment.id,
                annotator_id=user_a.id,
                label="bot",
                justificativa="Padrão de engajamento falso.",
            )
            db.add(ann_a)
            db.flush()

            ann_b = Annotation(
                comment_id=comment.id,
                annotator_id=user_b.id,
                label="humano",
            )
            db.add(ann_b)
            db.flush()

            conflict = AnnotationConflict(
                comment_id=comment.id,
                annotation_a_id=ann_a.id,
                annotation_b_id=ann_b.id,
                status="pending",
            )
            db.add(conflict)
            annotations_created += 2
            conflicts_created += 1

        # ratio >= 0.8: sem anotação (pendente para o pesquisador testar)

    db.commit()

    logger.info(
        "Seed executado: %d comentários, %d bots, %d anotações, %d conflitos",
        total,
        len(BOTS),
        annotations_created,
        conflicts_created,
    )

    return {
        "message": "Seed executado com sucesso!",
        "collection_id": str(col.id),
        "dataset_id": str(ds.id),
        "total_comments": total,
        "total_bots": len(BOTS),
        "total_humans": len(HUMANS),
        "annotations_created": annotations_created,
        "conflicts_created": conflicts_created,
        "annotators": [
            f"{user_a.name} ({user_a.username})",
            f"{user_b.name} ({user_b.username})",
        ],
    }
