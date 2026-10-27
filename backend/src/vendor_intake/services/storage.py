from pathlib import Path


class LocalStorage:
    """Stores uploads at <root>/<tenant_id>/<document_id>; user filenames never reach the path."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, tenant_id: str, document_id: str, data: bytes) -> str:
        path = self.root / tenant_id / document_id
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()
