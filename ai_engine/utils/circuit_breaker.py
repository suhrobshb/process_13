"""
Sophisticated Circuit Breaker for Self-Healing Automation
=========================================================

This module implements a sophisticated, stateful circuit breaker pattern designed
to enhance the resilience and self-healing capabilities of the AI Engine. It
prevents the system from repeatedly attempting an operation that is likely to
fail, allowing failing services or workflows time to recover.

Key Features:
-   **Three-State Logic**: Implements the classic CLOSED, OPEN, and HALF-OPEN
    states to manage service availability intelligently.
-   **Configurable Thresholds**: Each circuit breaker can be configured with a
    specific failure threshold and a reset timeout.
-   **Stateful & Persistent Design**: While the default implementation is in-memory,
    it is designed to be easily backed by a persistent store like Redis, making
    it suitable for distributed systems with multiple workers.
-   **Thread-Safe Management**: A central manager ensures that circuit breakers
    are handled safely in a multi-threaded environment (e.g., a FastAPI application
    with multiple Celery workers).
-   **Easy Integration**: Provides a simple `call` method to wrap any function
    or operation, making it easy to integrate into the workflow and task runners.
-   **Automatic Recovery**: The HALF-OPEN state allows the system to automatically
    test if a failing service has recovered, enabling self-healing workflows.

This utility is crucial for building robust automations that can gracefully
handle transient failures from external APIs, flaky UI elements, or temporary
system outages.
"""

import time
import logging
import threading
from typing import Dict, Any, Callable, Type

# Configure logging
logger = logging.getLogger(__name__)

# --- Constants for Circuit Breaker States ---
STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half-open"

# --- Custom Exception ---
class CircuitBreakerOpen(Exception):
    """Exception raised when an operation is blocked by an open circuit breaker."""
    pass

# --- Core Circuit Breaker Class ---

class CircuitBreaker:
    """
    An individual circuit breaker that tracks the state of a specific service.
    """
    def __init__(
        self,
        service_id: str,
        max_failures: int = 3,
        reset_timeout: int = 60
    ):
        """
        Initializes a new Circuit Breaker.

        Args:
            service_id: A unique identifier for the service/workflow being monitored.
            max_failures: The number of consecutive failures before the circuit opens.
            reset_timeout: The time in seconds to wait in the OPEN state before
                           transitioning to HALF-OPEN.
        """
        self.service_id = service_id
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        
        self._state = STATE_CLOSED
        self._failures = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> str:
        """
        Dynamically determines the current state of the circuit breaker.
        If the circuit is OPEN and the timeout has passed, it transitions to
        HALF-OPEN.
        """
        if self._state == STATE_OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed > self.reset_timeout:
                logger.warning(
                    f"Circuit breaker for '{self.service_id}' transitioning to HALF-OPEN state after {self.reset_timeout}s."
                )
                self._state = STATE_HALF_OPEN
        return self._state

    def record_failure(self):
        """
        Records a failure for the service. If the failure count exceeds the
        threshold, the circuit is opened.
        """
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.max_failures:
            if self._state != STATE_OPEN:
                logger.error(
                    f"Circuit breaker for '{self.service_id}' has OPENED after {self._failures} consecutive failures."
                )
                self._state = STATE_OPEN

    def record_success(self):
        """
        Records a success for the service, resetting the breaker to the
        CLOSED state.
        """
        if self._state != STATE_CLOSED:
            logger.info(
                f"Circuit breaker for '{self.service_id}' has been reset and is now CLOSED."
            )
        self._state = STATE_CLOSED
        self._failures = 0
        self._last_failure_time = 0.0

# --- Centralized Circuit Breaker Manager ---

