# src/agents/risk_agent.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from src.dtos import RiskAssessmentDTO, RiskLevel, RetrievalResultDTO


class RiskAssessmentAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        self.parser = JsonOutputParser(pydantic_object=RiskAssessmentDTO)

        self.system_prompt = (
            "Ești un asistent juridic specializat în analiza contractelor din România.\n"
            "Sarcina ta este să evaluezi riscul clauzei trimise pe baza Contextului Legal furnizat.\n\n"
            "REGULI STRICTE DE CORECTITUDINE:\n"
            "1. Nu inventa legi, articole sau acte normative care nu apar explicit în context.\n"
            "2. Identifică contradicțiile clare dintre clauză și context.\n"
            "3. Completează obligatoriu vectorul de 'references' menționând numele fișierelor sursă din context din care te-ai inspirat.\n"
            "4. Nivelul de risc ('risk_level') trebuie să fie strict una dintre valorile: RIDICAT, MEDIU, SCAZUT, CONFORM.\n\n"
            "Formatul de ieșire trebuie să fie strict un obiect JSON care respectă structura DTO.\n"
            "{format_instructions}"
        )

        self.user_prompt = (
            "Context Legal:\n{legal_context}\n\n"
            "Clauză de Analizat:\n{clause_text}\n"
        )

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", self.user_prompt)
        ])

    def assess(self, clause_id: str, clause_text: str, context_chunks: list[RetrievalResultDTO]) -> RiskAssessmentDTO:
        """
        Assesses risks within a contract clause.
        Short-circuits immediately if context is empty.
        """
        if not context_chunks:
            return RiskAssessmentDTO(
                clause_id=clause_id,
                risk_level=RiskLevel.NECUNOSCUT,
                issues=["Nu s-a putut recuperat niciun context legal relevant pentru evaluare."],
                references=[],
                context_was_empty=True
            )

        try:
            compiled_context = ""
            for chunk in context_chunks:
                compiled_context += f"--- SURSA FIȘIER: {chunk.source} ---\n{chunk.text}\n\n"

            chain = self.prompt_template | self.llm | self.parser

            response_data = chain.invoke({
                "format_instructions": self.parser.get_format_instructions(),
                "legal_context": compiled_context,
                "clause_text": clause_text
            })

            return RiskAssessmentDTO(
                clause_id=clause_id,
                risk_level=RiskLevel(response_data["risk_level"]),
                issues=response_data.get("issues", []),
                references=response_data.get("references", []),
                context_was_empty=False
            )

        except Exception as e:
            print(f"Eroare la parsarea evaluării pentru {clause_id}: {e}")
            return RiskAssessmentDTO(
                clause_id=clause_id,
                risk_level=RiskLevel.NECUNOSCUT,
                issues=[f"Eroare internă de execuție LLM/Parsare: {str(e)}"],
                references=[],
                context_was_empty=False
            )