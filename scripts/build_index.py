import os
import sys

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.tools.pdf_tools import load_corpus
from src.tools.vector_tools import build_index


CORPUS_DIR = os.path.join(BASE_DIR, "corpus")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore")

if __name__ == "__main__":
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    if os.path.exists(VECTORSTORE_DIR) and os.listdir(VECTORSTORE_DIR):
        print("vectorstore/ exista deja. Sterge continutul daca vrei sa reindexezi.")
        exit()

    documents = load_corpus(CORPUS_DIR)

    print(f"Documente incarcate: {len(documents)}")

    if len(documents) == 0:
        print("Nu exista PDF-uri valide in corpus/.")
        exit()

    build_index(documents, persist_directory=VECTORSTORE_DIR)

    print("Indexarea a fost finalizata.")