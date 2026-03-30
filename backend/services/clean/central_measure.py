"""Classe base para seletores de medida central (Template Method — DRY + OCP).

Os seletores Mean, Median e Mode compartilham a mesma lógica:
1. Contar comentários por usuário
2. Remover outliers via IQR (apenas para cálculo do threshold)
3. Calcular a medida central (threshold)
4. Selecionar usuários acima do threshold

O único passo que varia é o cálculo da medida central (passo 3),
delegado ao método abstrato `_compute_threshold`.
"""

from abc import abstractmethod

from models.collection import Comment

from .base import SelectorBase
from .stats import remove_outliers_iqr


class CentralMeasureSelector(SelectorBase):
    """Template Method: subclasses só implementam _compute_threshold."""

    def select(self, user_comments: dict[str, list[Comment]]) -> set[str]:
        user_counts = {uid: len(cs) for uid, cs in user_comments.items()}
        if not user_counts:
            return set()

        clean_counts = remove_outliers_iqr([float(c) for c in user_counts.values()])
        threshold = self._compute_threshold(clean_counts)
        return {uid for uid, count in user_counts.items() if count > threshold}

    @abstractmethod
    def _compute_threshold(self, clean_counts: list[float]) -> float: ...
