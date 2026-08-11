from __future__ import annotations

import html
import re
from calendar import monthrange
from datetime import date

import httpx

from backend.domain.silpy import SilpyExpedient

BASE_URL = "https://silpy.congreso.gov.py"
FORM_PATH = "/web/expedientesavanzado"


class SilpyUnavailable(RuntimeError):
    """The official SILpy portal cannot satisfy the current request."""


def _text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).strip()


def _parse_date(value: str) -> date | None:
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
    if match:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    spanish = re.search(r"(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{4})", value.upper())
    months = {
        "ENERO": 1,
        "FEBRERO": 2,
        "MARZO": 3,
        "ABRIL": 4,
        "MAYO": 5,
        "JUNIO": 6,
        "JULIO": 7,
        "AGOSTO": 8,
        "SETIEMBRE": 9,
        "SEPTIEMBRE": 9,
        "OCTUBRE": 10,
        "NOVIEMBRE": 11,
        "DICIEMBRE": 12,
    }
    if spanish and spanish.group(2) in months:
        return date(int(spanish.group(3)), months[spanish.group(2)], int(spanish.group(1)))
    return None


class SilpyPortalClient:
    """JSF search adapter for the current SILpy portal."""

    def __init__(self, timeout: float = 20) -> None:
        self.timeout = timeout

    PERIODS = {
        "2023-2028": (date(2023, 7, 1), date(2028, 6, 30)),
        "2018-2023": (date(2018, 7, 1), date(2023, 6, 30)),
    }

    @classmethod
    def ranges(cls, period: str) -> list[tuple[date, date]]:
        """Monthly windows avoid the portal's 100-result JSF paginator limit."""
        if period not in cls.PERIODS:
            raise ValueError("unsupported legislative period")
        start, end = cls.PERIODS[period]
        windows: list[tuple[date, date]] = []
        cursor = start
        while cursor <= end:
            last = date(cursor.year, cursor.month, monthrange(cursor.year, cursor.month)[1])
            windows.append((cursor, min(last, end)))
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        return windows

    async def list_range(
        self, client: httpx.AsyncClient, since: date, until: date
    ) -> list[SilpyExpedient]:
        for attempt in range(3):
            try:
                form = await client.get(FORM_PATH)
                form.raise_for_status()
                action_match = re.search(r'<form id="formMain"[^>]+action="([^"]+)', form.text)
                state_match = re.search(
                    r'name="jakarta.faces.ViewState"[^>]+value="([^"]+)', form.text
                )
                if not action_match or not state_match:
                    raise SilpyUnavailable("SILpy JSF form contract changed")
                response = await client.post(
                    html.unescape(action_match.group(1)),
                    data={
                        "formMain": "formMain",
                        "formMain:j_idt56": "A",
                        "formMain:desde_input": since.strftime("%d/%m/%Y"),
                        "formMain:hasta_input": until.strftime("%d/%m/%Y"),
                        "formMain:cmdBuscar": "",
                        "jakarta.faces.ViewState": state_match.group(1),
                    },
                )
                response.raise_for_status()
                return self._parse_results(response.text)
            except (httpx.HTTPError, SilpyUnavailable) as error:
                if attempt == 2:
                    raise SilpyUnavailable(f"SILpy portal unavailable: {error}") from error
                await __import__("asyncio").sleep(0.5 * (2**attempt))
        return []

    async def list_period(self, period: str) -> list[SilpyExpedient]:
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=self.timeout, follow_redirects=True
        ) as client:
            records: list[SilpyExpedient] = []
            for since, until in self.ranges(period):
                records.extend(await self.list_range(client, since, until))
            return records

    async def enrich_expedient(
        self, client: httpx.AsyncClient, item: SilpyExpedient
    ) -> SilpyExpedient:
        """Merge authors and public documents from SILpy's detail page.

        The advanced search intentionally omits these relations. This method is
        invoked by the worker only, never from a visitor request.
        """
        response = await client.get(f"/web/expediente/{item.id_proyecto}")
        response.raise_for_status()
        payload = item.model_dump(by_alias=True, mode="json") | self._parse_detail(response.text)
        return SilpyExpedient.model_validate(payload)

    async def list_sessions(self) -> list[dict[str, object]]:
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=self.timeout, follow_redirects=True
        ) as client:
            response = await client.get("/web/sesiones")
            response.raise_for_status()
        rows: list[dict[str, object]] = []
        for source_id, title in re.findall(
            r'href="https://silpy\.congreso\.gov\.py/web/sesion/(\d+)"[^>]*>(.*?)</a>',
            response.text,
            re.DOTALL,
        ):
            clean = _text(title)
            rows.append(
                {
                    "source_id": source_id,
                    "title": clean,
                    "held_on": _parse_date(clean),
                    "source_url": f"{BASE_URL}/web/sesion/{source_id}",
                }
            )
        return rows

    async def list_votes(self) -> list[dict[str, object]]:
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=self.timeout, follow_redirects=True
        ) as client:
            response = await client.get("/web/pages/ListarVotacion.xhtml")
            response.raise_for_status()
        rows: list[dict[str, object]] = []
        for row in re.findall(r'<tr data-ri="\d+".*?</tr>', response.text, re.DOTALL):
            vote = re.search(
                r'/web/votacion/(\d+)"[^>]*>\s*<span[^>]*>(.*?)</span>', row, re.DOTALL
            )
            if not vote:
                continue
            result = re.search(r"insignia[^>]*>(.*?)</span>", row, re.DOTALL)
            session_ref = re.search(r"/web/sesion/(\d+)", row)
            expedient_ref = re.search(r"/web/expediente/(\d+)", row)
            rows.append(
                {
                    "source_id": vote.group(1),
                    "motion": _text(vote.group(2)),
                    "result": _text(result.group(1)) if result else None,
                    "voted_on": _parse_date(_text(row)),
                    "session_source_id": session_ref.group(1) if session_ref else None,
                    "expedient_source_id": expedient_ref.group(1) if expedient_ref else None,
                    "source_url": f"{BASE_URL}/web/votacion/{vote.group(1)}",
                }
            )
        return rows

    async def list_legislators(self) -> list[dict[str, object]]:
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=self.timeout, follow_redirects=True
        ) as client:
            response = await client.get("/web/parlamentarios")
            response.raise_for_status()
        rows: list[dict[str, object]] = []
        pattern = r'/web/legislador/(\d+)"[^>]*>(.*?)</a>\s*<span[^>]*>(.*?)</span>'
        for source_id, name, chamber in re.findall(pattern, response.text, re.DOTALL):
            rows.append(
                {
                    "source_id": source_id,
                    "full_name": _text(name),
                    "chamber": "CAMARA DE SENADORES"
                    if "Senador" in _text(chamber)
                    else "CAMARA DE DIPUTADOS",
                    "profile_url": f"{BASE_URL}/web/legislador/{source_id}",
                }
            )
        return rows

    async def list_commission_meetings(self) -> list[dict[str, object]]:
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=self.timeout, follow_redirects=True
        ) as client:
            response = await client.get("/web/comisiones/reuniones")
            response.raise_for_status()
        rows: list[dict[str, object]] = []
        for row in re.findall(r'<tr data-ri="\d+".*?</tr>', response.text, re.DOTALL):
            link = re.search(r'/web/comision/reunion/(\d+)"[^>]*title="([^"]+)', row)
            cells = [_text(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)]
            if not link or len(cells) < 3:
                continue
            rows.append(
                {
                    "source_id": link.group(1),
                    "name": cells[2].split("PERMANENTE")[0].strip(),
                    "commission_type": "PERMANENTE" if "PERMANENTE" in cells[2] else None,
                    "chamber": "CAMARA DE SENADORES"
                    if "SENADORES" in cells[2]
                    else "CAMARA DE DIPUTADOS",
                    "source_url": f"{BASE_URL}/web/comision/reunion/{link.group(1)}",
                }
            )
        return rows

    def _parse_results(self, document: str) -> list[SilpyExpedient]:
        items: list[SilpyExpedient] = []
        for row in re.findall(r'<tr data-ri="\d+".*?</tr>', document, flags=re.DOTALL):
            cells = [
                _text(value) for value in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.DOTALL)
            ]
            link = re.search(
                r'href="https://silpy\.congreso\.gov\.py/web/expediente/(\d+)"[^>]*>(.*?)</a>',
                row,
                re.DOTALL,
            )
            if len(cells) < 9 or not link:
                continue
            try:
                items.append(
                    SilpyExpedient.model_validate(
                        {
                            "idProyecto": link.group(1),
                            "expedienteCamara": cells[2],
                            "acapite": _text(link.group(2)),
                            "fechaIngresoExpediente": cells[3],
                            "estadoProyecto": cells[4],
                            "tipoProyecto": cells[5],
                            "iniciativa": cells[6],
                            "descripcionEtapa": cells[7],
                            "origenProyecto": cells[8],
                            "appURL": f"{BASE_URL}/web/expediente/{link.group(1)}",
                        }
                    )
                )
            except ValueError:
                continue
        return items

    @staticmethod
    def _section(document: str, section_id: str) -> str:
        match = re.search(
            rf'<div id="formMain:tabDetalle:{section_id}".*?'
            r'(?=<div id="formMain:tabDetalle:tab(?:Autores|Evolucion)"'
            r'|<input id="formMain:tabDetalle_activeIndex")',
            document,
            re.DOTALL,
        )
        return match.group(0) if match else ""

    def _parse_detail(self, document: str) -> dict[str, object]:
        authors: list[dict[str, object]] = []
        authors_section = self._section(document, "tabAutores")
        author_pattern = r'/web/legislador/(\d+)"[^>]*>(.*?)</a>.*?font-italic[^>]*>(.*?)</span>'
        for source_id, name, party in re.findall(author_pattern, authors_section, re.DOTALL):
            authors.append(
                {
                    "idParlamentario": int(source_id),
                    "nombres": _text(name),
                    "apellidos": "",
                    "partidoPolitico": _text(party),
                }
            )

        attachments: list[dict[str, object]] = []
        documents_section = self._section(document, "tabDocumentos")
        attachment_pattern = (
            r'textCourier[^>]*>\s*(.*?)</span>(.{0,2500}?)'
            r'https?://silpy\.congreso\.gov\.py/web/descarga/expediente-(\d+)'
        )
        for filename, fragment, source_id in re.findall(
            attachment_pattern, documents_section, re.DOTALL
        ):
            size = re.search(r'textoFileSize[^>]*>(.*?)</span>', fragment, re.DOTALL)
            parts = [_text(filename), *([_text(size.group(1))] if size else [])]
            attachments.append(
                {
                    "idAdjunto": int(source_id),
                    "appURL": f"{BASE_URL}/web/descarga/expediente-{source_id}",
                    "infoAdjunto": " · ".join(parts) or "Documento de iniciativa",
                    "tipoArchivo": "application/pdf",
                }
            )
        return {"listaAutores": authors, "archivosAdjuntos": attachments}
