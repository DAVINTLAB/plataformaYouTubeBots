import statistics

from .central_measure import CentralMeasureSelector


class MeanSelector(CentralMeasureSelector):
    """Seleciona usuários acima da média (após remoção de outliers via IQR)."""

    def _compute_threshold(self, clean_counts: list[float]) -> float:
        return statistics.mean(clean_counts)
