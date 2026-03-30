from models.collection import Comment

from .base import SelectorBase


class PercentileSelector(SelectorBase):
    """Seleciona usuários no top 30% de volume de comentários."""

    def __init__(self, top_percent: float = 0.30):
        self.top_percent = top_percent

    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]:
        user_counts = {uid: len(cs) for uid, cs in user_comments.items()}
        if not user_counts:
            return set()

        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        cutoff = max(1, int(len(sorted_users) * self.top_percent))
        return {uid for uid, _ in sorted_users[:cutoff]}
