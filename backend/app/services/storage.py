import os
import uuid
import pathlib
from abc import ABC, abstractmethod
from typing import Tuple

STORAGE_BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "storage"


class BaseStorageService(ABC):
    """
    Abstract Storage Interface to allow seamless migration to cloud storage (S3/GCS) in future phases.
    """
    @abstractmethod
    def save_file(self, file_bytes: bytes, filename: str, category: str) -> Tuple[str, int]:
        """
        Saves file bytes to storage under category subfolder (e.g. 'candidates' or 'jobs').
        Returns tuple of (relative_or_absolute_file_path, file_size_in_bytes).
        """
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> bytes:
        """
        Retrieves file bytes from storage given a file path.
        """
        pass


class LocalStorageService(BaseStorageService):
    """
    Local filesystem implementation of storage service.
    Stores files in backend/storage/{category}/ directory with UUID prefix.
    """
    def __init__(self, base_dir: pathlib.Path = STORAGE_BASE_DIR):
        self.base_dir = base_dir

    def save_file(self, file_bytes: bytes, filename: str, category: str = "candidates") -> Tuple[str, int]:
        category_dir = self.base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename & prefix with UUID to ensure uniqueness
        safe_filename = pathlib.Path(filename).name
        unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
        target_path = category_dir / unique_filename

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        file_size = len(file_bytes)
        relative_path = str(target_path.relative_to(self.base_dir.parent))
        return relative_path, file_size

    def get_file(self, file_path: str) -> bytes:
        full_path = self.base_dir.parent / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found at path: {file_path}")
        with open(full_path, "rb") as f:
            return f.read()


storage_service = LocalStorageService()
