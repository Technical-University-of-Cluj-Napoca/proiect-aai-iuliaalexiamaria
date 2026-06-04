import os
import pdfplumber


def load_corpus(corpus_dir: str):
    documents = []

    for root, dirs, files in os.walk(corpus_dir):
        for file in files:

            if not file.lower().endswith(".pdf"):
                continue

            path = os.path.join(root, file)

            try:
                with pdfplumber.open(path) as pdf:

                    text = ""

                    for page in pdf.pages:
                        page_text = page.extract_text()

                        if page_text:
                            text += page_text + "\n"

                    documents.append({
                        "text": text,
                        "metadata": {
                            "source": file,
                            "path": path,
                            "type": os.path.basename(root),
                            "page_count": len(pdf.pages)
                        }
                    })

            except Exception as e:
                print(f"Eroare la {path}: {e}")

    return documents