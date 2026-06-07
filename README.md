[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/tDAXz5sa)

# ⚖️ Sistem de Analiză Juridică AI

> Proiect Agentic AI — Universitatea Tehnică din Cluj-Napoca, Sisteme Inteligente, Mai 2026

Sistem multi-agent capabil să analizeze contracte juridice în limba română, să identifice clauze riscante sau non-conforme cu legislația în vigoare și să propună reformulări argumentate.

---

## 🏗️ Arhitectură

Sistemul este construit pe trei piloni:

- **RAG (Retrieval-Augmented Generation)** — răspunsurile sunt fundamentate pe un corpus juridic real: GDPR, Legea 98/2016, clauze UNCITRAL, hotărâri ANPC și modele de contracte publice din România
- **Sistem multi-agent** — sarcina complexă de analiză juridică este descompusă în agenți specializați, fiecare responsabil de o etapă distinctă
- **Orchestrare LangGraph** — agenții comunică prin intermediul unui graf de stări cu tranziții condiționale

### Fluxul pipeline-ului

```
PDF Contract
     ↓
DocumentParserAgent    → extrage și structurează clauzele
     ↓
RAGRetrievalAgent      → recuperează context juridic relevant din corpus
     ↓
RiskAssessmentAgent    → clasifică clauzele: RIDICAT / MEDIU / SCĂZUT / CONFORM
     ↓
quality_check          → dacă NECUNOSCUT > 40%, reîncearcă retrieval-ul
     ↓
RecommendationAgent    → propune reformulări ancorate în legislație
     ↓
Raport Markdown        → document final descărcabil
```

---

## 📁 Structura proiectului

```
proiect-aai-iuliaalexiamaria/
│
├── .env                        ← chei API (nu se commitează)
├── .env.example                ← template pentru chei API
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
│
├── corpus/                     ← documente juridice sursă pentru RAG
│   ├── gdpr/
│   ├── legi/
│   ├── contracte/
│   ├── uncitral/
│   └── anpc/
│
├── data/                       ← contracte de analizat + output-uri
│
├── vectorstore/                ← generat de build_index.py
│
├── logs/
│   ├── rag_evaluation.json
│   ├── retrieval_heatmap.png
│   ├── risk_distribution.png
│   ├── workflow_graph.png
│   └── run_<timestamp>.json
│
├── notebooks/
│   └── demo_pipeline.ipynb
│
├── scripts/
│   ├── build_index.py          ← rulat O SINGURĂ DATĂ
│   ├── evaluate_rag.py
│   ├── test_parser.py
│   └── test_retrieval.py
│
└── src/
    ├── dtos.py                 ← toate DTO-urile și enum-urile
    ├── app.py                  ← Streamlit UI
    ├── agents/
    │   ├── parser_agent.py         ← DocumentParserAgent
    │   ├── retrieval_agent.py      ← RAGRetrievalAgent
    │   ├── risk_agent.py           ← RiskAssessmentAgent
    │   └── recommendation_agent.py ← RecommendationAgent
    ├── tools/
    │   ├── pdf_tools.py            ← load_corpus()
    │   └── vector_tools.py         ← build_index()
    └── graph/
        └── workflow.py             ← WorkflowState + StateGraph
```

---

## 🚀 Instalare și rulare locală

### Cerințe

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (package manager)
- Cheie API OpenAI

### Pași

**1. Clonează repository-ul:**
```bash
git clone https://github.com/Technical-University-of-Cluj-Napoca/proiect-aai-iuliaalexiamaria.git
cd proiect-aai-iuliaalexiamaria
```

**2. Instalează dependențele:**
```bash
uv sync
```

**3. Configurează cheia API:**
```bash
cp .env.example .env
# Editează .env și adaugă cheia ta OpenAI
```

`.env` trebuie să conțină:
```
OPENAI_API_KEY=sk-...
```

**4. Construiește indexul vectorial (o singură dată):**
```bash
python -m scripts.build_index
```

**5. Pornește aplicația:**
```bash
python -m streamlit run src/app.py
```

Deschide [http://localhost:8501](http://localhost:8501) în browser.

---

## 🐳 Rulare cu Docker

```bash
# Asigură-te că .env este configurat
docker compose up
```

Aplicația va fi disponibilă la [http://localhost:8501](http://localhost:8501).

> **Notă:** Vectorstore-ul trebuie să existe înainte de `docker compose up`. Rulează `build_index.py` o dată local înainte.

---

## 📊 Tipuri de clauze analizate

| Tip clauză | Legislație de referință | Risc tipic |
|---|---|---|
| Penalități de întârziere | Legea 98/2016, art. 164 | Neplafonat / unilateral |
| Prelucrare date personale | GDPR art. 13, 14 | Temei legal absent |
| Clauze de forță majoră | Cod Civil art. 1351 | Definiție ambiguă |
| Reziliere unilaterală | ANPC, clauze abuzive | Dezechilibru contractual |
| Cesiunea contractului | UNCITRAL Model Law | Consimțământ lipsă |
| Răspundere limitată | Cod Civil art. 1355 | Excludere ilegală |
| Clauze de confidențialitate | GDPR, NDA standard | Durată nedefinită |
| Jurisdicție și arbitraj | Regulament UE 1215/2012 | Clauză compromisorie |

---

## 👥 Echipă și responsabilități

| Membru | Responsabilități |
|---|---|
| **Iulia** | `src/dtos.py`, corpus juridic, `load_corpus()`, `build_index.py`, `DocumentParserAgent` |
| **Alexia** | `RAGRetrievalAgent`, `evaluate_rag.py`, `RiskAssessmentAgent`, `retrieval_heatmap.png`, `risk_distribution.png` |
| **Maria** | `RecommendationAgent`, orchestrare LangGraph (`workflow.py`), Streamlit (`app.py`), Docker, `demo_pipeline.ipynb` |

---

## 🔧 Tehnologii folosite

- **LangChain** — framework pentru pipeline RAG și prompt management
- **LangGraph** — orchestrare multi-agent cu graf de stări
- **ChromaDB** — bază de date vectorială pentru indexare semantică
- **OpenAI GPT-4o-mini** — model LLM pentru evaluare risc și reformulări
- **Streamlit** — interfață grafică web
- **pdfplumber** — extragere text din PDF-uri
- **RAGAS** — evaluare calitate RAG
- **Docker** — containerizare și portabilitate

