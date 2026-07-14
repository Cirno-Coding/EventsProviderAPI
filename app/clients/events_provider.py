from typing import Any
from urllib.parse import urlparse

import httpx


class EventsProviderError(Exception):
    pass


class EventsProviderAuthError(EventsProviderError):
    pass


class EventsProviderNotFoundError(EventsProviderError):
    pass


class EventsProviderBadRequestError(EventsProviderError):
    pass


class EventsProviderClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_events_page(
        self,
        *,
        changed_at: str,
        cursor_url: str | None = None,
    ) -> dict[str, Any]:
        if cursor_url is not None:
            response = await self._client.get(self._normalize_next_url(cursor_url))
        else:
            response = await self._client.get(
                "/api/events/",
                params={"changed_at": changed_at},
            )

        return self._handle_response(response)

    async def get_available_seats(self, event_id: str) -> list[str]:
        response = await self._client.get(f"/api/events/{event_id}/seats/")
        data = self._handle_response(response)
        return list(data["seats"])

    async def register(
        self,
        *,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        response = await self._client.post(
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )
        data = self._handle_response(response)
        return str(data["ticket_id"])

    async def unregister(
        self,
        *,
        event_id: str,
        ticket_id: str,
    ) -> bool:
        response = await self._client.request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )
        data = self._handle_response(response)
        return bool(data["success"])

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code in (200, 201):
            return response.json()

        if response.status_code == 400:
            raise EventsProviderBadRequestError(response.text)

        if response.status_code == 401:
            raise EventsProviderAuthError(response.text)

        if response.status_code == 404:
            raise EventsProviderNotFoundError(response.text)

        raise EventsProviderError(response.text)

    def _normalize_next_url(self, next_url: str) -> str:
        parsed = urlparse(next_url)

        if parsed.query:
            return f"{parsed.path}?{parsed.query}"

        return parsed.path
