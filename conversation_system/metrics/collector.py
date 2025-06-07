"""Metrics collection for performance monitoring."""

import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import structlog


logger = structlog.get_logger()


@dataclass
class LatencyMetric:
    """Represents a latency measurement."""
    timestamp: float
    value: float
    metric_type: str
    metadata: Optional[Dict[str, Any]] = None


class MetricsCollector:
    """Collects and stores performance metrics."""
    
    def __init__(self, metrics_dir: str = "./metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_metrics: List[LatencyMetric] = []
        self.session_start_time = time.time()
        
        # Metric aggregates for current session
        self.stt_latencies: List[float] = []
        self.ai_latencies: List[float] = []
        self.tts_latencies: List[float] = []
        self.e2e_latencies: List[float] = []
        
    def record_stt_latency(self, latency: float) -> None:
        """Record STT latency metric."""
        metric = LatencyMetric(
            timestamp=time.time(),
            value=latency,
            metric_type="stt_latency"
        )
        self.current_metrics.append(metric)
        self.stt_latencies.append(latency)
        
        logger.debug("Recorded STT latency", latency_ms=latency * 1000)
        
    def record_ai_latency(self, latency: float) -> None:
        """Record AI response latency metric."""
        metric = LatencyMetric(
            timestamp=time.time(),
            value=latency,
            metric_type="ai_latency"
        )
        self.current_metrics.append(metric)
        self.ai_latencies.append(latency)
        
        logger.debug("Recorded AI latency", latency_ms=latency * 1000)
        
    def record_tts_latency(self, latency: float) -> None:
        """Record TTS latency metric."""
        metric = LatencyMetric(
            timestamp=time.time(),
            value=latency,
            metric_type="tts_latency"
        )
        self.current_metrics.append(metric)
        self.tts_latencies.append(latency)
        
        logger.debug("Recorded TTS latency", latency_ms=latency * 1000)
        
    def record_e2e_latency(self, latency: float) -> None:
        """Record end-to-end latency metric."""
        metric = LatencyMetric(
            timestamp=time.time(),
            value=latency,
            metric_type="e2e_latency"
        )
        self.current_metrics.append(metric)
        self.e2e_latencies.append(latency)
        
        logger.debug("Recorded E2E latency", latency_ms=latency * 1000)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for current session."""
        def calculate_stats(values: List[float]) -> Dict[str, float]:
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0}
                
            sorted_values = sorted(values)
            return {
                "min": min(values) * 1000,  # Convert to ms
                "max": max(values) * 1000,
                "avg": sum(values) / len(values) * 1000,
                "p50": sorted_values[len(sorted_values) // 2] * 1000,
                "p95": sorted_values[int(len(sorted_values) * 0.95)] * 1000 if len(sorted_values) > 1 else sorted_values[0] * 1000
            }
            
        return {
            "session_duration_seconds": time.time() - self.session_start_time,
            "total_interactions": len(self.e2e_latencies),
            "stt_latency_ms": calculate_stats(self.stt_latencies),
            "ai_latency_ms": calculate_stats(self.ai_latencies),
            "tts_latency_ms": calculate_stats(self.tts_latencies),
            "e2e_latency_ms": calculate_stats(self.e2e_latencies)
        }
        
    def save_metrics(self) -> None:
        """Save current metrics to daily file."""
        if not self.current_metrics:
            return
            
        # Get today's metrics file
        today = datetime.now().strftime("%Y-%m-%d")
        metrics_file = self.metrics_dir / f"{today}.json"
        
        # PSEUDOCODE: Save metrics
        # try:
        #     # Load existing metrics if file exists
        #     existing_metrics = []
        #     if metrics_file.exists():
        #         with open(metrics_file, 'r') as f:
        #             existing_metrics = json.load(f)
        #             
        #     # Append current metrics
        #     for metric in self.current_metrics:
        #         existing_metrics.append(asdict(metric))
        #         
        #     # Save updated metrics
        #     with open(metrics_file, 'w') as f:
        #         json.dump(existing_metrics, f, indent=2)
        #         
        #     logger.info("Saved metrics", 
        #                metric_count=len(self.current_metrics),
        #                file=str(metrics_file))
        #                
        #     # Clear current metrics
        #     self.current_metrics.clear()
        #     
        # except Exception as e:
        #     logger.error("Failed to save metrics", error=str(e))
        
        pass
        
    def load_metrics(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load metrics for a specific date."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        metrics_file = self.metrics_dir / f"{date}.json"
        
        # PSEUDOCODE: Load metrics
        # if not metrics_file.exists():
        #     return []
        #     
        # try:
        #     with open(metrics_file, 'r') as f:
        #         return json.load(f)
        # except Exception as e:
        #     logger.error("Failed to load metrics", 
        #                 date=date,
        #                 error=str(e))
        #     return []
        
        return []
        
    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate metrics report for last N days."""
        # PSEUDOCODE: Generate report
        # from datetime import timedelta
        # 
        # all_metrics = []
        # end_date = datetime.now()
        # start_date = end_date - timedelta(days=days)
        # 
        # # Load metrics for each day
        # current_date = start_date
        # while current_date <= end_date:
        #     date_str = current_date.strftime("%Y-%m-%d")
        #     daily_metrics = self.load_metrics(date_str)
        #     all_metrics.extend(daily_metrics)
        #     current_date += timedelta(days=1)
        #     
        # # Calculate aggregate statistics
        # # ... (similar to get_summary but across multiple days)
        # 
        # return report
        
        pass