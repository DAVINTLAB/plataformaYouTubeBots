import statistics

from .central_measure import CentralMeasureSelector


class MedianSelector(CentralMeasureSelector):
    """Seleciona usuários acima da mediana (após remoção de outliers via IQR)."""

    def _compute_threshold(self, clean_counts: list[float]) -> float:
        return statistics.median(clean_counts)
