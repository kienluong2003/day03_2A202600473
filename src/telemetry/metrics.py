import time
from typing import Dict, Any, List
from src.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage) # Mock cost calculation
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Estimate request cost from token usage.
        Prices are USD per 1M tokens and intended for lab-level analysis.
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        pricing_per_million = {
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
            "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
            "local": {"input": 0.0, "output": 0.0},
            "default": {"input": 1.0, "output": 2.0},
        }

        normalized_model = (model or "").lower()
        selected_price = pricing_per_million["default"]
        for model_key, model_price in pricing_per_million.items():
            if model_key == "default":
                continue
            if model_key in normalized_model:
                selected_price = model_price
                break

        input_cost = (prompt_tokens / 1_000_000) * selected_price["input"]
        output_cost = (completion_tokens / 1_000_000) * selected_price["output"]
        return round(input_cost + output_cost, 6)

# Global tracker instance
tracker = PerformanceTracker()
