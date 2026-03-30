from datetime import UTC, datetime, timedelta

from models.collection import Comment

from .base import SelectorBase

# Canal criado há menos de 90 dias é considerado recente
_RECENT_CHANNEL_DAYS = 90

# Avatar padrão do YouTube (sem foto personalizada)
_DEFAULT_AVATARS = (
    "ggpht.com/a/default",
    "ggpht.com/a-/default",
)


class ProfileSelector(SelectorBase):
    """Seleciona usuários com perfil suspeito usando dados já coletados.

    Critérios: sem foto de avatar ou data de criação recente do canal.
    Usa author_profile_image_url e author_channel_published_at da coleta.
    """

    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]:
        if not user_comments:
            return set()

        now = datetime.now(UTC)
        suspicious: set[str] = set()

        for uid, comments in user_comments.items():
            first = comments[0]

            # Avatar padrão?
            avatar = first.author_profile_image_url or ""
            is_default_avatar = any(d in avatar for d in _DEFAULT_AVATARS)

            # Canal recente?
            is_recent = False
            pub = first.author_channel_published_at
            if pub is not None:
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=UTC)
                is_recent = (now - pub) < timedelta(days=_RECENT_CHANNEL_DAYS)

            if is_default_avatar or is_recent:
                suspicious.add(uid)

        return suspicious