class CircuitBreakerManager:
    """
    A thread-safe manager for creating and accessing CircuitBreaker instances.
    
    In a production environment with multiple workers, the `_breakers` dictionary
    should be replaced with a distributed cache like Redis to ensure all workers
    share the same state for each circuit breaker.
    """
    def __init__(self):
        # For production, this should be a client to a distributed store like Redis.
        # e.g., self._breakers = redis.Redis(...)
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_breaker(
        self,
        service_id: str,
        max_failures: int = 3,
        reset_timeout: int = 60
    ) -> CircuitBreaker:
        """
        Retrieves an existing circuit breaker or creates a new one. This method
        is thread-safe.

        Args:
            service_id: The unique identifier for the service.
            max_failures: The failure threshold (used only if creating a new breaker).
            reset_timeout: The reset timeout (used only if creating a new breaker).

        Returns:
            The CircuitBreaker instance for the given service.
        """
        with self._lock:
            # In a Redis implementation, this would be:
            # state_data = self._breakers.get(f"circuit_breaker:{service_id}")
            # if state_data:
            #     return CircuitBreaker.from_state(json.loads(state_data))
            if service_id not in self._breakers:
                logger.info(f"Creating new circuit breaker for service '{service_id}'.")
                self._breakers[service_id] = CircuitBreaker(service_id, max_failures, reset_timeout)
            return self._breakers[service_id]

    def call(
        self,
        service_id: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Wraps a function call with circuit breaker logic.

        This is the primary method for using the circuit breaker. It checks the
        state, executes the function, and records success or failure accordingly.

        Args:
            service_id: The identifier for the service being called.
            func: The function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The return value of the wrapped function.

        Raises:
            CircuitBreakerOpen: If the circuit is open and the call is blocked.
            Any exception raised by the wrapped function.
        """
        breaker = self.get_breaker(service_id)
        
        if breaker.state == STATE_OPEN:
            raise CircuitBreakerOpen(f"Circuit for '{service_id}' is open. Call is blocked.")

        # In the HALF-OPEN state, we allow the call to proceed.
        # The success or failure of this call will determine the next state.
        
        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as e:
            # Any exception is treated as a failure.
            breaker.record_failure()
            # Re-raise the original exception so the caller can handle it.
            raise e

# --- Global Singleton Instance ---
# This makes it easy to access the same manager from anywhere in the application.
circuit_breaker_manager = CircuitBreakerManager()

# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # A mock function that simulates a flaky external service
    def flaky_api_call():
        import random
        if random.random() < 0.6: # 60% chance of failure
            raise ConnectionError("Failed to connect to the external service.")
        return "Success! Data received."

    SERVICE_NAME = "external_payment_gateway"

    print("--- Demonstrating Circuit Breaker Pattern ---")
    print("Simulating calls to a flaky API. It will fail until the circuit opens.")

    # 1. Simulate initial failures to open the circuit
    for i in range(5):
        try:
            print(f"\nAttempt {i+1}: Calling the service...")
            result = circuit_breaker_manager.call(SERVICE_NAME, flaky_api_call)
            print(f"   -> Result: {result}")
        except CircuitBreakerOpen as e:
            print(f"   -> BLOCKED: {e}")
        except ConnectionError as e:
            print(f"   -> FAILED: {e}")
        
        breaker_instance = circuit_breaker_manager.get_breaker(SERVICE_NAME)
        print(f"   -> Breaker State: {breaker_instance.state}, Failures: {breaker_instance._failures}")

    # 2. Wait for the reset timeout to transition to HALF-OPEN
    print("\n--- Waiting for reset timeout (setting to 3s for demo) ---")
    breaker_instance.reset_timeout = 3
    time.sleep(3.5)

    # 3. Attempt a call in the HALF-OPEN state
    print("\nAttempting one call in HALF-OPEN state...")
    try:
        # We'll force this one to succeed to show recovery
        def always_succeeds():
            return "Recovery successful!"
            
        result = circuit_breaker_manager.call(SERVICE_NAME, always_succeeds)
        print(f"   -> Result: {result}")
    except Exception as e:
        print(f"   -> FAILED during HALF-OPEN: {e}")
    
    print(f"   -> Final Breaker State: {breaker_instance.state}, Failures: {breaker_instance._failures}")

    # 4. Show that the circuit is now closed and works again
    print("\nAttempting another call now that the circuit is closed...")
    try:
        result = circuit_breaker_manager.call(SERVICE_NAME, always_succeeds)
        print(f"   -> Result: {result}")
    except Exception as e:
        print(f"   -> FAILED: {e}")
        
    print(f"   -> Final Breaker State: {breaker_instance.state}, Failures: {breaker_instance._failures}")
