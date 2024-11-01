from typing import List, Optional, Dict
from typing import Any
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from src.domain.interfaces import VectorStore
from src.domain.document import ChatMessage
import logging

class ChromaVectorStore(VectorStore):
    DEFAULT_K = 4
    MIN_K = 1

    def __init__(self,
                 collection_name: str,
                 persist_directory: str,
                 embedding_model: Optional[Any] = None):
        if not collection_name.strip():
            raise ValueError("Collection name cannot be empty")
        if not persist_directory.strip():
            raise ValueError("Persist directory cannot be empty")

        try:
            self.embedding_model = embedding_model or OpenAIEmbeddings()
            self.store = Chroma(
                collection_name=collection_name,
                embedding_function=self.embedding_model,
                persist_directory=persist_directory
            )
        except Exception as e:
            logging.error(f"Failed to initialize ChromaVectorStore: {str(e)}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if hasattr(self, 'store'):
            self.store.persist()

    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None) -> Any:
        collection_size = len(self.store.get())
        logging.info(f"Vector store contains {collection_size} documents")
        if collection_size == 0:
            raise ValueError("Vector store is empty!")

        # Pass search_kwargs if provided
        if search_kwargs:
            return self.store.as_retriever(search_kwargs=search_kwargs)
        return self.store.as_retriever()

    def store_documents(self, documents: List[Document]) -> None:
        if not documents:
            raise ValueError("Attempting to store empty document list")
        for doc in documents:
            if not isinstance(doc, Document):
                raise TypeError(f"Expected Document type, got {type(doc)}")
            if not doc.page_content:
                raise ValueError(f"Document has empty content: {doc.metadata}")
        self.store.from_documents(documents, self.embedding_model)
        logging.info(f"Successfully stored {len(documents)} documents")

    def search(self, query: str, k: int = DEFAULT_K) -> List[Document]:
        if k < self.MIN_K:
            raise ValueError(f"k must be >= {self.MIN_K}")
        if not query.strip():
            raise ValueError("Query string cannot be empty")
        return self.store.similarity_search(query, k=k)
