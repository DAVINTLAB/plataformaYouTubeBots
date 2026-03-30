from models.collection import Comment

from .base import SelectorBase


class ShortCommentsSelector(SelectorBase):
    """Seleciona usuários com maioria de comentários curtos ou repetitivos."""

    def __init__(self, threshold_chars: int = 20):
        self.threshold_chars = threshold_chars

    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]:
        suspicious: set[str] = set()
        for uid, comments in user_comments.items():
            if not comments:
                continue

            short = [
                c
                for c in comments
                if len(c.text_original.strip()) < self.threshold_chars
            ]
            texts = [c.text_original.strip().lower() for c in comments]
            repetition_rate = 1 - len(set(texts)) / len(texts) if texts else 0

            if len(short) / len(comments) > 0.7 or repetition_rate > 0.5:
                suspicious.add(uid)

        return suspicious
