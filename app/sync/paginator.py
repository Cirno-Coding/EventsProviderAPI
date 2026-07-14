from collections.abc import AsyncIterator
from typing import Any, Protocol


class EventsProviderClientProtocol(Protocol):
    async def get_events_page(
        self,
        *,
        changed_at: str,
        cursor_url: str | None = None,
    ) -> dict[str, Any]:
        pass


class EventsPaginator:
    def __init__(
        self,
        *,
        client: EventsProviderClientProtocol,
        changed_at: str,
    ) -> None:
        self._client = client
        self._changed_at = changed_at

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        next_url: str | None = None

        while True:
            page = await self._client.get_events_page(
                changed_at=self._changed_at,
                cursor_url=next_url,
            )

            for event in page["results"]:
                yield event

            next_url = page.get("next")

            if next_url is None:
                break
