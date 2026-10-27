"""Write the OpenAPI document to a file: `python -m vendor_intake.export_openapi ../openapi.json`.

Uses an in-memory database so exporting never touches local data.
"""

import json
import sys
import tempfile
from pathlib import Path

from vendor_intake.config import Settings
from vendor_intake.main import create_app


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    with tempfile.TemporaryDirectory() as scratch:
        app = create_app(Settings(database_url="sqlite://", storage_dir=Path(scratch)))
        target.write_text(json.dumps(app.openapi(), indent=2) + "\n")


if __name__ == "__main__":
    main()
