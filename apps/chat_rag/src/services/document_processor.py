# src/services/document_processor.py
from typing import List, Dict
from langchain.docstore.document import Document
from src.domain.interfaces import DocumentExtractor, TextCleaner
from src.domain.document import ChatMessage, ChatMetadata
import logging

class DocumentProcessor:
    def __init__(self, 
                 extractor: DocumentExtractor,
                 cleaners: List[TextCleaner]):
        self.extractor = extractor
        self.cleaners = cleaners

    def process(self) -> List[Document]:
        metadata = self.extractor.extract_metadata()
        messages = self.extractor.extract_content()
        return self._create_documents(messages, metadata)

    def _clean_text(self, text: str) -> str:
        for cleaner in self.cleaners:
            text = cleaner.clean(text)
        return text

    def _create_documents(self, 
                         messages: List[ChatMessage], 
                         metadata: ChatMetadata) -> List[Document]:
        documents = []
        base_metadata = {
            "version": metadata.version,
            "type": metadata.type
        }
        
        for message in messages:
            cleaned_content = self._clean_text(message.content)
            if len(cleaned_content) < 10:
                continue
            # Combine message-specific metadata with base metadata
            document_metadata = {
                **base_metadata,
                "message_number": message.message_number,
                "chat_id": message.chat_id,
                "folder": message.folder,
                "title": message.title,
                "role": message.role
            }
            
            # Create formatted content with context
            formatted_content = self._format_content(message, cleaned_content)
            logging.info(f"Formatted: \n{cleaned_content}")
            logging.info(document_metadata)
            doc = Document(
                page_content=formatted_content,
                metadata=document_metadata
            )
            documents.append(doc)
        
        return documents

    def _format_content(self, message: ChatMessage, cleaned_content: str) -> str:
        """Format the content with contextual information"""
        return (
            f"Folder: {message.folder}\n"
            f"Chat: {message.title}\n"
            f"Role: {message.role}\n"
            f"Content: {cleaned_content}\n"
            f"---\n"
        )
