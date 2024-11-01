from dotenv import load_dotenv
from typing import List, Dict
from src.config.settings import Settings
from src.infrastructure.extractors import ChatJsonExtractor
from src.infrastructure.text_processors import (
    HyphenationCleaner,
    NewlineCleaner,
    MultipleNewlineCleaner
)
from src.infrastructure.vector_stores import ChromaVectorStore
from src.services.document_processor import DocumentProcessor
from src.services.chat_service import ChatService
from src.exceptions import DocumentExtractionError, VectorStoreError
import logging

def setup_ingestion(settings: Settings):
    extractor = ChatJsonExtractor("chats.json")
    cleaners = [
        HyphenationCleaner(),
        NewlineCleaner(),
        MultipleNewlineCleaner()
    ]

    processor = DocumentProcessor(extractor, cleaners)
    vector_store = ChromaVectorStore(
        collection_name=settings.COLLECTION_NAME,
        persist_directory=settings.PERSIST_DIRECTORY
    )

    documents = processor.process()
    if not documents:
        raise ValueError("No documents were processed!")
    vector_store.store_documents(documents)

    # Verify storage
    logging.info("Verifying vector store...")
    try:
        # Attempt a simple search to verify the store is working
        test_results = vector_store.search("test", k=1)
        if test_results:
            logging.info("Vector store verification successful")
        else:
            raise VectorStoreError("Vector store returned no results in verification")
    except Exception as e:
        raise VectorStoreError("Failed to verify vector store operation")

    return vector_store

def main():
    load_dotenv()
    settings = Settings()

    if len(sys.argv) > 1 and sys.argv[1] == '--ingest':
        vector_store = setup_ingestion(settings)
        print("Ingestion completed successfully")
        return

    # Chat mode
    vector_store = ChromaVectorStore(
        collection_name=settings.COLLECTION_NAME,
        persist_directory=settings.PERSIST_DIRECTORY
    )

    chat_service = ChatService(
        vector_store=vector_store,
        model_name=settings.MODEL_NAME,
        temperature=settings.TEMPERATURE
    )

    run_chat_loop(chat_service)

def run_chat_loop(chat_service: ChatService):
    """Separate chat loop for better separation of concerns"""
    print("Chat initialized. Type 'exit' or 'quit' to end the session.")

    while True:
        try:
            question = input("\nQuestion: ").strip()
            if not question:
                continue

            if question.lower() in ['exit', 'quit']:
                break

            answer, sources = chat_service.process_query(question)
            display_results(answer, sources)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            logging.error(f"Error during chat: {str(e)}", exc_info=True)

def display_results(answer: str, sources: List[Dict]):
    """Separate function for displaying results"""
    print("\nSources:")
    for source in sources:
        print(f"\nFolder: {source['folder']}")
        print(f"  - {source['title']} (message: {source['message_number']})")
        print(f"Text chunk: {source['content']}...")
    print(f"\nAnswer: {answer}")

# Add proper logging configuration
import logging
import sys
from pathlib import Path

def setup_logging():
    """Configure logging for the application"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

# Updated main.py
if __name__ == "__main__":
    try:
        setup_logging()
        main()
    except Exception as e:
        logging.error(f"Application failed: {str(e)}", exc_info=True)
        sys.exit(1)