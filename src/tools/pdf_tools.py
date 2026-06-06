import os
from pathlib import Path

import pdfplumber


def load_corpus(corpus_dir: str):
    """
    Parcurge recursiv folderul corpus/ si extrage textul din toate PDF-urile gasite.

    Returneaza o lista de dictionare cu:
    - text: continutul extras din PDF
    - metadata: informatii utile pentru citarea sursei in RAG
    """

    documents = []
    corpus_path = Path(corpus_dir)

    if not corpus_path.exists():
        raise FileNotFoundError(f"Folderul corpus nu exista: {corpus_dir}")

    for pdf_path in corpus_path.rglob("*.pdf"):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []

                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text)

                full_text = "\n".join(text_parts).strip()

                if not full_text:
                    print(f"Atentie: text gol extras din {pdf_path}")
                    continue

                documents.append({
                    "text": full_text,
                    "metadata": {
                        "source": pdf_path.name,
                        "path": str(pdf_path),
                        "type": pdf_path.parent.name,
                        "page_count": len(pdf.pages)
                    }
                })

        except Exception as e:
            print(f"Eroare la citirea PDF-ului {pdf_path}: {e}")

    return documents