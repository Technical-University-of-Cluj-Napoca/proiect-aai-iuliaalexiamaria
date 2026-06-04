import os

from src.agents.parser_agent import DocumentParserAgent


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, "data", "contract_exemplu.pdf")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "contract_exemplu_parsed.json")


if __name__ == "__main__":
    parser = DocumentParserAgent()

    result = parser.parse(PDF_PATH)

    print("Titlu:", result.metadata.title)
    print("Numar pagini:", result.metadata.page_count)
    print("Numar sectiuni:", len(result.sections))
    print("Numar clauze:", len(result.clauses))

    print("\nPrimele 3 clauze:")
    for clause in result.clauses[:3]:
        print(clause.model_dump())

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    print("\nSalvat in:", OUTPUT_PATH)