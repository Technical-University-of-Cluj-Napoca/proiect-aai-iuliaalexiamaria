# src/agents/recommendation_agent.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.dtos import (
    RecommendationDTO,
    RiskAssessmentDTO,
    RiskLevel,
    RetrievalResultDTO,
)


class RecommendationAgent:
    """
    Agent responsabil de generarea reformulărilor pentru clauzele riscante.

    Logica principală:
    - Pentru RIDICAT: self-consistency — 3 apeluri independente, al 4-lea alege cea mai bună variantă
    - Pentru MEDIU: un singur apel LLM
    - Pentru SCAZUT / CONFORM / NECUNOSCUT: nu se apelează LLM, se returnează reformulated_text gol
    """

    def __init__(self):
        # Temperatura 0.7 pentru variație în candidații de self-consistency
        self.llm_creative = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        # Temperatura 0.0 pentru selecția finală deterministă
        self.llm_judge = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

        self.str_parser = StrOutputParser()

        # Prompt pentru generarea unei reformulări individuale
        self.reformulation_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Ești un jurist specializat în drept contractual român.\n"
                    "Sarcina ta este să reformulezi clauza problematică furnizată, "
                    "astfel încât să respecte legislația română în vigoare și să asigure "
                    "echilibrul contractual între părți.\n\n"
                    "REGULI OBLIGATORII:\n"
                    "1. Folosește stil juridic formal, în limba română.\n"
                    "2. Ancorează reformularea în sursele din contextul legal furnizat — "
                    "citează explicit actul normativ relevant (ex: 'conform art. X din GDPR').\n"
                    "3. Asigură echilibrul contractual: nicio parte nu trebuie să aibă avantaje unilaterale.\n"
                    "4. Răspunde DOAR cu textul reformulat al clauzei, fără explicații suplimentare."
                ),
            ),
            (
                "user",
                (
                    "Context legal relevant:\n{legal_context}\n\n"
                    "Probleme identificate în clauză:\n{issues}\n\n"
                    "Clauza originală de reformulat:\n{original_text}"
                ),
            ),
        ])

        # Prompt pentru selecția celei mai bune variante (self-consistency)
        self.judge_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Ești un expert juridic care evaluează variante de reformulare a unei clauze contractuale.\n"
                    "Alege varianta care:\n"
                    "- Respectă cel mai bine legislația română\n"
                    "- Este cea mai clară și mai echilibrată contractual\n"
                    "- Citează explicit surse legislative\n\n"
                    "Răspunde DOAR cu textul variantei alese, fără nicio explicație."
                ),
            ),
            (
                "user",
                (
                    "Clauza originală:\n{original_text}\n\n"
                    "Variante de reformulare:\n{candidates}\n\n"
                    "Alege cea mai bună variantă:"
                ),
            ),
        ])

        # Prompt pentru generarea explicației finale
        self.explanation_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Ești un jurist care explică unui client de ce o clauză contractuală a fost reformulată.\n"
                    "Explică pe scurt (2-4 propoziții), în română, de ce reformularea propusă este mai sigură "
                    "și mai conformă cu legislația. Fii concis și clar."
                ),
            ),
            (
                "user",
                (
                    "Clauza originală:\n{original_text}\n\n"
                    "Reformularea propusă:\n{reformulated_text}\n\n"
                    "Probleme identificate:\n{issues}"
                ),
            ),
        ])

    def _build_legal_context(self, context_chunks: list[RetrievalResultDTO]) -> str:
        """Concatenează chunk-urile de context cu sursa lor, pentru ancorare corectă."""
        if not context_chunks:
            return "Nu există context legal disponibil."

        parts = []
        for chunk in context_chunks:
            parts.append(f"--- SURSA: {chunk.source} ---\n{chunk.text}")
        return "\n\n".join(parts)

    def _generate_single_reformulation(
        self,
        original_text: str,
        issues: list[str],
        legal_context: str,
    ) -> str:
        """Generează o singură reformulare a clauzei."""
        chain = self.reformulation_prompt | self.llm_creative | self.str_parser
        return chain.invoke({
            "legal_context": legal_context,
            "issues": "\n".join(f"- {issue}" for issue in issues),
            "original_text": original_text,
        })

    def _select_best_candidate(
        self,
        original_text: str,
        candidates: list[str],
    ) -> str:
        """Al 4-lea apel LLM: alege cea mai bună variantă dintre candidați."""
        formatted_candidates = "\n\n".join(
            f"Varianta {i + 1}:\n{candidate}"
            for i, candidate in enumerate(candidates)
        )
        chain = self.judge_prompt | self.llm_judge | self.str_parser
        return chain.invoke({
            "original_text": original_text,
            "candidates": formatted_candidates,
        })

    def _generate_explanation(
        self,
        original_text: str,
        reformulated_text: str,
        issues: list[str],
    ) -> str:
        """Generează o explicație scurtă pentru jurist despre motivul reformulării."""
        chain = self.explanation_prompt | self.llm_judge | self.str_parser
        return chain.invoke({
            "original_text": original_text,
            "reformulated_text": reformulated_text,
            "issues": "\n".join(f"- {issue}" for issue in issues),
        })

    def recommend(
        self,
        clause_id: str,
        original_text: str,
        risk_assessment: RiskAssessmentDTO,
        context_chunks: list[RetrievalResultDTO],
    ) -> RecommendationDTO:
        """
        Generează o recomandare de reformulare pentru o clauză.

        - RIDICAT  → self-consistency (3 candidați + 1 judecată)
        - MEDIU    → un singur apel LLM
        - altele   → returnează DTO gol, fără apel LLM
        """
        # Clauzele SCAZUT, CONFORM, NECUNOSCUT nu necesită reformulare
        if risk_assessment.risk_level not in (RiskLevel.RIDICAT, RiskLevel.MEDIU):
            return RecommendationDTO(
                clause_id=clause_id,
                original_text=original_text,
                reformulated_text="",
                explanation="",
                sources=[],
                candidates=None,
            )

        legal_context = self._build_legal_context(context_chunks)
        sources = list({chunk.source for chunk in context_chunks})

        try:
            if risk_assessment.risk_level == RiskLevel.RIDICAT:
                # Self-consistency: 3 apeluri independente cu temperatură creativă
                candidates = []
                for i in range(3):
                    candidate = self._generate_single_reformulation(
                        original_text=original_text,
                        issues=risk_assessment.issues,
                        legal_context=legal_context,
                    )
                    candidates.append(candidate)
                    print(f"   [RecommendationAgent] Candidat {i + 1} generat pentru {clause_id}")

                # Al 4-lea apel: judecătorul alege cea mai bună variantă
                best = self._select_best_candidate(original_text, candidates)
                print(f"   [RecommendationAgent] Variantă finală selectată pentru {clause_id}")

            else:
                # MEDIU: un singur apel
                candidates = None
                best = self._generate_single_reformulation(
                    original_text=original_text,
                    issues=risk_assessment.issues,
                    legal_context=legal_context,
                )
                print(f"   [RecommendationAgent] Reformulare generată pentru {clause_id}")

            # Generează explicația finală
            explanation = self._generate_explanation(
                original_text=original_text,
                reformulated_text=best,
                issues=risk_assessment.issues,
            )

            return RecommendationDTO(
                clause_id=clause_id,
                original_text=original_text,
                reformulated_text=best,
                explanation=explanation,
                sources=sources,
                candidates=candidates,
            )

        except Exception as e:
            print(f"   [RecommendationAgent] Eroare la generarea recomandării pentru {clause_id}: {e}")
            return RecommendationDTO(
                clause_id=clause_id,
                original_text=original_text,
                reformulated_text="",
                explanation=f"Eroare la generarea reformulării: {str(e)}",
                sources=sources,
                candidates=None,
            )

    def generate_report(
        self,
        recommendations: list[RecommendationDTO],
        risk_map: dict,
        output_path: str,
    ) -> str:
        """
        Generează raportul Markdown final.
        Lizibil de un jurist fără cunoștințe tehnice.
        """
        lines = []
        lines.append("# Raport de Analiză Juridică\n")
        lines.append(
            "> Acest raport a fost generat automat de sistemul de analiză a contractelor juridice.\n"
        )
        lines.append("---\n")

        # Secțiunea de sumar
        high = sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.RIDICAT)
        medium = sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.MEDIU)
        low = sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.SCAZUT)
        conform = sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.CONFORM)
        unknown = sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.NECUNOSCUT)

        lines.append("## Sumar Executiv\n")
        lines.append(f"| Nivel de Risc | Număr Clauze |")
        lines.append(f"|---|---|")
        lines.append(f"| 🔴 RIDICAT | {high} |")
        lines.append(f"| 🟡 MEDIU | {medium} |")
        lines.append(f"| 🟢 SCĂZUT | {low} |")
        lines.append(f"| ✅ CONFORM | {conform} |")
        lines.append(f"| ❓ NECUNOSCUT | {unknown} |")
        lines.append("")

        # Secțiunea de detalii per clauză
        lines.append("## Clauze Analizate\n")

        # Întâi clauzele cu risc ridicat
        risc_order = [RiskLevel.RIDICAT, RiskLevel.MEDIU, RiskLevel.SCAZUT, RiskLevel.CONFORM, RiskLevel.NECUNOSCUT]

        for level in risc_order:
            clauses_at_level = [
                rec for rec in recommendations
                if risk_map.get(rec.clause_id) and risk_map[rec.clause_id].risk_level == level
            ]
            if not clauses_at_level:
                continue

            emoji = {"RIDICAT": "🔴", "MEDIU": "🟡", "SCAZUT": "🟢", "CONFORM": "✅", "NECUNOSCUT": "❓"}
            lines.append(f"### {emoji.get(level.value, '')} Clauze cu Risc {level.value}\n")

            for rec in clauses_at_level:
                risk = risk_map[rec.clause_id]
                lines.append(f"#### Clauza `{rec.clause_id}`\n")

                lines.append("**Text original:**")
                lines.append(f"> {rec.original_text}\n")

                if risk.issues:
                    lines.append("**Probleme identificate:**")
                    for issue in risk.issues:
                        lines.append(f"- {issue}")
                    lines.append("")

                if risk.references:
                    lines.append("**Referințe legislative:**")
                    for ref in risk.references:
                        lines.append(f"- {ref}")
                    lines.append("")

                if rec.reformulated_text:
                    lines.append("**Reformulare propusă:**")
                    lines.append(f"> {rec.reformulated_text}\n")

                    lines.append("**Explicație:**")
                    lines.append(f"{rec.explanation}\n")

                    if rec.sources:
                        lines.append("**Surse corpus:**")
                        for src in rec.sources:
                            lines.append(f"- `{src}`")
                        lines.append("")

                lines.append("---\n")

        report_content = "\n".join(lines)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"   [RecommendationAgent] Raport salvat la: {output_path}")
        return report_content