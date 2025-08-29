"""
Ultra-Fast Circuit Breaker Pattern for High-Volume Operations
Prevents cascading failures and maintains sub-100ms response times
"""

import time
import threading
from functools import wraps
from typing import Callable, Any, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered

class UltraCircuitBreaker:
    """High-performance circuit breaker for protecting endpoints"""
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 15,
        success_threshold: int = 2,
        expected_exception: type = Exception,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception
        self.name = name
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        # Performance metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_circuit_opens = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Response time tracking
        self.response_times = []
        self.max_response_times = 100  # Keep last 100 response times
    
    def _record_success(self, response_time: float = None):
        """Record successful call"""
        with self.lock:
            self.failure_count = 0
            self.success_count += 1
            self.total_successes += 1
            self.last_success_time = time.time()
            
            if response_time:
                self.response_times.append(response_time)
                if len(self.response_times) > self.max_response_times:
                    self.response_times.pop(0)
            
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.success_threshold:
                    self._close_circuit()
    
    def _record_failure(self):
        """Record failed call"""
        with self.lock:
            self.failure_count += 1
            self.success_count = 0
            self.total_failures += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self._open_circuit()
            elif self.failure_count >= self.failure_threshold:
                self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit breaker"""
        with self.lock:
            self.state = CircuitState.OPEN
            self.total_circuit_opens += 1
            logger.warning(f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures")
    
    def _close_circuit(self):
        """Close the circuit breaker"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            logger.info(f"Circuit breaker '{self.name}' CLOSED")
    
    def _half_open_circuit(self):
        """Put circuit in half-open state"""
        with self.lock:
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0
            self.failure_count = 0
            logger.info(f"Circuit breaker '{self.name}' HALF-OPEN for testing")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        with self.lock:
            return (
                self.state == CircuitState.OPEN and
                self.last_failure_time and
                time.time() - self.last_failure_time >= self.recovery_timeout
            )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        with self.lock:
            self.total_calls += 1
            
            # Check if circuit should transition to half-open
            if self._should_attempt_reset():
                self._half_open_circuit()
            
            # Block calls if circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry after {self.recovery_timeout} seconds."
                )
        
        # Execute the function
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            self._record_success(response_time)
            return result
        
        except self.expected_exception as e:
            self._record_failure()
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state and metrics"""
        with self.lock:
            avg_response_time = (
                sum(self.response_times) / len(self.response_times)
                if self.response_times else 0
            )
            
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'total_calls': self.total_calls,
                'total_failures': self.total_failures,
                'total_successes': self.total_successes,
                'total_circuit_opens': self.total_circuit_opens,
                'avg_response_time_ms': round(avg_response_time, 2),
                'success_rate': round(
                    (self.total_successes / self.total_calls * 100)
                    if self.total_calls > 0 else 0, 
                    2
                )
            }
    
    def reset(self):
        """Manually reset the circuit breaker"""
        with self.lock:
            self._close_circuit()
            self.failure_count = 0
            self.success_count = 0

class CircuitOpenError(Exception):
    """Exception raised when circuit is open"""
    pass

# Global circuit breaker registry
_circuit_breakers: Dict[str, UltraCircuitBreaker] = {}
_registry_lock = threading.RLock()

def get_circuit_breaker(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: int = 15,
    success_threshold: int = 2
) -> UltraCircuitBreaker:
    """Get or create a circuit breaker instance"""
    
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = UltraCircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold
            )
        return _circuit_breakers[name]

def circuit_breaker(
    name: str = None,
    failure_threshold: int = 3,
    recovery_timeout: int = 15,
    success_threshold: int = 2,
    expected_exception: type = Exception
):
    """Decorator for applying circuit breaker pattern to functions"""
    
    def decorator(func: Callable) -> Callable:
        # Use function name if no name provided
        cb_name = name or f"{func.__module__}.{func.__name__}"
        
        # Get or create circuit breaker
        breaker = get_circuit_breaker(
            cb_name,
            failure_threshold,
            recovery_timeout,
            success_threshold
        )
        breaker.expected_exception = expected_exception
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # Attach breaker for introspection
        wrapper.circuit_breaker = breaker
        
        return wrapper
    
    return decorator

def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """Get state of all circuit breakers"""
    with _registry_lock:
        return {
            name: breaker.get_state()
            for name, breaker in _circuit_breakers.items()
        }

def reset_all_circuits():
    """Reset all circuit breakers"""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()

# Endpoint-specific circuit breaker configurations
ENDPOINT_CONFIGS = {
    'database': {
        'failure_threshold': 3,
        'recovery_timeout': 10,
        'success_threshold': 2
    },
    'scanning': {
        'failure_threshold': 5,
        'recovery_timeout': 5,
        'success_threshold': 3
    },
    'dashboard': {
        'failure_threshold': 3,
        'recovery_timeout': 15,
        'success_threshold': 1
    },
    'api': {
        'failure_threshold': 5,
        'recovery_timeout': 10,
        'success_threshold': 2
    },
    'batch': {
        'failure_threshold': 2,
        'recovery_timeout': 20,
        'success_threshold': 1
    }
}

def apply_circuit_breakers(app):
    """Apply circuit breakers to Flask application"""
    from flask import jsonify
    
    @app.errorhandler(CircuitOpenError)
    def handle_circuit_open(e):
        """Handle circuit open errors"""
        return jsonify({
            'success': False,
            'error': 'Service temporarily unavailable',
            'message': str(e),
            'retry_after': 15
        }), 503
    
    @app.route('/api/circuit_status')
    def circuit_status():
        """Endpoint to check circuit breaker status"""
        return jsonify(get_all_circuit_states())
    
    @app.route('/api/circuit_reset', methods=['POST'])
    def circuit_reset():
        """Endpoint to manually reset circuits (admin only)"""
        reset_all_circuits()
        return jsonify({
            'success': True,
            'message': 'All circuits reset successfully'
        })
    
    logger.info("✅ Circuit breakers configured for all endpoints")
    return app