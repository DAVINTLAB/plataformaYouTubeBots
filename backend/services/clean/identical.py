from sqlalchemy.orm import Session

from models.collection import Comment

from .base import SelectorBase


class IdenticalSelector(SelectorBase):
    """Seleciona usuários que postaram comentários idênticos em múltiplos vídeos.

    Cruza com outras coletas no banco: se o mesmo author_channel_id postou
    o mesmo text_original em coletas diferentes, é considerado suspeito.
    """

    def __init__(self, db: Session, collection_id: str):
        self.db = db
        self.collection_id = collection_id

    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]:
        if not user_comments:
            return set()

        suspicious: set[str] = set()

        for uid, comments in user_comments.items():
            texts = {c.text_original.strip().lower() for c in comments}
            if not texts:
                continue

            # Buscar comentários do mesmo autor em OUTRAS coletas
            other_comments = (
                self.db.query(Comment.text_original)
                .filter(
                    Comment.author_channel_id == uid,
                    Comment.collection_id != self.collection_id,
                )
                .all()
            )

            other_texts = {r.text_original.strip().lower() for r in other_comments}
            if texts & other_texts:
                suspicious.add(uid)

        return suspicious
