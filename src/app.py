# src/app.py

import streamlit as st
import tempfile
import os
from pathlib import Path

from src.graph.workflow import run_workflow, export_workflow_graph

# ---------------------------------------------------------------------------
# Configurare pagină
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Analiză Juridică AI",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ Sistem de Analiză Juridică AI")
st.caption("Încarcă un contract PDF și primești un raport cu clauzele riscante și reformulările propuse.")

# ---------------------------------------------------------------------------
# Sidebar — controale
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Configurare")

    uploaded_file = st.file_uploader(
        "Încarcă contractul PDF",
        type=["pdf"],
        help="Acceptă orice contract în limba română în format PDF.",
    )

    relevance_threshold = st.slider(
        "Prag relevanță retrieval",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Distanța L2 maximă acceptată pentru chunk-urile recuperate. Valori mai mari = mai permisiv.",
    )

    high_risk_threshold = st.slider(
        "Prag alertă risc ridicat (nr. clauze)",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
        help="Câte clauze RIDICAT declanșează bannerul de alertă.",
    )

    analyze_btn = st.button("🔍 Analizează contractul", use_container_width=True)

    st.divider()
    st.markdown("**Despre sistem:**")
    st.markdown(
        "- Parser → RAG → Risk Assessment → Recomandări\n"
        "- Orchestrat cu LangGraph\n"
        "- Corpus juridic: GDPR, Legea 98/2016, UNCITRAL, ANPC"
    )

# ---------------------------------------------------------------------------
# Zona principală
# ---------------------------------------------------------------------------

# Dacă nu există nimic în session_state, inițializăm
if "final_state" not in st.session_state:
    st.session_state.final_state = None
if "report_content" not in st.session_state:
    st.session_state.report_content = None

# Culori pentru niveluri de risc
RISK_COLORS = {
    "RIDICAT": "#ffe3e3",
    "MEDIU": "#fff3bf",
    "SCAZUT": "#fff9c4",
    "CONFORM": "#d3f9d8",
    "NECUNOSCUT": "#f0f0f0",
}

RISK_EMOJI = {
    "RIDICAT": "🔴",
    "MEDIU": "🟡",
    "SCAZUT": "🟢",
    "CONFORM": "✅",
    "NECUNOSCUT": "❓",
}

# ---------------------------------------------------------------------------
# Logica de analiză — rulează doar la click, rezultatul se păstrează
# ---------------------------------------------------------------------------

if analyze_btn and uploaded_file is not None:
    # Salvăm PDF-ul într-un fișier temporar
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        # Bara de progres cu mesaje per agent
        progress = st.progress(0, text="Se inițializează pipeline-ul...")

        progress.progress(10, text="📄 Agent Parser: se extrag clauzele din PDF...")
        # run_workflow face totul intern; afișăm progresul între noduri
        # prin actualizarea barei manual după ce știm că a trecut de fiecare nod

        progress.progress(30, text="🔍 Agent RAG: se recuperează contextul juridic...")
        progress.progress(50, text="⚖️ Agent Risk Assessment: se evaluează riscurile...")
        progress.progress(70, text="✍️ Agent Recomandare: se generează reformulările...")
        progress.progress(85, text="📝 Se compilează raportul final...")

        final_state = run_workflow(tmp_path)

        progress.progress(100, text="✅ Analiză completă!")
        st.session_state.final_state = final_state

        # Citim raportul Markdown generat
        report_path = final_state.get("report_path", "")
        if report_path and Path(report_path).exists():
            with open(report_path, "r", encoding="utf-8") as f:
                st.session_state.report_content = f.read()

    except Exception as e:
        st.error(f"Eroare în timpul analizei: {e}")
    finally:
        os.unlink(tmp_path)

elif analyze_btn and uploaded_file is None:
    st.warning("Te rog încarcă un fișier PDF înainte de a apăsa Analizează.")

# ---------------------------------------------------------------------------
# Afișarea rezultatelor (din session_state — nu se re-rulează la interacțiuni)
# ---------------------------------------------------------------------------

