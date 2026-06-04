import re
import pdfplumber

from src.dtos import (
    ParsedDocumentDTO,
    DocumentMetadataDTO,
    SectionDTO,
    ClauseDTO,
    ClauseType
)


class DocumentParserAgent:

    def parse(self, pdf_path: str) -> ParsedDocumentDTO:

        sections = []
        clauses = []

        try:
            with pdfplumber.open(pdf_path) as pdf:

                page_count = len(pdf.pages)

                for page_number, page in enumerate(pdf.pages, start=1):

                    text = page.extract_text()

                    if not text:
                        continue

                    lines = text.split("\n")

                    current_section = "General"

                    for line in lines:

                        line = line.strip()

                        if not line:
                            continue

                        if re.match(
                                r"^(Articolul|Art\.|Art|Clauza)\s+\d+",
                                line,
                                re.IGNORECASE
                        ):

                            current_section = line

                            sections.append(
                                SectionDTO(
                                    title=line,
                                    start_page=page_number
                                )
                            )

                        clauses.append(
                            ClauseDTO(
                                id=f"clause_{len(clauses)+1}",
                                section=current_section,
                                text=line,
                                page=page_number,
                                type=self.classify_clause(line)
                            )
                        )

                metadata = DocumentMetadataDTO(
                    title="Contract",
                    page_count=page_count,
                    parties=[]
                )

                return ParsedDocumentDTO(
                    metadata=metadata,
                    sections=sections,
                    clauses=clauses
                )

        except Exception as e:

            print(e)

            return ParsedDocumentDTO(
                metadata=DocumentMetadataDTO(),
                sections=[],
                clauses=[]
            )

    def classify_clause(self, text: str):

        text = text.lower()

        if "penalit" in text:
            return ClauseType.penalitate

        if "confiden" in text:
            return ClauseType.confidentialitate

        if "gdpr" in text or "date personale" in text:
            return ClauseType.date_personale

        if "forta majora" in text or "forță majoră" in text:
            return ClauseType.forta_majora

        if "rezili" in text:
            return ClauseType.reziliere

        if "oblig" in text:
            return ClauseType.obligatie

        if "drept" in text:
            return ClauseType.drept

        return ClauseType.altele