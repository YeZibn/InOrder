"""Bounded, per-worker admission for workflow and dependency calls."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any, Awaitable, Callable, Optional

from ..infrastructure.llm.errors import WorkflowOverloadedError, WorkflowTimeoutError
from .runtime import WorkflowRuntimeConfig


class CapacityLease:
    def __init__(self, gate: "CapacityGate"):
        self._gate = gate
        self._released = False

    async def release(self) -> None:
        if not self._released:
            self._released = True
            # A second cancellation must not strand the permit after the flag
            # has been set, even if this coroutine is interrupted at await.
            await asyncio.shield(self._gate._release())


class CapacityGate:
    def __init__(self, limit: int, max_waiting: int, wait_seconds: float):
        self.limit = limit
        self.max_waiting = max_waiting
        self.wait_seconds = wait_seconds
        self.active = 0
        self.waiting = 0
        self._condition = asyncio.Condition()

    async def acquire(
        self,
        deadline_at: Optional[float] = None,
        disconnected: Optional[Callable[[], Awaitable[bool]]] = None,
        deadline_is_overload: bool = False,
    ) -> CapacityLease:
        wait_end = time.monotonic() + self.wait_seconds
        async with self._condition:
            if deadline_at is not None and time.monotonic() >= deadline_at:
                self._deadline_error(deadline_is_overload)
            if self.active < self.limit and self.waiting == 0:
                self.active += 1
                return CapacityLease(self)
            if self.waiting >= self.max_waiting:
                raise WorkflowOverloadedError("capacity wait queue is full")
            self.waiting += 1
            try:
                while self.active >= self.limit:
                    now = time.monotonic()
                    if deadline_at is not None and now >= deadline_at:
                        self._deadline_error(deadline_is_overload)
                    if now >= wait_end:
                        raise WorkflowOverloadedError("capacity wait timed out")
                    if disconnected is not None and await disconnected():
                        raise asyncio.CancelledError()
                    remaining = min(wait_end - now, (deadline_at - now) if deadline_at is not None else self.wait_seconds)
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout=min(remaining, 0.1))
                    except asyncio.TimeoutError:
                        pass
                if disconnected is not None and await disconnected():
                    raise asyncio.CancelledError()
                if deadline_at is not None and time.monotonic() >= deadline_at:
                    self._deadline_error(deadline_is_overload)
                self.active += 1
                return CapacityLease(self)
            finally:
                self.waiting -= 1
                if self.active < self.limit and self.waiting:
                    self._condition.notify(1)

    async def _release(self) -> None:
        async with self._condition:
            self.active -= 1
            if self.active < 0:
                raise RuntimeError("capacity gate released too many times")
            self._condition.notify(1)

    @staticmethod
    def _deadline_error(as_overload: bool) -> None:
        if as_overload:
            raise WorkflowOverloadedError("capacity wait exceeded workflow deadline")
        raise WorkflowTimeoutError("workflow deadline exceeded while waiting for capacity")


class BoundedExecutor:
    """Submit only when a thread slot is free; count work until it really ends."""

    def __init__(self, workers: int, max_waiting: int, wait_seconds: float, name: str):
        self.gate = CapacityGate(workers, max_waiting, wait_seconds)
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix=name)

    async def run(self, operation: Callable[..., Any], *args: Any, deadline_at: Optional[float] = None, additional_gate: Optional[CapacityGate] = None) -> Any:
        lease = await self.gate.acquire(deadline_at=deadline_at)
        extra_lease = None
        try:
            if additional_gate is not None:
                extra_lease = await additional_gate.acquire(deadline_at=deadline_at)
            future = self._executor.submit(operation, *args)
        except BaseException:
            if extra_lease is not None:
                await extra_lease.release()
            await lease.release()
            raise
        loop = asyncio.get_running_loop()

        def on_finished(_future) -> None:
            # The concurrent future completes only after its worker exits (or
            # before it starts if cancellation succeeds). The awaiting coroutine
            # can be cancelled earlier and must not release the slot itself.
            try:
                async def release_all():
                    if extra_lease is not None:
                        await extra_lease.release()
                    await lease.release()
                loop.call_soon_threadsafe(lambda: loop.create_task(release_all()))
            except RuntimeError:
                pass  # The event loop has already shut down with this worker.

        future.add_done_callback(on_finished)
        return await asyncio.wrap_future(future)

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class WorkerCapacity:
    """All limits owned by one API worker and one event loop."""

    def __init__(self, config: WorkflowRuntimeConfig):
        self.workflow = CapacityGate(config.max_concurrency, config.max_waiting, config.queue_timeout_seconds)
        self.llm = CapacityGate(config.llm_max_concurrency, config.max_concurrency, config.queue_timeout_seconds)
        self.sync_nodes = BoundedExecutor(config.max_concurrency, config.max_concurrency, config.queue_timeout_seconds, "inorder-node")
        self.langextract = BoundedExecutor(config.langextract_max_threads, config.max_concurrency, config.queue_timeout_seconds, "inorder-langextract")

    def close(self) -> None:
        self.sync_nodes.close()
        self.langextract.close()
