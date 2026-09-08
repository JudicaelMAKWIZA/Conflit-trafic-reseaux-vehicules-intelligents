"""Observateur passif ; le calcul final se fait sur les logs clos."""
from traffic_conflict.metrics.compute import compute_metrics


class MetricsCollector:
    def __init__(self):
        self.observation_count = 0

    def observe(self, snapshot):
        self.observation_count += 1

    def finalize(self, output_dir):
        return compute_metrics(output_dir)
