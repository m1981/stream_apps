import pytest
from unittest.mock import Mock, patch
from langchain.docstore.document import Document
from src.infrastructure.vector_stores import ChromaVectorStore

@pytest.fixture
def mock_embeddings():
    return Mock()

@pytest.fixture
def mock_chroma():
    with patch('src.infrastructure.vector_stores.Chroma') as mock:
        # Configure the mock
        mock_instance = mock.return_value
        mock_instance.get.return_value = [1, 2, 3]  # Simulate 3 documents
        mock_instance.similarity_search.return_value = [
            Document(page_content="test content", metadata={})
        ]
        yield mock

@pytest.fixture
def vector_store(mock_embeddings, mock_chroma):
    return ChromaVectorStore(
        collection_name="test_collection",
        persist_directory="/tmp/test",
        embedding_model=mock_embeddings
    )

class TestChromaVectorStore:
    def test_initialization_with_valid_params(self, mock_embeddings, mock_chroma):
        store = ChromaVectorStore(
            collection_name="test_collection",
            persist_directory="/tmp/test",
            embedding_model=mock_embeddings
        )
        assert store.embedding_model == mock_embeddings

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
                persist_directory=persist_directory,
                embedding_model=mock_embeddings
            )

    def test_store_documents_valid(self, vector_store):
        docs = [Document(page_content="test content", metadata={"test": "metadata"})]
        vector_store.store_documents(docs)
        vector_store.store.from_documents.assert_called_once()

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
        retriever = vector_store.as_retriever()
        assert retriever == vector_store.store.as_retriever()

    def test_as_retriever_empty_store(self, vector_store):
        vector_store.store.get.return_value = []
        with pytest.raises(ValueError, match="Vector store is empty!"):
            vector_store.as_retriever()

    def test_as_retriever_with_search_kwargs(self, vector_store):
        search_kwargs = {"search_type": "mmr", "k": 5}
        retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
        vector_store.store.as_retriever.assert_called_once_with(search_kwargs=search_kwargs)

    def test_context_manager(self, vector_store):
        with vector_store as vs:
            assert vs == vector_store
        vector_store.store.persist.assert_called_once()

    @patch('src.infrastructure.vector_stores.Chroma')
    def test_initialization_error(self, mock_chroma):
        mock_chroma.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            ChromaVectorStore(
                collection_name="test_collection",
                persist_directory="/tmp/test"
            )