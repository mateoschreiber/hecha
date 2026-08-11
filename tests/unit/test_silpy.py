import json
from pathlib import Path

import pytest

from backend.application.sync_expedients import payload_hash
from backend.domain.silpy import SilpyExpedient
from backend.infrastructure.silpy_portal_client import SilpyPortalClient

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


def test_portal_detail_parser_extracts_public_relations() -> None:
    document = """
    <div id="formMain:tabDetalle:tabDocumentos"><span class="textCourier"> LEY.pdf</span>
    <span class="textoFileSize">2 MB</span>
    https://silpy.congreso.gov.py/web/descarga/expediente-77</div>
    <div id="formMain:tabDetalle:tabAutores"><a href="/web/legislador/42">Ana Pérez</a>
    <span class="font-italic">ANR</span></div>
    <div id="formMain:tabDetalle:tabEvolucion"></div>
    """
    detail = SilpyPortalClient()._parse_detail(document)
    assert detail["listaAutores"] == [
        {"idParlamentario": 42, "nombres": "Ana Pérez", "apellidos": "", "partidoPolitico": "ANR"}
    ]
    assert detail["archivosAdjuntos"][0]["infoAdjunto"] == "LEY.pdf · 2 MB"
