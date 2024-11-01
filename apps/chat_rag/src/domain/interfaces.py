from abc import ABC, abstractmethod
from typing import List, Dict, Protocol, Any, Optional
from langchain.docstore.document import Document
from .document import ChatMessage, ChatMetadata

class DocumentExtractor(ABC):
    @abstractmethod
    def extract_metadata(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def extract_content(self) -> List[Any]:
        pass

class TextCleaner(Protocol):
    def clean(self, text: str) -> str:
        pass

class VectorStore(Protocol):
    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        pass

    def store_documents(self, documents: List[Document]) -> None:
        pass


    def search(self, query: str, k: int) -> List[Document]:
        pass
