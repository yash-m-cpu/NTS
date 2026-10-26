from typing import Callable, Dict, Any, List
from app.models.features import FeatureWindow

MetricFunction = Callable[[List[FeatureWindow]], Dict[str, Any]]

class MetricRegistry:
    def __init__(self):
        self._metrics: Dict[str, MetricFunction] = {}
        self.version = "1.0.0"

    def register(self, metric_key: str):
        def decorator(func: MetricFunction):
            self._metrics[metric_key] = func
            return func
        return decorator
        
    def get_metrics(self):
        return self._metrics
        
registry = MetricRegistry()
