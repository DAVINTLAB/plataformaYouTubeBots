from models.collection import Comment

from .base import SelectorBase


class TimeIntervalSelector(SelectorBase):
    """Seleciona usuários que postaram comentários em rajada (intervalo < threshold)."""

    def __init__(self, threshold_seconds: int = 30):
        self.threshold_seconds = threshold_seconds

    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]:
        suspicious: set[str] = set()
        for uid, comments in user_comments.items():
            if len(comments) < 2:
                continue

            sorted_comments = sorted(comments, key=lambda c: c.published_at)
            for a, b in zip(sorted_comments, sorted_comments[1:], strict=False):
                delta = (b.published_at - a.published_at).total_seconds()
                if 0 <= delta < self.threshold_seconds:
                    suspicious.add(uid)
                    break

        return suspicious
