from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ElementType(StrEnum):
    TEXT_BOX = "text_box"
    IMAGE = "image"
    CHART = "chart"
    TABLE = "table"
    SHAPE = "shape"
    GROUP = "group"
    OTHER = "other"


class ElementFeature(BaseModel):
    element_type: ElementType
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)
    font_size: float | None = None
    bold: bool | None = None
    alignment: str | None = None
    fill_color: str | None = None
    character_count: int | None = Field(default=None, ge=0)
    table_rows: int | None = Field(default=None, ge=1)
    table_columns: int | None = Field(default=None, ge=1)


class SlideStructure(BaseModel):
    slide_number: int = Field(ge=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    elements: list[ElementFeature]
    structural_description: str
    preview_url: str | None = None


class PresentationAnalysis(BaseModel):
    filename: str
    slide_count: int
    slides: list[SlideStructure]


class DesignMatch(BaseModel):
    template_id: UUID
    name: str
    source_filename: str
    slide_number: int
    similarity: float
    preview_url: str | None = None
    download_url: str
    is_fallback: bool = False


class UploadResponse(BaseModel):
    presentation_id: UUID
    analysis: PresentationAnalysis
    matches: dict[int, list[DesignMatch]] = {}


class HealthResponse(BaseModel):
    status: str
    database: str
    groq_configured: bool
    reference_directory: str
