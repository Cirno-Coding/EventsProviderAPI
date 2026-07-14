from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlaceShortResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str

    model_config = ConfigDict(from_attributes=True)


class PlaceDetailResponse(PlaceShortResponse):
    seats_pattern: str


class EventListItemResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceShortResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceDetailResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventListItemResponse]


class SeatsResponse(BaseModel):
    event_id: UUID
    available_seats: list[str]
