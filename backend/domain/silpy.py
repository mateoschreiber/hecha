from __future__ import annotations

import unicodedata
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_text(value: str | None) -> str | None:
    """Normalize public SILpy labels without changing their meaning.

    SILpy returns the same labels with inconsistent casing, accents and whitespace.
    Keeping a single canonical value is essential because these fields power filters,
    catalogues and dashboard aggregates.
    """
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def normalize_label(value: str | None) -> str | None:
    cleaned = normalize_text(value)
    if cleaned is None:
        return None
    return unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode().upper()


def normalize_chamber(value: str | None) -> str | None:
    label = normalize_label(value)
    if label is None:
        return None
    if "DIPUT" in label:
        return "CAMARA DE DIPUTADOS"
    if "SENAD" in label:
        return "CAMARA DE SENADORES"
    return label


def normalize_status(value: str | None) -> str | None:
    return normalize_label(value)


def normalize_project_type(value: str | None) -> str | None:
    return normalize_label(value)


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

    @field_validator(
        "number", "title", "source_url", "initiative", "stage", "substage", "urgency", mode="before"
    )
    @classmethod
    def normalize_public_text(cls, value: Any) -> str | None:
        return normalize_text(str(value)) if value is not None else None

    @field_validator("chamber", mode="before")
    @classmethod
    def normalize_public_chamber(cls, value: Any) -> str | None:
        return normalize_chamber(str(value)) if value is not None else None

    @field_validator("status", "project_type", mode="before")
    @classmethod
    def normalize_public_labels(cls, value: Any, info: Any) -> str | None:
        if value is None:
            return None
        if info.field_name == "status":
            return normalize_status(str(value))
        return normalize_project_type(str(value))
