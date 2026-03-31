from __future__ import annotations

import time
from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def timed() -> Iterator[float]:
    start = time.perf_counter()
    try:
        yield start
    finally:
        _ = time.perf_counter() - start
