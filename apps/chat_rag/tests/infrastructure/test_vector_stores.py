import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain.docstore.document import Document
from src.infrastructure.vector_stores import ChromaVectorStore

@pytest.fixture
def mock_embeddings():
    return Mock()

@pytest.fixture
def mock_chromadb_client():
    with patch('chromadb.PersistentClient') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def mock_chroma():
    with patch('langchain_chroma.Chroma') as mock:
        # Create a MagicMock instance with all the necessary methods
        mock_instance = MagicMock()
        mock_instance.get.return_value = {'ids': [1, 2, 3]}
        mock_instance.similarity_search.return_value = [
            Document(page_content="test content", metadata={})
        ]
        # Set the return value of the mock to be our configured instance
        mock.return_value = mock_instance
        yield mock_instance  # Note: yielding the instance, not the mock itself

@pytest.fixture
def vector_store(mock_embeddings, mock_chroma, mock_chromadb_client):
    with patch('os.makedirs'):
        # Mock OpenAIEmbeddings
        with patch('langchain_openai.OpenAIEmbeddings') as mock_openai:
            mock_openai.return_value = mock_embeddings
            store = ChromaVectorStore(
                collection_name="test_collection",
                persist_directory="/tmp/test"
            )
            # Explicitly set the store attribute to our mock
            store.store = mock_chroma
            return store

class TestChromaVectorStore:
    @pytest.mark.parametrize("collection_name,persist_directory", [
        ("", "/tmp/test"),
        ("test", ""),
        (" ", "/tmp/test"),
        ("test", " "),
    ])
    def test_initialization_with_invalid_params(self, collection_name, persist_directory, mock_embeddings):
        with pytest.raises(ValueError):
            ChromaVectorStore(
                collection_name=collection_name,
                persist_directory=persist_directory
            )

    def test_store_documents_valid(self, vector_store):
        docs = [Document(page_content="test content", metadata={"test": "metadata"})]
        vector_store.store_documents(docs)
        vector_store.store.add_documents.assert_called_once_with(docs)

    def test_store_documents_empty_list(self, vector_store):
        with pytest.raises(ValueError, match="Attempting to store empty document list"):
            vector_store.store_documents([])

    def test_store_documents_invalid_type(self, vector_store):
        with pytest.raises(TypeError):
            vector_store.store_documents([{"invalid": "document"}])

    def test_store_documents_empty_content(self, vector_store):
        docs = [Document(page_content="", metadata={"test": "metadata"})]
        with pytest.raises(ValueError, match="Document has empty content"):
            vector_store.store_documents(docs)

    def test_search_valid(self, vector_store):
        results = vector_store.search("test query")
        vector_store.store.similarity_search.assert_called_once_with("test query", k=4)
        assert isinstance(results, list)

    @pytest.mark.parametrize("query,k", [
        ("", 4),
        (" ", 4),
        ("test", 0),
        ("test", -1),
    ])
    def test_search_invalid_params(self, vector_store, query, k):
        with pytest.raises(ValueError):
            vector_store.search(query, k)

    def test_as_retriever_with_documents(self, vector_store):
        # Ensure the get method returns non-empty results
        vector_store.store.get.return_value = {'ids': [1, 2, 3]}
        retriever = vector_store.as_retriever()
        assert retriever == vector_store.store.as_retriever.return_value

    def test_as_retriever_empty_store(self, vector_store):
        vector_store.store.get.return_value = {'ids': []}
        with pytest.raises(ValueError, match="Vector store is empty!"):
            vector_store.as_retriever()

    def test_as_retriever_with_search_kwargs(self, vector_store):
        # Ensure the get method returns non-empty results
        vector_store.store.get.return_value = {'ids': [1, 2, 3]}
        search_kwargs = {"search_type": "mmr", "k": 5}
        retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
        vector_store.store.as_retriever.assert_called_once_with(search_kwargs=search_kwargs)

    def test_context_manager(self, vector_store):
        with vector_store as vs:
            assert vs == vector_store

    @patch('chromadb.PersistentClient')
    def test_initialization_error(self, mock_client):
        mock_client.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            ChromaVectorStore(
                collection_name="test_collection",
                persist_directory="/tmp/test"
            )

    def test_verify_store(self, vector_store):
        vector_store.store.get.return_value = {'ids': [1, 2, 3]}
        count = vector_store.verify_store()
        assert count == 3
        vector_store.store.get.assert_called_once()

    def test_verify_store_empty(self, vector_store):
        vector_store.store.get.return_value = {'ids': []}
        count = vector_store.verify_store()
        assert count == 0
        vector_store.store.get.assert_called_once()

    def test_verify_store_error(self, vector_store):
        vector_store.store.get.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            vector_store.verify_store()