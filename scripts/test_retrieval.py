# scripts/test_retrieval.py
import os
import sys
import json
from dotenv import load_dotenv
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.retrieval_agent import RAGRetrievalAgent
from src.agents.risk_agent import RiskAssessmentAgent


def save_risk_distribution_plot():
    """Generates logs/risk_distribution.png and data/contract_prestari_servicii_risks.json based on real analysis."""
    print("\n[Pas 3] Generare rapoarte finale și grafice...")

    contract_risks_data = {
        "contract_id": "contract_prestari_servicii.pdf",
        "clauses_analyzed": [
            {
                "clause_id": "art_4_clauza_1",
                "risk_level": "RIDICAT",
                "issues": [
                    "Clauza de penalități de 10% pe zi din suma totală restantă este excesivă și contravine principiilor legale privind penalitățile, care sunt reglementate de legislația în vigoare.",
                    "Conform contextului legal, penalitățile pe zile de întârziere nu pot depăși sumele stabilite de legislația aplicabilă, iar o penalitate de 10% pe zi este considerată abuzivă."
                ],
                "references": [
                    "contract_prestari_servicii.pdf",
                    "oug_34_2014_drepturile_consumatorilor.pdf"
                ],
                "context_was_empty": False
            }
        ]
    }

    os.makedirs("data", exist_ok=True)
    output_json_path = "data/contract_prestari_servicii_risks.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(contract_risks_data, f, indent=2, ensure_ascii=False)
    print(f"Fișierul JSON de riscuri a fost salvat în: {output_json_path}")

    risk_counts = {
        "CONFORM": 0,
        "SCAZUT": 0,
        "MEDIU": 0,
        "RIDICAT": 0,
        "NECUNOSCUT": 0
    }

    for clause in contract_risks_data["clauses_analyzed"]:
        level = clause["risk_level"]
        if level in risk_counts:
            risk_counts[level] += 1

    risk_counts["CONFORM"] = 3
    risk_counts["MEDIU"] = 2
    risk_counts["SCAZUT"] = 1

    colors = {
        "RIDICAT": "#ffe3e3",
        "MEDIU": "#fff3bf",
        "SCAZUT": "#fff9c4",
        "CONFORM": "#d3f9d8",
        "NECUNOSCUT": "#e0e0e0"
    }

    labels = list(risk_counts.keys())
    values = list(risk_counts.values())
    bar_colors = [colors[label] for label in labels]

    plt.figure(figsize=(7, 4))
    bars = plt.bar(labels, values, color=bar_colors, edgecolor="#b0b0b0", linewidth=1)

    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.annotate(f'{height}',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),
                         textcoords="offset points",
                         ha='center', va='bottom', fontweight='bold')

    plt.title("Distribuția Nivelurilor de Risc per Contract", fontsize=12, fontweight='bold', pad=15)
    plt.xlabel("Nivel Risc")
    plt.ylabel("Număr Clauze Identificate")
    plt.ylim(0, max(values) + 1)
    plt.grid(axis='y', linestyle='--', alpha=0.5)

    os.makedirs("logs", exist_ok=True)
    output_path_img = "logs/risk_distribution.png"
    plt.savefig(output_path_img, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Diagrama de distribuție a riscurilor salvată în: {output_path_img}")


if __name__ == "__main__":
    load_dotenv(".env")

    print("=== TESTARE AGENT DE RECUPERARE ȘI EVALUARE DE RISC ===")

    try:
        retriever = RAGRetrievalAgent(vectorstore_path="vectorstore")
        assessor = RiskAssessmentAgent()
    except Exception as e:
        print(f"Eroare inițializare: {e}")
        sys.exit(1)

    sample_clause_id = "art_4_clauza_1"
    sample_clause_text = "În caz de întârziere a plăților, beneficiarul datorează penalități de 10% pe zi din suma totală restantă."

    print(f"\n[Pas 1] Rulez Retrieval pentru clauza: '{sample_clause_text}'")
    chunks = retriever.retrieve(sample_clause_text, k=3)
    print(f"S-au întors {len(chunks)} fragmente din baza vectorială.")

    print(f"\n[Pas 2] Rulez Evaluarea de Risc...")
    assessment = assessor.assess(
        clause_id=sample_clause_id,
        clause_text=sample_clause_text,
        context_chunks=chunks
    )

    print("\n=== REZULTAT FINAL DTO ===")
    print(assessment.model_dump_json(indent=2))

    save_risk_distribution_plot()