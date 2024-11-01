from typing import List, Optional, Dict
from typing import Any
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from src.domain.interfaces import VectorStore
from src.domain.document import ChatMessage
import logging

class ChromaVectorStore(VectorStore):
    def __init__(self,
                 collection_name: str,
                 persist_directory: str,
                 embedding_model: Optional[Any] = None):
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_model,
            persist_directory=persist_directory
        )

    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None) -> Any:
        collection_size = len(self.store.get())
        logging.info(f"Vector store contains {collection_size} documents")
        if collection_size == 0:
            logging.warning("Vector store is empty!")

        # Pass search_kwargs if provided
        if search_kwargs:
            return self.store.as_retriever(search_kwargs=search_kwargs)
        return self.store.as_retriever()

    def store_documents(self, documents: List[Document]) -> None:
        self.store.from_documents(documents, self.embedding_model)

    def search(self, query: str, k: int = 4) -> List[Document]:
        return self.store.similarity_search(query, k=k)
