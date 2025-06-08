"""
Performance metrics collection and analysis for the conversation system.
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import structlog

logger = structlog.get_logger()


@dataclass
class LatencyMetrics:
    """Latency metrics for a specific component."""
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float
    samples: int


@dataclass
class SessionMetrics:
    """Metrics for a single conversation session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_interactions: int
    stt_latencies: List[float]
    ai_latencies: List[float]
    tts_latencies: List[float]
    e2e_latencies: List[float]
    errors: List[Dict[str, Any]]
    interruptions: int


class MetricsCollector:
    """
    Collects and analyzes performance metrics for the conversation system.
    Tracks latencies, errors, and system performance across sessions.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".conversation_system" / "metrics"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[SessionMetrics] = None
        self.session_start_time = None
        
    def start_session(self, session_id: str) -> None:
        """Start a new metrics collection session."""
        logger.debug("Starting metrics collection", session_id=session_id)
        
        self.current_session = SessionMetrics(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=None,
            total_interactions=0,
            stt_latencies=[],
            ai_latencies=[],
            tts_latencies=[],
            e2e_latencies=[],
            errors=[],
            interruptions=0
        )
        self.session_start_time = time.time()
        
    def end_session(self) -> None:
        """End the current metrics collection session."""
        if not self.current_session:
            logger.warning("No active session to end")
            return
            
        self.current_session.end_time = datetime.now()
        logger.debug("Ending metrics collection", 
                    session_id=self.current_session.session_id,
                    interactions=self.current_session.total_interactions)
        
    def record_stt_latency(self, latency_ms: float) -> None:
        """Record STT processing latency."""
        if self.current_session:
            self.current_session.stt_latencies.append(latency_ms)
            
    def record_ai_latency(self, latency_ms: float) -> None:
        """Record AI response latency."""
        if self.current_session:
            self.current_session.ai_latencies.append(latency_ms)
            
    def record_tts_latency(self, latency_ms: float) -> None:
        """Record TTS processing latency."""
        if self.current_session:
            self.current_session.tts_latencies.append(latency_ms)
            
    def record_e2e_latency(self, latency_ms: float) -> None:
        """Record end-to-end latency (user speech -> audio output)."""
        if self.current_session:
            self.current_session.e2e_latencies.append(latency_ms)
            
    def record_interaction(self) -> None:
        """Record a completed interaction."""
        if self.current_session:
            self.current_session.total_interactions += 1
            
    def record_error(self, component: str, error: str, metadata: Optional[Dict] = None) -> None:
        """Record an error occurrence."""
        if self.current_session:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "component": component,
                "error": error,
                "metadata": metadata or {}
            }
            self.current_session.errors.append(error_record)
            
    def record_interruption(self) -> None:
        """Record a user interruption event."""
        if self.current_session:
            self.current_session.interruptions += 1
            
    def _calculate_latency_stats(self, latencies: List[float]) -> LatencyMetrics:
        """Calculate statistical metrics for a list of latencies."""
        if not latencies:
            return LatencyMetrics(0, 0, 0, 0, 0, 0, 0)
            
        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)
        
        def percentile(p: float) -> float:
            index = int(p * count)
            if index >= count:
                index = count - 1
            return sorted_latencies[index]
        
        return LatencyMetrics(
            min=min(latencies),
            max=max(latencies),
            avg=sum(latencies) / count,
            p50=percentile(0.5),
            p95=percentile(0.95),
            p99=percentile(0.99),
            samples=count
        )
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current session metrics."""
        if not self.current_session:
            return {"error": "No active session"}
            
        session_duration = 0
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
            
        return {
            "session_id": self.current_session.session_id,
            "session_duration_seconds": session_duration,
            "total_interactions": self.current_session.total_interactions,
            "stt_latency_ms": asdict(self._calculate_latency_stats(self.current_session.stt_latencies)),
            "ai_latency_ms": asdict(self._calculate_latency_stats(self.current_session.ai_latencies)),
            "tts_latency_ms": asdict(self._calculate_latency_stats(self.current_session.tts_latencies)),
            "e2e_latency_ms": asdict(self._calculate_latency_stats(self.current_session.e2e_latencies)),
            "total_errors": len(self.current_session.errors),
            "interruptions": self.current_session.interruptions,
            "error_rate": len(self.current_session.errors) / max(1, self.current_session.total_interactions)
        }
        
    def save_metrics(self) -> None:
        """Save current session metrics to storage."""
        if not self.current_session:
            logger.warning("No session to save")
            return
            
        try:
            filename = f"session_{self.current_session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.storage_path / filename
            
            # Convert session to dict for JSON serialization
            session_dict = asdict(self.current_session)
            session_dict["start_time"] = self.current_session.start_time.isoformat()
            if self.current_session.end_time:
                session_dict["end_time"] = self.current_session.end_time.isoformat()
            else:
                session_dict["end_time"] = None
                
            with open(filepath, 'w') as f:
                json.dump(session_dict, f, indent=2)
                
            logger.info("Metrics saved", filepath=str(filepath))
            
        except Exception as e:
            logger.error("Failed to save metrics", error=str(e))
            
    def load_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Load metrics for a specific session."""
        try:
            # Find the most recent file for this session
            pattern = f"session_{session_id}_*.json"
            files = list(self.storage_path.glob(pattern))
            
            if not files:
                return None
                
            # Get the most recent file
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
                
            # Convert back to SessionMetrics
            data["start_time"] = datetime.fromisoformat(data["start_time"])
            if data["end_time"]:
                data["end_time"] = datetime.fromisoformat(data["end_time"])
                
            return SessionMetrics(**data)
            
        except Exception as e:
            logger.error("Failed to load session metrics", 
                        session_id=session_id, error=str(e))
            return None
            
    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate a comprehensive metrics report for the last N days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Load all recent session files
            sessions = []
            for filepath in self.storage_path.glob("session_*.json"):
                try:
                    # Check file modification time
                    if datetime.fromtimestamp(filepath.stat().st_mtime) < cutoff_date:
                        continue
                        
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    data["start_time"] = datetime.fromisoformat(data["start_time"])
                    if data["end_time"]:
                        data["end_time"] = datetime.fromisoformat(data["end_time"])
                        
                    sessions.append(SessionMetrics(**data))
                    
                except Exception as e:
                    logger.warning("Failed to load session file", 
                                  filepath=str(filepath), error=str(e))
                    
            if not sessions:
                return {
                    "period_days": days,
                    "total_sessions": 0,
                    "total_interactions": 0,
                    "message": "No data available for the specified period"
                }
                
            # Aggregate metrics
            all_stt_latencies = []
            all_ai_latencies = []
            all_tts_latencies = []
            all_e2e_latencies = []
            total_interactions = 0
            total_errors = 0
            total_interruptions = 0
            
            for session in sessions:
                all_stt_latencies.extend(session.stt_latencies)
                all_ai_latencies.extend(session.ai_latencies)
                all_tts_latencies.extend(session.tts_latencies)
                all_e2e_latencies.extend(session.e2e_latencies)
                total_interactions += session.total_interactions
                total_errors += len(session.errors)
                total_interruptions += session.interruptions
                
            return {
                "period_days": days,
                "total_sessions": len(sessions),
                "total_interactions": total_interactions,
                "total_errors": total_errors,
                "total_interruptions": total_interruptions,
                "error_rate": total_errors / max(1, total_interactions),
                "interruption_rate": total_interruptions / max(1, total_interactions),
                "stt_latency_ms": asdict(self._calculate_latency_stats(all_stt_latencies)),
                "ai_latency_ms": asdict(self._calculate_latency_stats(all_ai_latencies)),
                "tts_latency_ms": asdict(self._calculate_latency_stats(all_tts_latencies)),
                "e2e_latency_ms": asdict(self._calculate_latency_stats(all_e2e_latencies)),
            }
            
        except Exception as e:
            logger.error("Failed to generate report", error=str(e))
            return {"error": f"Failed to generate report: {str(e)}"}