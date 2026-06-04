from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


def build_index(documents, persist_directory="vectorstore/"):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    langchain_docs = []

    for doc in documents:
        chunks = splitter.split_text(doc["text"])

        for chunk in chunks:
            langchain_docs.append(
                Document(
                    page_content=chunk,
                    metadata=doc["metadata"]
                )
            )

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vectorstore = Chroma.from_documents(
        documents=langchain_docs,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    return vectorstore