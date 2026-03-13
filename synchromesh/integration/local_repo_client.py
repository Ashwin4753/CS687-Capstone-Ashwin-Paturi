from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

class LocalRepoClient:
    """
    Local repository client for controlled demo / local-real mode.

    This client mirrors the minimal interface used by the orchestrator:
      - list_files(repo_root)
      - read_file(path)
      - write_file(path, content)

    Notes:
    - Paths returned by list_files() are relative to the selected repo root.
    - read_file() and write_file() accept those relative paths.
    - This client is intended for locally cloned repositories under target_repo/.
    """

    def __init__(self, base_path: str):
        if not base_path or not str(base_path).strip():
            raise ValueError("base_path must be a non-empty path.")

        self.base_path = Path(base_path).resolve()

        if not self.base_path.exists():
            raise FileNotFoundError(f"Local repo path does not exist: {self.base_path}")

        if not self.base_path.is_dir():
            raise NotADirectoryError(f"Local repo path is not a directory: {self.base_path}")

    async def list_files(self, repo_root: str = "") -> List[str]:
        """
        Recursively lists files under the selected local repository.

        Parameters:
        - repo_root: optional subdirectory within the selected repo

        Returns:
        - list of relative file paths using forward slashes
        """
        scan_root = self._resolve_repo_root(repo_root)

        files: List[str] = []
        for root, dirs, filenames in os.walk(scan_root):
            # Skip common noisy directories
            dirs[:] = [
                d for d in dirs
                if d not in {
                    ".git",
                    "node_modules",
                    ".next",
                    ".turbo",
                    ".cache",
                    "dist",
                    "build",
                    "__pycache__",
                    ".venv",
                    "venv",
                }
            ]

            for filename in filenames:
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(scan_root).as_posix()
                files.append(rel_path)

        files.sort()
        return files

    async def read_file(self, path: str) -> str:
        """
        Reads a local file using a path relative to the selected repo root.
        """
        file_path = self._resolve_relative_file(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {file_path}")

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback for odd encodings
            return file_path.read_text(encoding="utf-8", errors="replace")

    async def write_file(self, path: str, content: str) -> None:
        """
        Writes content to a local file using a path relative to the selected repo root.
        Creates parent directories if needed.
        """
        file_path = self._resolve_relative_file(path)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def set_repo(self, owner: str, repo: str) -> None:
        """
        Compatibility shim for code paths that expect GitHub-style clients.
        Not used for local repo access, but kept to avoid interface mismatch.
        """
        return

    def _resolve_repo_root(self, repo_root: str) -> Path:
        """
        Resolves an optional subfolder inside the selected repo.
        """
        normalized = str(repo_root or "").strip()

        if normalized in {"", ".", "./", "/"}:
            return self.base_path

        candidate = (self.base_path / normalized).resolve()

        if not str(candidate).startswith(str(self.base_path)):
            raise ValueError("repo_root escapes the base repository path.")

        if not candidate.exists():
            raise FileNotFoundError(f"repo_root does not exist: {candidate}")

        if not candidate.is_dir():
            raise NotADirectoryError(f"repo_root is not a directory: {candidate}")

        return candidate

    def _resolve_relative_file(self, relative_path: str) -> Path:
        """
        Resolves a file path relative to the selected repo root.
        """
        if not relative_path or not str(relative_path).strip():
            raise ValueError("relative file path must be a non-empty string.")

        normalized = str(relative_path).replace("\\", "/").lstrip("./")
        candidate = (self.base_path / normalized).resolve()

        if not str(candidate).startswith(str(self.base_path)):
            raise ValueError("file path escapes the base repository path.")

        return candidate