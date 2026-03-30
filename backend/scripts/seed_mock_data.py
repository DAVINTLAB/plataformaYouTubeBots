"""
Seed de dados mockados para teste local da US-04 (Anotação).

Cria:
  - 1 coleta com 150 comentários de 30 usuários do YouTube
  - 1 dataset com 18 usuários selecionados como suspeitos
  - Comentários variados: bots com spam/links/cópias, humanos com textos legítimos
  - Bots com canais recentes (2024), humanos com canais antigos (2015–2019)
  - Bots postam em rajada (intervalos de 2–5min), humanos em dias diferentes

Uso:
  cd backend && source .venv/Scripts/activate
  DATABASE_URL=...davint python scripts/seed_mock_data.py
"""

import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal  # noqa: E402
from models.collection import Collection, Comment  # noqa: E402
from models.dataset import Dataset, DatasetEntry  # noqa: E402
from models.user import User  # noqa: E402

# ─── Seed determinístico ─────────────────────────────────────────────────────

random.seed(42)

VIDEO_ID = "mockSeedV1"

# ─── 30 usuários do YouTube ─────────────────────────────────────────────────

YOUTUBE_USERS = [
    # 18 bots (selecionados para o dataset)
    ("UCbot_spam01", "SpamMaster3000"),
    ("UCbot_spam02", "PromoBot_BR"),
    ("UCbot_spam03", "LinkDrop99"),
    ("UCbot_spam04", "CopyPasteKing"),
    ("UCbot_spam05", "FakeEngager"),
    ("UCbot_spam06", "SubForSub_YT"),
    ("UCbot_spam07", "ClickBaitQueen"),
    ("UCbot_spam08", "ViewBot2024"),
    ("UCbot_spam09", "AutoComment_X"),
    ("UCbot_copy01", "EchoBot_Alpha"),
    ("UCbot_copy02", "MirrorText_99"),
    ("UCbot_copy03", "RepeatAfterMe"),
    ("UCbot_engag01", "LikeHunter_BR"),
    ("UCbot_engag02", "EngageFarm"),
    ("UCbot_engag03", "ReactionBot_X"),
    ("UCbot_burst01", "RapidFire_YT"),
    ("UCbot_burst02", "FloodComment"),
    ("UCbot_burst03", "BurstPoster99"),
    # 12 humanos (não selecionados)
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

# ─── Textos de bots (agrupados por padrão) ──────────────────────────────────

SPAM_TEXTS = [
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

COPYPASTE_TEXTS = [
    "Primeiro! Like se você também chegou cedo!",
    "Quem tá assistindo em 2024? Deixa o like!",
    "Esse vídeo merece 1 milhão de likes!",
    "Alguém mais veio pelo TikTok?",
    "Ninguém: ... Absolutamente ninguém: ... Eu: assistindo esse vídeo",
]

ENGAGEMENT_TEXTS = [
    "Que vídeo INCRÍVEL!! Amei DEMAIS!! 😍😍😍",
    "Melhor canal do YouTube INTEIRO!! Recomendo!!",
    "Parabéns pelo conteúdo!! MARAVILHOSO!! 👏👏👏",
    "Simplesmente PERFEITO!! Nota 10!! ⭐⭐⭐⭐⭐",
    "Assisti 3 vezes!! Cada vez melhor!! SENSACIONAL!!",
    "Não tenho palavras!! QUE PRODUÇÃO!! TOP DEMAIS!!",
    "MELHOR vídeo que já vi na VIDA!! Sério mesmo!!",
]

BURST_TEXTS = [
    "kkkkkk muito bom",
    "kkk real",
    "verdade kkk",
    "sim sim concordo",
    "exatamente isso",
    "boa boa",
    "top top top",
    "haha demais",
]

# ─── Textos de humanos ──────────────────────────────────────────────────────

HUMAN_TEXTS = [
    "Muito bom o vídeo, explicou bem o conceito de detecção de bots. "
    "Vou usar como referência na minha pesquisa de TCC.",
    "Discordo do ponto sobre falsos positivos. Na prática, a taxa é bem "
    "menor quando se combina múltiplas features.",
    "Poderia indicar algum artigo sobre o tema? Estou começando a estudar "
    "NLP aplicado a redes sociais.",
    "Excelente conteúdo! Compartilhei com meu grupo de pesquisa da PUCRS.",
    "Uma sugestão: seria legal incluir análise de sentimento como feature "
    "adicional para detectar bots com comentários positivos genéricos.",
    "Tenho uma dúvida técnica: como vocês lidam com bots que usam variações "
    "de texto para evitar detecção por comentários idênticos?",
    "Trabalho com moderação de conteúdo há 5 anos. A heurística de "
    "intervalo temporal é a mais eficaz na prática.",
    "Obrigado pela resposta! Vou conferir o paper que você indicou no " "minuto 12:30.",
    "Interessante a abordagem de união de critérios. No meu mestrado "
    "estou usando interseção — vou testar a diferença.",
    "Faz sentido combinar múltiplas heurísticas. O percentil sozinho "
    "gera muitos falsos positivos com power users legítimos.",
    "Ótima explicação sobre a API do YouTube. A documentação oficial é "
    "confusa demais, esse vídeo ajudou bastante.",
    "Já testaram com vídeos de música? O padrão de bots é bem diferente "
    "em comparação com vídeos educacionais.",
    "Concordo com o João Santos — as features de perfil (data de criação "
    "do canal, foto padrão) são muito discriminativas.",
    "Parabéns pelo trabalho! Estou usando a mesma abordagem no meu projeto "
    "de IC e os resultados são promissores.",
    "A parte sobre canais criados recentemente é crucial. Bots costumam "
    "usar contas descartáveis com menos de 30 dias.",
    "Qual o tamanho mínimo de dataset que vocês recomendam? Tenho um vídeo "
    "com apenas 200 comentários — vale a pena analisar?",
    "Não sei se vocês perceberam, mas o CopyPasteKing ali nos comentários "
    "é claramente um bot — texto idêntico 3 vezes kk",
    "Seria possível adaptar essa metodologia para comentários do Instagram? "
    "As APIs são diferentes mas o padrão de bots é parecido.",
    "Gostei da ferramenta! Uma feature útil seria exportar o dataset "
    "final em formato compatível com o Weka ou scikit-learn.",
    "O critério de comentários curtos precisa de cuidado — em vídeos de "
    "humor, humanos também postam 'kkkkk' e 'hahaha'.",
]


def _get_bot_texts(channel_id):
    """Retorna os textos apropriados para cada tipo de bot."""
    if "spam" in channel_id:
        return SPAM_TEXTS
    if "copy" in channel_id:
        return COPYPASTE_TEXTS
    if "engag" in channel_id:
        return ENGAGEMENT_TEXTS
    if "burst" in channel_id:
        return BURST_TEXTS
    return SPAM_TEXTS


def _get_bot_criteria(channel_id):
    """Retorna os critérios que cada bot atende."""
    if "spam" in channel_id:
        return ["percentil", "intervalo", "perfil"]
    if "copy" in channel_id:
        return ["identicos", "intervalo"]
    if "engag" in channel_id:
        return ["curtos", "percentil"]
    if "burst" in channel_id:
        return ["intervalo", "curtos"]
    return ["percentil"]


def seed():
    db = SessionLocal()

    try:
        existing = (
            db.query(Collection)
            .filter(Collection.video_id == VIDEO_ID, Collection.status == "completed")
            .first()
        )
        if existing:
            ds = db.query(Dataset).filter(Dataset.collection_id == existing.id).first()
            if ds:
                print(
                    f"Seed para '{VIDEO_ID}' ja existe (coleta={existing.id}, "
                    f"dataset={ds.id}). Nada a fazer."
                )
                return
            collection = existing
            print(
                f"Coleta para '{VIDEO_ID}' ja existe (id={existing.id}). "
                "Criando apenas o dataset."
            )
        else:
            admin = db.query(User).filter(User.role == "admin").first()
            if not admin:
                print("ERRO: Nenhum usuario admin encontrado. Crie um primeiro.")
                return

            # ─── Criar coleta ────────────────────────────────────────────
            collection = Collection(
                video_id=VIDEO_ID,
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
            db.add(collection)
            db.flush()
            print(f"Coleta criada: id={collection.id}")

            # ─── Criar comentarios ───────────────────────────────────────
            base_time = datetime(2024, 1, 15, 8, 0, 0)
            comment_count = 0

            for user_idx, (channel_id, display_name) in enumerate(YOUTUBE_USERS):
                is_bot = channel_id.startswith("UCbot_")
                texts = _get_bot_texts(channel_id) if is_bot else HUMAN_TEXTS

                # Bots: 4–8 comentarios, humanos: 2–4
                n_comments = random.randint(4, 8) if is_bot else random.randint(2, 4)

                for i in range(n_comments):
                    if is_bot:
                        # Bots postam em rajada (2–5 min entre comentarios)
                        pub_time = base_time + timedelta(
                            hours=user_idx * 3,
                            minutes=i * random.randint(2, 5),
                        )
                    else:
                        # Humanos postam em dias/horas diferentes
                        pub_time = base_time + timedelta(
                            days=random.randint(0, 10),
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                        )

                    text = texts[i % len(texts)]
                    # Bots copypaste repetem o mesmo texto; outros variam
                    if "copy" in channel_id:
                        text = texts[0]  # sempre o mesmo

                    comment = Comment(
                        collection_id=collection.id,
                        comment_id=f"{channel_id}_c{i}",
                        parent_id=None,
                        author_channel_id=channel_id,
                        author_display_name=display_name,
                        text_original=text,
                        text_display=text,
                        like_count=0 if is_bot else random.randint(1, 30),
                        reply_count=0 if is_bot else random.randint(0, 5),
                        published_at=pub_time,
                        updated_at=pub_time,
                        author_profile_image_url=(
                            "https://yt3.ggpht.com/default"
                            if is_bot
                            else f"https://yt3.ggpht.com/{channel_id}"
                        ),
                        author_channel_url=f"https://youtube.com/channel/{channel_id}",
                        author_channel_published_at=(
                            datetime(2024, 1, random.randint(1, 14))
                            if is_bot
                            else datetime(
                                random.randint(2015, 2019),
                                random.randint(1, 12),
                                random.randint(1, 28),
                            )
                        ),
                    )
                    db.add(comment)
                    comment_count += 1

            collection.total_comments = comment_count
            db.flush()
            n_bots = len([u for u in YOUTUBE_USERS if u[0].startswith("UCbot_")])
            n_hum = len(YOUTUBE_USERS) - n_bots
            print(
                f"  {comment_count} comentarios criados"
                f" ({n_bots} bots, {n_hum} humanos)"
            )

        # ─── Criar dataset (18 bots selecionados) ───────────────────────
        admin = db.query(User).filter(User.role == "admin").first()

        dataset_name = f"{VIDEO_ID}_percentil_intervalo_perfil"
        existing_ds = db.query(Dataset).filter(Dataset.name == dataset_name).first()
        if existing_ds:
            print(f"Dataset '{dataset_name}' ja existe. Pulando.")
            return

        bot_users = [
            (cid, name) for cid, name in YOUTUBE_USERS if cid.startswith("UCbot_")
        ]

        dataset = Dataset(
            name=dataset_name,
            collection_id=collection.id,
            criteria_applied=["percentil", "intervalo", "perfil"],
            thresholds={"threshold_chars": 20, "threshold_seconds": 30},
            total_users_original=len(YOUTUBE_USERS),
            total_users_selected=len(bot_users),
            created_by=admin.id,
        )
        db.add(dataset)
        db.flush()
        print(f"Dataset criado: '{dataset.name}' (id={dataset.id})")

        for channel_id, display_name in bot_users:
            # Contar comentarios deste autor
            count = (
                db.query(Comment)
                .filter(
                    Comment.collection_id == collection.id,
                    Comment.author_channel_id == channel_id,
                )
                .count()
            )
            entry = DatasetEntry(
                dataset_id=dataset.id,
                author_channel_id=channel_id,
                author_display_name=display_name,
                comment_count=count,
                matched_criteria=_get_bot_criteria(channel_id),
            )
            db.add(entry)

        db.commit()
        print(f"  {len(bot_users)} entries criadas")
        print()
        print("=" * 60)
        print("Seed concluido!")
        print()
        print("Dados criados:")
        print(f"  Coleta: {VIDEO_ID} ({collection.total_comments} comentarios)")
        print(f"  Dataset: {dataset_name} ({len(bot_users)} usuarios suspeitos)")
        print(
            f"  Usuarios totais: {len(YOUTUBE_USERS)} "
            f"({len(bot_users)} bots + {len(YOUTUBE_USERS) - len(bot_users)} humanos)"
        )
        print()
        print("Para testar:")
        print("  1. Logar como 'user' / 'user1234' e anotar comentarios")
        print("  2. Logar como 'davint' / 'admin123' e ver o progresso")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"ERRO: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
