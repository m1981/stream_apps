from typing import List, Optional, Dict
from typing import Any
from langchain.docstore.document import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from src.domain.interfaces import VectorStore
from src.domain.document import ChatMessage
import chromadb
from chromadb.config import Settings
import logging
import os

class ChromaVectorStore(VectorStore):
    DEFAULT_K = 4
    MIN_K = 1

    def __init__(self,
                 collection_name: str,
                 persist_directory: str,
                 embedding_model = "text-embedding-3-large"):
        if not collection_name.strip():
            raise ValueError("Collection name cannot be empty")
        if not persist_directory.strip():
            raise ValueError("Persist directory cannot be empty")
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)

        try:
            # Create Chroma client with new configuration
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )

            self.embedding_model = OpenAIEmbeddings(model=embedding_model)
            
            # Initialize Langchain's Chroma wrapper
            self.store = Chroma(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embedding_model,
            )
            
        except Exception as e:
            logging.error(f"Failed to initialize ChromaVectorStore: {str(e)}")
            raise

    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None) -> Any:
        collection_size = self.verify_store()
        if collection_size == 0:
            raise ValueError("Vector store is empty!")

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
        
        # Use add_documents instead of from_documents
        self.store.add_documents(documents)
        logging.info(f"Successfully stored {len(documents)} documents")

    def search(self, query: str, k: int = DEFAULT_K) -> List[Document]:
        if k < self.MIN_K:
            raise ValueError(f"k must be >= {self.MIN_K}")
        if not query.strip():
            raise ValueError("Query string cannot be empty")
        return self.store.similarity_search(query, k=k)

    def verify_store(self) -> int:
        try:
            collection = self.store.get()
            count = len(collection['ids']) if collection else 0
            logging.info(f"Vector store contains {count} documents")
            return count
        except Exception as e:
            logging.error(f"Failed to verify vector store: {str(e)}")
            raise
