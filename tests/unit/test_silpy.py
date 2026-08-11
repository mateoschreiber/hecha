import json
from pathlib import Path

import pytest

from backend.application.sync_expedients import payload_hash
from backend.domain.silpy import SilpyExpedient

FIXTURES = Path(__file__).parents[1] / "fixtures" / "silpy"


def test_detail_fixture_parses_known_and_unknown_fields() -> None:
    item = SilpyExpedient.model_validate(
        json.loads((FIXTURES / "expedient-detail.json").read_text())
    )
    assert item.id_proyecto == 129338
    assert item.filed_on.isoformat() == "2021-09-01"
    assert item.authors[0].apellidos == "BUZARQUIS CÁCERES"


def test_hash_is_deterministic() -> None:
    assert payload_hash({"b": 2, "a": 1}) == payload_hash({"a": 1, "b": 2})


def test_invalid_date_is_quarantinable() -> None:
    with pytest.raises(ValueError):
        SilpyExpedient.model_validate(
            {"idProyecto": 1, "acapite": "x", "fechaIngresoExpediente": "bad"}
        )
