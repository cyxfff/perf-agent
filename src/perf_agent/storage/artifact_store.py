from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ArtifactStore(ABC):
    @abstractmethod
    def save_json(self, relative_path: str, payload: Any) -> Path:
        raise NotImplementedError

    @abstractmethod
    def save_text(self, relative_path: str, content: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def save_bytes(self, relative_path: str, content: bytes) -> Path:
        raise NotImplementedError
