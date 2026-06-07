# src/graph/workflow.py

import json
import time
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from src.agents.parser_agent import DocumentParserAgent
from src.agents.retrieval_agent import RAGRetrievalAgent
from src.agents.risk_agent import RiskAssessmentAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.dtos import (
    ParsedDocumentDTO,
    RetrievalResultDTO,
    RiskAssessmentDTO,
    RecommendationDTO,
    RiskLevel,
)

# Numărul maxim de iterații pentru bucla de feedback
MAX_ITER = 2

# Pragul de clauze NECUNOSCUT (%) peste care se retriggerează retrieval-ul
UNKNOWN_THRESHOLD = 0.40

# Pragul de clauze RIDICAT peste care se setează high_risk_alert
HIGH_RISK_THRESHOLD = 2



class WorkflowState(TypedDict):
    pdf_path: str
    parsed_doc: Optional[ParsedDocumentDTO]
    context_map: dict[str, list[RetrievalResultDTO]]
    risk_map: dict[str, RiskAssessmentDTO]
    high_risk_alert: bool
    recommendations: list[RecommendationDTO]
    report_path: str
    iteration: int


class WorkflowLogger:
    def __init__(self):
        Path("logs").mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = f"logs/run_{timestamp}.json"
        self.entries = []

    def log(self, node: str, duration: float, tokens: int = 0, extra: dict = None):
        entry = {
            "node": node,
            "duration_sec": round(duration, 3),
            "tokens_estimate": tokens,
            **(extra or {}),
        }
        self.entries.append(entry)
        print(f"   [LOG] {node} — {duration:.2f}s")

    def save(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)
        print(f"   [LOG] Jurnal salvat la: {self.log_path}")



def make_parse_document(logger: WorkflowLogger):
    """Nod: parsează PDF-ul și returnează ParsedDocumentDTO."""
    agent = DocumentParserAgent()

    def generate_recommendations(state: WorkflowState) -> WorkflowState:
        print("\n[NOD] generate_recommendations")
        start = time.time()

        recommendations = []
        clauses = state["parsed_doc"].clauses if state["parsed_doc"] else []

        # Limităm la primele 10 clauze pentru demo
        clauses = clauses[:10]

        for clause in clauses:
            risk = state["risk_map"].get(clause.id)
            if not risk:
                continue
            # Sari peste NECUNOSCUT pentru viteză
            if risk.risk_level.value == "NECUNOSCUT":
                continue

    def parse_document(state: WorkflowState) -> WorkflowState:
        print("\n[NOD] parse_document")
        start = time.time()

        parsed = agent.parse(state["pdf_path"])

        logger.log(
            node="parse_document",
            duration=time.time() - start,
            extra={"clauses_found": len(parsed.clauses), "sections": len(parsed.sections)},
        )

        return {**state, "parsed_doc": parsed}

    return parse_document


def make_retrieve_context(logger: WorkflowLogger):
    """
    Nod: pentru fiecare clauză, recuperează context juridic relevant.
    La a doua iterație (după feedback), folosește parametri mai permisivi.
    """
    agent = RAGRetrievalAgent()

    def retrieve_context(state: WorkflowState) -> WorkflowState:
        print(f"\n[NOD] retrieve_context (iterație {state['iteration']})")
        start = time.time()

        context_map = {}
        clauses = state["parsed_doc"].clauses if state["parsed_doc"] else []

        for clause in clauses:
            results = agent.retrieve(
                clause_text=clause.text,
                k=5,
                iteration=state["iteration"],
            )
            context_map[clause.id] = results

        logger.log(
            node="retrieve_context",
            duration=time.time() - start,
            extra={"clauses_processed": len(clauses), "iteration": state["iteration"]},
        )

        return {**state, "context_map": context_map}

    return retrieve_context


