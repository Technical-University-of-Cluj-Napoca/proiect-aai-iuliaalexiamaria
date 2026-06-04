from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ClauseType(str, Enum):
    penalitate = "penalitate"
    obligatie = "obligatie"
    drept = "drept"
    forta_majora = "forta_majora"
    confidentialitate = "confidentialitate"
    reziliere = "reziliere"
    date_personale = "date_personale"
    altele = "altele"


class RiskLevel(str, Enum):
    RIDICAT = "RIDICAT"
    MEDIU = "MEDIU"
    SCAZUT = "SCAZUT"
    CONFORM = "CONFORM"
    NECUNOSCUT = "NECUNOSCUT"


class PartyDTO(BaseModel):
    name: str = ""
    cui_cnp: str = ""
    address: str = ""


class SectionDTO(BaseModel):
    title: str
    start_page: int


class ClauseDTO(BaseModel):
    id: str
    section: str
    text: str
    page: int
    type: ClauseType


class DocumentMetadataDTO(BaseModel):
    title: str = ""
    page_count: int = 0
    parties: list[PartyDTO] = []
    signing_date: Optional[str] = None
    effective_date: Optional[str] = None
    value: str = ""
    duration: str = ""


class ParsedDocumentDTO(BaseModel):
    metadata: DocumentMetadataDTO
    sections: list[SectionDTO]
    clauses: list[ClauseDTO]


class RetrievalResultDTO(BaseModel):
    text: str
    source: str
    score: float


class RiskAssessmentDTO(BaseModel):
    clause_id: str
    risk_level: RiskLevel
    issues: list[str]
    references: list[str]
    context_was_empty: bool = False


class RecommendationDTO(BaseModel):
    clause_id: str
    original_text: str
    reformulated_text: str
    explanation: str
    sources: list[str]
    candidates: Optional[list[str]] = None