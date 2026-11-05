from typing import Literal, Optional
from pydantic import BaseModel, Field



class GeoSpanExtractionResult(BaseModel):
  all_loc_span: list[str] = Field(default_factory=list)


class GeoField(BaseModel):
  value: str
  provenance: Literal["extracted", "deduced"] = "extracted"


class LocationItem(BaseModel):
  city: Optional[GeoField] = None
  hamlet: Optional[GeoField] = None
  urban_zone: Optional[GeoField] = None
  county: Optional[GeoField] = None
  address: Optional[GeoField] = None
  specific_name_place: Optional[GeoField] = None


class EventGeoExtraction(BaseModel):
  all_loc_span: list[str] = Field(default_factory=list)
  place_type: Literal["single", "intersection", "multiple"] = "single"
  luoghi: list[LocationItem] = Field(default_factory=list)