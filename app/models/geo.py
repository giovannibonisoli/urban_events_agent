from typing import Literal, Optional
from pydantic import BaseModel, Field


# 1. Risultato del primo agente: GEO SPAN EXTRACTOR
class GeoSpanExtractionResult(BaseModel):
  all_loc_span: list[str] = Field(default_factory=list)


# 2. Struttura del singolo attributo geografico con Provenance
class GeoField(BaseModel):
  value: str
  provenance: Literal["extracted", "deduced"] = "extracted"


# 3. Dettaglio dei campi specifici per un luogo
class LocationItem(BaseModel):
  city: Optional[str] = None
  hamlet: Optional[str] = None
  urban_zone: Optional[str] = None
  county: Optional[str] = None
  address: Optional[str] = None
  specific_name_place: Optional[str] = None


# 4. Risultato del secondo agente: GEO STRUCTURER
class EventGeoExtraction(BaseModel):
  # Allineato alle linee guida: "single", "intersection", "disjoint" (o "disgiunto" / "intersezione" / "singolo")
  place_type: Literal["single", "intersection", "disjoint"] = "single"
  places: list[LocationItem] = Field(default_factory=list)