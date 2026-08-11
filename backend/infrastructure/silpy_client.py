from __future__ import annotations

import asyncio
import random
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from backend.domain.silpy import SilpyExpedient
from backend.infrastructure.config import Settings, get_settings


class SilpyUnavailable(RuntimeError):
    pass


class SilpyClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.failures = 0
        self.open_until: datetime | None = None

    def _check_circuit(self) -> None:
        if self.open_until and datetime.now(UTC) < self.open_until:
            raise SilpyUnavailable("SILpy circuit is open")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._check_circuit()
        for attempt in range(self.settings.silpy_max_attempts):
            try:
                async with httpx.AsyncClient(
                    base_url=self.settings.silpy_base_url,
                    timeout=self.settings.silpy_timeout_seconds,
                ) as client:
                    response = await client.get(path, params=params)
                    response.raise_for_status()
                    self.failures = 0
                    return response.json()
            except (httpx.HTTPError, ValueError) as error:
                if attempt + 1 == self.settings.silpy_max_attempts:
                    self.failures += 1
                    if self.failures >= 3:
                        self.open_until = datetime.now(UTC) + timedelta(minutes=5)
                    raise SilpyUnavailable("SILpy request failed") from error
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.5))
        raise AssertionError("unreachable")

    async def list_expedients(self, page: int) -> Sequence[SilpyExpedient]:
        data = await self._get(
            "/data/proyecto", {"offset": page, "limit": self.settings.silpy_page_size}
        )
        return [SilpyExpedient.model_validate(item) for item in data]

    async def get_expedient(self, source_id: int) -> SilpyExpedient:
        return SilpyExpedient.model_validate(await self._get(f"/data/proyecto/{source_id}/detalle"))
