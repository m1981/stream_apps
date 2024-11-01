class ChatProcessingError(Exception):
    """Base exception for chat processing errors"""
    pass

class DocumentExtractionError(ChatProcessingError):
    """Raised when document extraction fails"""
    pass

class VectorStoreError(ChatProcessingError):
    """Raised when vector store operations fail"""
    pass