"""
Resilience & Recovery Service

Implements circuit breakers, retries, timeouts, and recovery strategies.
Ensures system stability and graceful degradation.
"""

import logging
from typing import Callable, Any, Optional, List, TypeVar, Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, config: CircuitBreakerConfig = CircuitBreakerConfig()):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.call_count = 0
        self.failure_rate = 0.0

    async def call(self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker attempting reset")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.call_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker closed - recovered")

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.call_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.call_count > 0:
            self.failure_rate = self.failure_count / self.call_count

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error("Circuit breaker opened due to failures")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout_seconds

    def get_state(self) -> dict:
        """Get circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_rate": self.failure_rate,
            "call_count": self.call_count,
        }


class RetryConfig:
    """Retry configuration."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 10000,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay_ms(self, attempt: int) -> int:
        """Calculate delay for attempt."""
        delay = self.initial_delay_ms * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay_ms)

        if self.jitter:
            # Add random jitter
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)

        return int(delay)


class RetryPolicy:
    """Retry policy implementation."""

    def __init__(self, config: RetryConfig = RetryConfig()):
        self.config = config
        self.attempt_count = 0
        self.last_error: Optional[Exception] = None

    async def execute(self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with retry logic."""
        self.attempt_count = 0

        for attempt in range(self.config.max_attempts):
            self.attempt_count = attempt + 1

            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                self.last_error = e

                if attempt < self.config.max_attempts - 1:
                    delay_ms = self.config.get_delay_ms(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay_ms}ms: {e}"
                    )
                    await asyncio.sleep(delay_ms / 1000)
                else:
                    logger.error(
                        f"All {self.config.max_attempts} attempts failed: {e}"
                    )
                    raise


class TimeoutHandler:
    """Timeout handling."""

    @staticmethod
    async def execute_with_timeout(
        fn: Callable[..., Awaitable[T]],
        timeout_seconds: float,
        *args,
        **kwargs,
    ) -> T:
        """Execute function with timeout."""
        try:
            return await asyncio.wait_for(
                fn(*args, **kwargs),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {timeout_seconds}s")
            raise


class BulkheadPattern:
    """Bulkhead pattern for resource isolation."""

    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
        self.max_concurrent = max_concurrent

    async def execute(self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with bulkhead protection."""
        async with self.semaphore:
            self.active_count += 1
            try:
                return await fn(*args, **kwargs)
            finally:
                self.active_count -= 1

    def get_status(self) -> dict:
        """Get bulkhead status."""
        return {
            "active_count": self.active_count,
            "max_concurrent": self.max_concurrent,
            "utilization": self.active_count / self.max_concurrent,
        }


class ResilientClient:
    """Client with built-in resilience patterns."""

    def __init__(
        self,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout_seconds: float = 30,
        max_concurrent: int = 10,
    ):
        self.circuit_breaker = CircuitBreaker(
            circuit_breaker_config or CircuitBreakerConfig()
        )
        self.retry_policy = RetryPolicy(retry_config or RetryConfig())
        self.timeout_seconds = timeout_seconds
        self.bulkhead = BulkheadPattern(max_concurrent)
        self.call_metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "timeout_calls": 0,
        }

    async def call(self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Call function with all resilience patterns."""
        self.call_metrics["total_calls"] += 1

        try:
            # Apply bulkhead, then circuit breaker, then retry, then timeout
            return await self.bulkhead.execute(
                self._call_with_resilience,
                fn,
                *args,
                **kwargs,
            )
        except asyncio.TimeoutError:
            self.call_metrics["timeout_calls"] += 1
            raise
        except Exception:
            self.call_metrics["failed_calls"] += 1
            raise

    async def _call_with_resilience(
        self, fn: Callable[..., Awaitable[T]], *args, **kwargs
    ) -> T:
        """Internal call with circuit breaker, retry, and timeout."""
        async def safe_call():
            return await TimeoutHandler.execute_with_timeout(
                fn, self.timeout_seconds, *args, **kwargs
            )

        try:
            result = await self.circuit_breaker.call(self.retry_policy.execute, safe_call)
            self.call_metrics["successful_calls"] += 1
            return result
        except Exception:
            raise

    def get_metrics(self) -> dict:
        """Get client metrics."""
        metrics = {
            "call_metrics": self.call_metrics,
            "circuit_breaker": self.circuit_breaker.get_state(),
            "bulkhead": self.bulkhead.get_status(),
        }

        if self.call_metrics["total_calls"] > 0:
            metrics["success_rate"] = (
                self.call_metrics["successful_calls"]
                / self.call_metrics["total_calls"]
            )

        return metrics


@dataclass
class FailureRecoveryStrategy:
    """Strategy for recovering from failures."""
    name: str
    description: str
    actions: List[str]
    timeout_minutes: int


class FailureRecoveryOrchestrator:
    """Orchestrates recovery from failures."""

    def __init__(self):
        self.recovery_strategies: dict[str, FailureRecoveryStrategy] = {}
        self.active_recoveries: dict[str, datetime] = {}

    def register_strategy(self, strategy: FailureRecoveryStrategy) -> None:
        """Register recovery strategy."""
        self.recovery_strategies[strategy.name] = strategy
        logger.info(f"Recovery strategy registered: {strategy.name}")

    async def recover(self, failure_type: str) -> bool:
        """Attempt recovery."""
        if failure_type not in self.recovery_strategies:
            logger.error(f"No recovery strategy for: {failure_type}")
            return False

        strategy = self.recovery_strategies[failure_type]
        logger.info(f"Executing recovery strategy: {strategy.name}")

        try:
            for action in strategy.actions:
                logger.info(f"Executing recovery action: {action}")
                # Execute recovery actions
                await asyncio.sleep(0.1)

            self.active_recoveries[failure_type] = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False

    def get_recovery_status(self) -> dict:
        """Get recovery status."""
        return {
            "active_recoveries": len(self.active_recoveries),
            "strategies": list(self.recovery_strategies.keys()),
            "recoveries": {
                k: v.isoformat() for k, v in self.active_recoveries.items()
            },
        }
