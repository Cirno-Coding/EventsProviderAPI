from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateTicketRequest(BaseModel):
    event_id: UUID
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    seat: str = Field(min_length=1, max_length=50)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("idempotency_key")
    @classmethod
    def normalize_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("idempotency_key must not be blank")

        return normalized


class CreateTicketResponse(BaseModel):
    ticket_id: UUID


class DeleteTicketResponse(BaseModel):
    success: bool
