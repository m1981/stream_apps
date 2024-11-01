import pytest
from src.services.document_processor import DocumentProcessor
from src.domain.document import ChatMessage, ChatMetadata

class MockExtractor:
    def extract_metadata(self):
        return ChatMetadata(version="1.0", type="chat_history")

    def extract_content(self):
        return [
            ChatMessage(
                role="user",
                content="test message",
                message_number=1,
                chat_id="123",
                folder="test",
                title="Test Chat"
            )
        ]

class MockCleaner:
    def clean(self, text: str) -> str:
        return text.strip()

def test_document_processor():
    processor = DocumentProcessor(
        extractor=MockExtractor(),
        cleaners=[MockCleaner()]
    )

    documents = processor.process()
    assert len(documents) == 1
    assert documents[0].metadata["chat_id"] == "123"
    assert documents[0].metadata["folder"] == "test"
