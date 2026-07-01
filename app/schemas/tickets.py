from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateTicketRequest(BaseModel):
    event_id: UUID
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    seat: str = Field(min_length=1, max_length=50)


class CreateTicketResponse(BaseModel):
    ticket_id: UUID


class DeleteTicketResponse(BaseModel):
    success: bool