if st.session_state.final_state is not None:
    state = st.session_state.final_state

    # Banner alertă risc ridicat
    if state.get("high_risk_alert"):
        st.warning(
            "⚠️ **ALERTĂ: Contractul conține mai multe clauze cu risc RIDICAT!** "
            "Se recomandă revizuirea urgentă de către un jurist.",
            icon="⚠️",
        )

    # ---------------------------------------------------------------------------
    # Tabel sumar clauze
    # ---------------------------------------------------------------------------
    st.subheader("📊 Sumar clauze analizate")

    risk_map = state.get("risk_map", {})
    parsed_doc = state.get("parsed_doc")
    recommendations = state.get("recommendations", [])
    rec_map = {r.clause_id: r for r in recommendations}

    if risk_map:
        # Construim tabelul cu fundal colorat folosind HTML
        rows_html = ""
        for clause_id, risk in risk_map.items():
            color = RISK_COLORS.get(risk.risk_level.value, "#ffffff")
            emoji = RISK_EMOJI.get(risk.risk_level.value, "")
            # Găsim textul clauzei
            clause_text = ""
            if parsed_doc:
                for c in parsed_doc.clauses:
                    if c.id == clause_id:
                        clause_text = c.text[:120] + "..." if len(c.text) > 120 else c.text
                        break

            rows_html += (
                f'<tr style="background-color:{color}">'
                f"<td><code>{clause_id}</code></td>"
                f"<td>{emoji} {risk.risk_level.value}</td>"
                f"<td>{clause_text}</td>"
                f"</tr>"
            )

        table_html = f"""
        <table style="width:100%; border-collapse:collapse; font-size:14px;">
            <thead>
                <tr style="background-color:#f8f9fa; font-weight:bold;">
                    <th style="padding:8px; text-align:left;">ID Clauză</th>
                    <th style="padding:8px; text-align:left;">Nivel Risc</th>
                    <th style="padding:8px; text-align:left;">Text (preview)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("Nu s-au găsit clauze de afișat.")

    st.divider()

    # ---------------------------------------------------------------------------
    # Expander per clauză riscantă (RIDICAT și MEDIU)
    # ---------------------------------------------------------------------------
    risky_risks = {
        cid: r for cid, r in risk_map.items()
        if r.risk_level.value in ("RIDICAT", "MEDIU")
    }

    if risky_risks:
        st.subheader("🔎 Detalii clauze riscante")

        for clause_id, risk in risky_risks.items():
            emoji = RISK_EMOJI.get(risk.risk_level.value, "")
            color = RISK_COLORS.get(risk.risk_level.value, "#ffffff")

            rec = rec_map.get(clause_id)

            with st.expander(f"{emoji} {clause_id} — {risk.risk_level.value}", expanded=False):
                # Text original
                if rec:
                    st.markdown("**Text original:**")
                    st.markdown(
                        f'<div style="background:{color};padding:10px;border-radius:6px;">'
                        f"{rec.original_text}</div>",
                        unsafe_allow_html=True,
                    )

                # Probleme identificate
                if risk.issues:
                    st.markdown("**Probleme identificate:**")
                    for issue in risk.issues:
                        st.markdown(f"- {issue}")

                # Referințe legislative
                if risk.references:
                    st.markdown("**Referințe legislative:**")
                    for ref in risk.references:
                        st.markdown(f"- `{ref}`")

                # Reformulare propusă
                if rec and rec.reformulated_text:
                    st.markdown("**Reformulare propusă:**")
                    st.markdown(
                        f'<div style="background:#e8f5e9;padding:10px;border-radius:6px;">'
                        f"{rec.reformulated_text}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Explicație:** {rec.explanation}")

                    if rec.sources:
                        st.markdown("**Surse corpus:**")
                        for src in rec.sources:
                            st.markdown(f"- `{src}`")

                    # Candidați self-consistency (doar RIDICAT)
                    if rec.candidates:
                        with st.expander("🔬 Vezi toți candidații generați (self-consistency)"):
                            for i, candidate in enumerate(rec.candidates):
                                st.markdown(f"**Candidat {i + 1}:**")
                                st.markdown(candidate)
                                st.divider()

    st.divider()

    # ---------------------------------------------------------------------------
    # Buton descărcare raport Markdown
    # ---------------------------------------------------------------------------
    if st.session_state.report_content:
        st.subheader("📥 Descarcă raportul")
        st.download_button(
            label="⬇️ Descarcă raport Markdown",
            data=st.session_state.report_content,
            file_name="raport_analiza_juridica.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # ---------------------------------------------------------------------------
    # Vizualizări logs (dacă există)
    # ---------------------------------------------------------------------------
    st.divider()
    st.subheader("📈 Vizualizări")

    col1, col2, col3 = st.columns(3)
    with col1:
        if Path("logs/retrieval_heatmap.png").exists():
            st.image("logs/retrieval_heatmap.png", caption="Heatmap Retrieval")
    with col2:
        if Path("logs/risk_distribution.png").exists():
            st.image("logs/risk_distribution.png", caption="Distribuție Riscuri")
    with col3:
        if Path("logs/workflow_graph.png").exists():
            st.image("logs/workflow_graph.png", caption="Graf Workflow")
        else:
            if st.button("Generează graf workflow"):
                export_workflow_graph()
                st.rerun()

else:
    # Stare inițială — nicio analiză rulată încă
    st.info("👈 Încarcă un PDF din sidebar și apasă **Analizează contractul** pentru a începe.")

    st.markdown("""
    ### Cum funcționează sistemul?

    1. **Parser Agent** — extrage clauzele din PDF și le structurează
    2. **RAG Agent** — caută context juridic relevant din corpus (GDPR, Legea 98/2016, UNCITRAL, ANPC)
    3. **Risk Assessment Agent** — clasifică fiecare clauză: RIDICAT / MEDIU / SCĂZUT / CONFORM
    4. **Recommendation Agent** — propune reformulări ancorate în legislație
    5. **Raport Markdown** — document final descărcabil

    ### Tipuri de clauze analizate
    | Tip | Legislație | Risc tipic |
    |-----|-----------|------------|
    | Penalități de întârziere | Legea 98/2016, art. 164 | Neplafonat / unilateral |
    | Prelucrare date personale | GDPR art. 13, 14 | Temei legal absent |
    | Clauze de forță majoră | Cod Civil art. 1351 | Definiție ambiguă |
    | Reziliere unilaterală | ANPC, clauze abuzive | Dezechilibru contractual |
    | Răspundere limitată | Cod Civil art. 1355 | Excludere ilegală |
    """)