def make_assess_risk(logger: WorkflowLogger):
    """Nod: evaluează riscul fiecărei clauze pe baza contextului recuperat."""
    agent = RiskAssessmentAgent()

    def assess_risk(state: WorkflowState) -> WorkflowState:
        print(f"\n[NOD] assess_risk (iterație {state['iteration']})")
        start = time.time()

        risk_map = {}
        clauses = state["parsed_doc"].clauses if state["parsed_doc"] else []

        for clause in clauses:
            context_chunks = state["context_map"].get(clause.id, [])
            assessment = agent.assess(
                clause_id=clause.id,
                clause_text=clause.text,
                context_chunks=context_chunks,
            )
            risk_map[clause.id] = assessment

        logger.log(
            node="assess_risk",
            duration=time.time() - start,
            extra={
                "clauses_assessed": len(clauses),
                "high_risk": sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.RIDICAT),
                "unknown": sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.NECUNOSCUT),
            },
        )

        return {**state, "risk_map": risk_map, "iteration": state["iteration"] + 1}

    return assess_risk


def quality_check(state: WorkflowState) -> str:
    """
    Nod de decizie: verifică dacă prea multe clauze sunt NECUNOSCUT.

    Dacă rata NECUNOSCUT > 40% și nu am depășit MAX_ITER,
    întoarce la retrieve_context cu parametri mai permisivi.
    Altfel, continuă pipeline-ul.
    """
    risk_map = state["risk_map"]
    if not risk_map:
        return "flag_high_risk"

    unknown_count = sum(1 for r in risk_map.values() if r.risk_level == RiskLevel.NECUNOSCUT)
    unknown_rate = unknown_count / len(risk_map)

    print(f"\n[NOD] quality_check — NECUNOSCUT: {unknown_count}/{len(risk_map)} ({unknown_rate:.0%}), iterație: {state['iteration']}")

    # Bucla de feedback: dacă prea multe NECUNOSCUT și mai avem iterații
    if unknown_rate > UNKNOWN_THRESHOLD and state["iteration"] <= MAX_ITER:
        print("   → Retrieval insuficient, se reîncearcă cu parametri mai permisivi.")
        return "retrieve_context"

    return "flag_high_risk"


def make_flag_high_risk(logger: WorkflowLogger):
    """
    Nod: setează high_risk_alert dacă numărul de clauze RIDICAT depășește pragul.
    Nu blochează pipeline-ul.
    """
    def flag_high_risk(state: WorkflowState) -> WorkflowState:
        print("\n[NOD] flag_high_risk")
        start = time.time()

        high_risk_count = sum(
            1 for r in state["risk_map"].values()
            if r.risk_level == RiskLevel.RIDICAT
        )
        alert = high_risk_count >= HIGH_RISK_THRESHOLD

        if alert:
            print(f"   ⚠️  ALERTĂ: {high_risk_count} clauze cu risc RIDICAT!")

        logger.log(
            node="flag_high_risk",
            duration=time.time() - start,
            extra={"high_risk_count": high_risk_count, "alert_triggered": alert},
        )

        return {**state, "high_risk_alert": alert}

    return flag_high_risk


def make_generate_recommendations(logger: WorkflowLogger):
    """Nod: generează reformulări pentru clauzele RIDICAT și MEDIU."""
    agent = RecommendationAgent()

    def generate_recommendations(state: WorkflowState) -> WorkflowState:
        print("\n[NOD] generate_recommendations")
        start = time.time()

        recommendations = []
        clauses = state["parsed_doc"].clauses if state["parsed_doc"] else []

        for clause in clauses:
            risk = state["risk_map"].get(clause.id)
            if not risk:
                continue

            context_chunks = state["context_map"].get(clause.id, [])
            rec = agent.recommend(
                clause_id=clause.id,
                original_text=clause.text,
                risk_assessment=risk,
                context_chunks=context_chunks,
            )
            recommendations.append(rec)

        logger.log(
            node="generate_recommendations",
            duration=time.time() - start,
            extra={
                "total": len(recommendations),
                "with_reformulation": sum(1 for r in recommendations if r.reformulated_text),
            },
        )

        return {**state, "recommendations": recommendations}

    return generate_recommendations


