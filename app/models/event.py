from pydantic import BaseModel, Field


class EventDate(BaseModel):
    day: int | None = None
    month: int | None = None
    year: int | None = None


class _GeoExtraction(BaseModel):
    place: str = Field(default="", description="Nome del centro abitato esplicitamente citato come luogo dell'evento (comune, città, paese, frazione, località). Usare '' solo se non citato.")
    county: str | None = Field(default=None, description="Provincia esplicitamente menzionata nell'articolo. None se non presente.")
    street: str | None = Field(default=None, description="Nome della via, piazza, strada, corso, viale, statale. None se non presente.")
    description: str | None = Field(default=None, description="Descrizione del luogo specifico (nome del luogo, edificio, negozio, stadio, punto di riferimento, ecc.) esplicitamente citato. None se non presente.")


class _DateExtraction(BaseModel):
    start_date: EventDate = Field(default_factory=EventDate)
    end_date: EventDate | None = None


class Event(BaseModel):
    category: str
    place: str
    county: str | None = None
    street: str | None = None
    description: str | None = None

    start_date: EventDate
    end_date: EventDate | None = None

    latitude: float | None = None
    longitude: float | None = None
    geocoded_city: str | None = None
