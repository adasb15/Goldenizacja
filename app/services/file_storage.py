from pathlib import Path

from app.core.config import settings


class FileStorageService:
    def __init__(self) -> None:
        self.base_path = Path(settings.filestream_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_document(self, title: str, content: str) -> str:
        safe_title = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-")
        path = self.base_path / f"{safe_title}.txt"
        path.write_text(content, encoding="utf-8")
        return str(path)
