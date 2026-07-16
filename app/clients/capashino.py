import httpx


class CapashinoError(Exception):
    pass


class CapashinoClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            },
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_notification(
        self,
        *,
        message: str,
        reference_id: str,
        idempotency_key: str,
    ) -> None:
        try:
            response = await self._client.post(
                "/api/notifications",
                json={
                    "message": message,
                    "reference_id": reference_id,
                    "idempotency_key": idempotency_key,
                },
            )
        except httpx.HTTPError as exc:
            raise CapashinoError("Capashino is unavailable") from exc

        if response.status_code == 201:
            return

        raise CapashinoError(
            "Capashino returned "
            f"{response.status_code}: {response.text}",
        )