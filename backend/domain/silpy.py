from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SilpyAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")
    id_parlamentario: int = Field(alias="idParlamentario")
    nombres: str = ""
    apellidos: str = ""
    partido_politico: str | None = Field(default=None, alias="partidoPolitico")
    camara: str | None = Field(default=None, alias="camaraParlamentario")


class SilpyAttachment(BaseModel):
    model_config = ConfigDict(extra="allow")
    id_adjunto: int = Field(alias="idAdjunto")
    url: str | None = Field(default=None, alias="appURL")
    info: str | None = Field(default=None, alias="infoAdjunto")
    mime_type: str | None = Field(default=None, alias="tipoArchivo")


class SilpyExpedient(BaseModel):
    """Tolerant source model; unknown fields remain available in raw payload."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id_proyecto: int = Field(alias="idProyecto")
    number: str | None = Field(default=None, alias="expedienteCamara")
    title: str = Field(alias="acapite")
    source_url: str | None = Field(default=None, alias="appURL")
    project_type: str | None = Field(default=None, alias="tipoProyecto")
    chamber: str | None = Field(default=None, alias="origenProyecto")
    initiative: str | None = Field(default=None, alias="iniciativa")
    status: str | None = Field(default=None, alias="estadoProyecto")
    stage: str | None = Field(default=None, alias="descripcionEtapa")
    substage: str | None = Field(default=None, alias="descripcionSubEtapa")
    urgency: str | None = Field(default=None, alias="urgencia")
    filed_on: date | None = Field(default=None, alias="fechaIngresoExpediente")
    authors: list[SilpyAuthor] = Field(default_factory=list, alias="listaAutores")
    attachments: list[SilpyAttachment] = Field(default_factory=list, alias="archivosAdjuntos")
    committees_text: str | None = Field(default=None, alias="giradosComision")

    @field_validator("filed_on", mode="before")
    @classmethod
    def parse_silpy_date(cls, value: Any) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            parsed = value
        else:
            parsed = date.fromisoformat("-".join(reversed(str(value).split("/"))))
        if not 2007 <= parsed.year <= date.today().year + 1:
            raise ValueError("fecha SILpy fuera de rango")
        return parsed
