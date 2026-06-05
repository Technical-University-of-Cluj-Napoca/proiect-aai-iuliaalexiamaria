# src/agents/retrieval_agent.py
import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from src.dtos import RetrievalResultDTO


class RAGRetrievalAgent:
    def __init__(self, vectorstore_path="vectorstore"):
        """Initializes the persistent vector store without re-indexing."""
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        if not os.path.exists(vectorstore_path):
            raise FileNotFoundError(f"Vectorstore not found at {vectorstore_path}. Please run build_index.py first.")

        self.vectorstore = Chroma(
            persist_directory=vectorstore_path,
            embedding_function=embeddings
        )

    def retrieve(self, clause_text: str, k: int = 5, iteration: int = 0) -> list[RetrievalResultDTO]:
        """
        Retrieves relevant legal documents for a given clause text.
        Applies parameter adaptation if triggered by a feedback retry loop.
        """
        current_k = k if iteration == 0 else k + 3

        base_threshold = 1.0 if iteration == 0 else 1.3

        results_with_scores = self.vectorstore.similarity_search_with_score(clause_text, k=current_k)

        retrieved_dtos = []
        for doc, score in results_with_scores:
            print(f"   [DEBUG CHROMA] Gasit text in {doc.metadata.get('source')}, Distanta L2: {score:.4f}")

            if score <= base_threshold:  #
                retrieved_dtos.append(
                    RetrievalResultDTO(
                        text=doc.page_content,
                        source=doc.metadata.get("source", "unknown_source.pdf"),
                        score=float(score)
                    )
                )

        retrieved_dtos.sort(key=lambda x: x.score)
        return retrieved_dtos