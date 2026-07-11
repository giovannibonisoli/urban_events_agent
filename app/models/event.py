from pydantic import BaseModel, Field


class EventDate(BaseModel):
    day: int | None = None
    month: int | None = None
    year: int | None = None


class _EventExtraction(BaseModel):
    category: str = Field(description="Tipologia dell'evento, es. 'concerto', 'furto', 'festival'")
    city: str = Field(description="Città o comune dove si svolge l'evento")
    location: str = Field(description="Luogo specifico all'interno della città, es. 'piazza Martiri', 'ModenaFiere', 'supermercato Lidl', 'via Garibaldi'. Usare la stringa vuota '' solo se l'articolo non menziona alcun luogo specifico.")

    start_date: EventDate
    end_date: EventDate | None = None


class Event(BaseModel):
    category: str
    city: str
    location: str | None = None

    start_date: EventDate
    end_date: EventDate | None = None

    latitude: float | None = None
    longitude: float | None = None
    geocoded_city: str | None = None
