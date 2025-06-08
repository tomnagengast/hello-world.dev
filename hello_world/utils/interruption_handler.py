"""Interruption handling for conversation flow."""

import threading
import time
from typing import Optional, Callable
import structlog


logger = structlog.get_logger()


class InterruptionHandler:
    """Handles interruption detection and coordination."""
    
    def __init__(self):
        self.is_interrupted = False
        self._lock = threading.Lock()
        self._callbacks = []
        self._last_interruption_time = 0
        
    def trigger_interruption(self) -> None:
        """Trigger an interruption event."""
        with self._lock:
            if self.is_interrupted:
                # Already interrupted
                return
                
            self.is_interrupted = True
            self._last_interruption_time = time.time()
            
        logger.info("Interruption triggered")
        
        # Execute callbacks
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error("Interruption callback error", error=str(e))
                
    def reset(self) -> None:
        """Reset interruption state."""
        with self._lock:
            self.is_interrupted = False
            
        logger.debug("Interruption state reset")
        
    def is_interrupted_atomic(self) -> bool:
        """Check interruption state atomically."""
        with self._lock:
            return self.is_interrupted
            
    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called on interruption."""
        self._callbacks.append(callback)
        
    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """Unregister an interruption callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            
    def get_time_since_interruption(self) -> Optional[float]:
        """Get time since last interruption in seconds."""
        if self._last_interruption_time == 0:
            return None
        return time.time() - self._last_interruption_time