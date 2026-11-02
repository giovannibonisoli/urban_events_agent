from typing import Optional
from pydantic import BaseModel, Field


class EventDate(BaseModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


class _GeoExtraction(BaseModel):
    place: str = Field(default="", description="Nome del centro abitato esplicitamente citato come luogo dell'evento (comune, città, paese, frazione, località). Usare '' solo se non citato.")
    county: Optional[str] = Field(default=None, description="Provincia esplicitamente menzionata nell'articolo. None se non presente.")
    street: Optional[str] = Field(default=None, description="Nome della via, piazza, strada, corso, viale, statale. None se non presente.")
    loc_description: Optional[str] = Field(default=None, description="Descrizione del luogo specifico (nome del luogo, edificio, negozio, stadio, punto di riferimento, ecc.) esplicitamente citato. None se non presente.")


class _DateExtraction(BaseModel):
    start_date: EventDate = Field(default_factory=EventDate)
    end_date: Optional[EventDate] = None


class Event(BaseModel):
    category: str
    place: str
    county: Optional[str] = None
    street: Optional[str] = None
    loc_description: Optional[str] = None

    start_date: EventDate
    end_date: Optional[EventDate] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocoded_city: Optional[str] = None
    extracted_info: Optional[dict[str, str]] = None
