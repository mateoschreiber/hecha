from __future__ import annotations

import json
from pathlib import Path

from apps.api.app.main import app

snapshot = Path("packages/contracts/openapi.json")
expected = json.loads(snapshot.read_text())
actual = app.openapi()
if actual != expected:
    raise SystemExit("OpenAPI changed: regenerate packages/contracts/openapi.json intentionally.")