def make_compile_report(logger: WorkflowLogger):
    """Nod final: compilează raportul Markdown și îl salvează pe disc."""
    agent = RecommendationAgent()

    def compile_report(state: WorkflowState) -> WorkflowState:
        print("\n[NOD] compile_report")
        start = time.time()

        Path("data").mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/raport_{timestamp}.md"

        agent.generate_report(
            recommendations=state["recommendations"],
            risk_map=state["risk_map"],
            output_path=output_path,
        )

        logger.log(
            node="compile_report",
            duration=time.time() - start,
            extra={"report_path": output_path},
        )

        logger.save()

        return {**state, "report_path": output_path}

    return compile_report


def build_workflow() -> StateGraph:
    """
    Construiește și compilează graful de stări LangGraph.

    Fluxul:
    parse_document → retrieve_context → assess_risk → quality_check
        ↑                                                    |
        └──────────── (retry dacă NECUNOSCUT > 40%) ────────┘
                                                             |
                                              flag_high_risk → generate_recommendations → compile_report
    """
    logger = WorkflowLogger()

    graph = StateGraph(WorkflowState)

    # Adaugă nodurile
    graph.add_node("parse_document", make_parse_document(logger))
    graph.add_node("retrieve_context", make_retrieve_context(logger))
    graph.add_node("assess_risk", make_assess_risk(logger))
    graph.add_node("flag_high_risk", make_flag_high_risk(logger))
    graph.add_node("generate_recommendations", make_generate_recommendations(logger))
    graph.add_node("compile_report", make_compile_report(logger))

    # Definește tranzițiile liniare
    graph.set_entry_point("parse_document")
    graph.add_edge("parse_document", "retrieve_context")
    graph.add_edge("retrieve_context", "assess_risk")

    # Tranziție condițională: quality_check decide dacă reîncercăm sau continuăm
    graph.add_conditional_edges(
        "assess_risk",
        quality_check,
        {
            "retrieve_context": "retrieve_context",  # bucla de feedback
            "flag_high_risk": "flag_high_risk",       # continuă normal
        },
    )

    graph.add_edge("flag_high_risk", "generate_recommendations")
    graph.add_edge("generate_recommendations", "compile_report")
    graph.add_edge("compile_report", END)

    return graph.compile()


def run_workflow(pdf_path: str) -> WorkflowState:
    """
    Punctul de intrare principal al sistemului.
    Primește calea către un PDF și returnează starea finală completă.
    """
    app = build_workflow()

    initial_state: WorkflowState = {
        "pdf_path": pdf_path,
        "parsed_doc": None,
        "context_map": {},
        "risk_map": {},
        "high_risk_alert": False,
        "recommendations": [],
        "report_path": "",
        "iteration": 0,
    }

    print(f"\n{'=' * 60}")
    print(f"  START WORKFLOW: {pdf_path}")
    print(f"{'=' * 60}")

    final_state = app.invoke(initial_state)

    print(f"\n{'=' * 60}")
    print(f"  WORKFLOW FINALIZAT")
    print(f"  Raport: {final_state['report_path']}")
    print(f"  Alertă risc ridicat: {final_state['high_risk_alert']}")
    print(f"{'=' * 60}\n")

    return final_state


def export_workflow_graph():
    """Exportă diagrama grafului în logs/workflow_graph.png."""
    try:
        app = build_workflow()
        png = app.get_graph().draw_mermaid_png()
        Path("logs").mkdir(exist_ok=True)
        with open("logs/workflow_graph.png", "wb") as f:
            f.write(png)
        print("   [EXPORT] Graf salvat la logs/workflow_graph.png")
    except Exception as e:
        print(f"   [EXPORT] Nu s-a putut exporta graful: {e}")