import re
import traceback

import pdfplumber

from src.dtos import (
    ParsedDocumentDTO,
    DocumentMetadataDTO,
    SectionDTO,
    ClauseDTO,
    ClauseType,
)


class DocumentParserAgent:
    def parse(self, pdf_path: str) -> ParsedDocumentDTO:
        sections = []
        clauses = []
        full_text = ""

        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)

                current_section = "General"
                current_clause_lines = []
                current_clause_page = 1

                for page_number, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""

                    if not text.strip():
                        continue

                    full_text += text + "\n"

                    lines = text.split("\n")

                    for line in lines:
                        line = self.clean_line(line)

                        if not line:
                            continue

                        if self.is_section_title(line):
                            if current_clause_lines:
                                clause_text = " ".join(current_clause_lines).strip()

                                clauses.append(
                                    ClauseDTO(
                                        id=f"clause_{len(clauses) + 1}",
                                        section=current_section,
                                        text=clause_text,
                                        page=current_clause_page,
                                        type=self.classify_clause(clause_text),
                                    )
                                )

                                current_clause_lines = []

                            current_section = line

                            sections.append(
                                SectionDTO(
                                    title=line,
                                    start_page=page_number,
                                )
                            )

                            current_clause_page = page_number
                            continue

                        if self.is_clause_start(line):
                            if current_clause_lines:
                                clause_text = " ".join(current_clause_lines).strip()

                                clauses.append(
                                    ClauseDTO(
                                        id=f"clause_{len(clauses) + 1}",
                                        section=current_section,
                                        text=clause_text,
                                        page=current_clause_page,
                                        type=self.classify_clause(clause_text),
                                    )
                                )

                            current_clause_lines = [line]
                            current_clause_page = page_number
                        else:
                            current_clause_lines.append(line)

                if current_clause_lines:
                    clause_text = " ".join(current_clause_lines).strip()

                    clauses.append(
                        ClauseDTO(
                            id=f"clause_{len(clauses) + 1}",
                            section=current_section,
                            text=clause_text,
                            page=current_clause_page,
                            type=self.classify_clause(clause_text),
                        )
                    )

                metadata = DocumentMetadataDTO(
                    title=self.extract_title(full_text),
                    page_count=page_count,
                    parties=[],
                    signing_date=self.extract_signing_date(full_text),
                    effective_date=None,
                    value=self.extract_value(full_text),
                    duration=self.extract_duration(full_text),
                )

                return ParsedDocumentDTO(
                    metadata=metadata,
                    sections=sections,
                    clauses=clauses,
                )

        except Exception:
            traceback.print_exc()

            return ParsedDocumentDTO(
                metadata=DocumentMetadataDTO(),
                sections=[],
                clauses=[],
            )

    def clean_line(self, line: str) -> str:
        line = line.strip()
        line = re.sub(r"\s+", " ", line)
        return line

    def is_section_title(self, line: str) -> bool:
        patterns = [
            r"^(Articolul|Art\.|Art)\s+\d+",
            r"^(Clauza)\s+\d+",
            r"^Capitolul\s+[IVXLCDM\d]+",
            r"^CAPITOLUL\s+[IVXLCDM\d]+",
            r"^Secțiunea\s+\d+",
            r"^Sectiunea\s+\d+",

            # Titluri tipice din contracte:
            # 1. Părţi contractante
            # 2. Definiţii
            # 3. Obiectul contractului
            r"^\d+\.\s+[A-ZĂÂÎȘȚa-zăâîșț].*",
        ]

        return any(re.match(pattern, line, re.IGNORECASE) for pattern in patterns)
    def is_clause_start(self, line: str) -> bool:
        patterns = [
            r"^\d+\.\d+",
            r"^\d+\)",
            r"^\(\d+\)",
            r"^[a-z]\)",
            r"^Art\.\s*\d+",
            r"^Articolul\s+\d+",
            r"^Clauza\s+\d+",
        ]

        return any(re.match(pattern, line, re.IGNORECASE) for pattern in patterns)

    def extract_title(self, text: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines[:15]:
            if "contract" in line.lower():
                return line

        return lines[0] if lines else "Contract"

    def extract_signing_date(self, text: str):
        patterns = [
            r"\b\d{2}\.\d{2}\.\d{4}\b",
            r"\b\d{2}/\d{2}/\d{4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def extract_value(self, text: str) -> str:
        pattern = r"(\d+[.,]?\d*)\s*(lei|ron|eur|euro)"
        match = re.search(pattern, text, re.IGNORECASE)

        return match.group(0) if match else ""

    def extract_duration(self, text: str) -> str:
        pattern = r"(durata.{0,40}?(\d+\s*(zile|luni|ani)))"
        match = re.search(pattern, text, re.IGNORECASE)

        return match.group(2) if match else ""

    def classify_clause(self, text: str) -> ClauseType:
        text = text.lower()

        if "penalit" in text or "întârziere" in text or "intarziere" in text:
            return ClauseType.penalitate

        if "confiden" in text or "secret" in text:
            return ClauseType.confidentialitate

        if "gdpr" in text or "date personale" in text or "prelucrarea datelor" in text:
            return ClauseType.date_personale

        if "forta majora" in text or "forță majoră" in text:
            return ClauseType.forta_majora

        if "rezili" in text or "încetarea contractului" in text or "incetarea contractului" in text:
            return ClauseType.reziliere

        if "oblig" in text:
            return ClauseType.obligatie

        if "drept" in text:
            return ClauseType.drept

        return ClauseType.altele