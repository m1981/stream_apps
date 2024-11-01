# tests/infrastructure/test_extractors.py

import pytest
from pathlib import Path
import json
import tempfile
from src.infrastructure.extractors import ChatJsonExtractor
from src.domain.document import ChatMessage, ChatMetadata
from src.exceptions import DocumentExtractionError

@pytest.fixture
def valid_chat_data():
    return {
        "version": "1",
        "chats": [
            {
                "id": "chat-123",
                "title": "Test Chat",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"}
                ],
                "folder": "folder-123"
            }
        ],
        "folders": {
            "folder-123": {
                "id": "folder-123",
                "name": "Test Folder",
                "expanded": True,
                "order": 0,
                "color": "#be123c"
            }
        }
    }

@pytest.fixture
def valid_json_file(tmp_path, valid_chat_data):
    # Using pytest's tmp_path fixture for better test isolation
    json_file = tmp_path / "test_chat.json"
    with json_file.open('w') as f:
        json.dump(valid_chat_data, f)
    return str(json_file)

@pytest.fixture
def chat_extractor(valid_json_file):
    return ChatJsonExtractor(valid_json_file)

class TestChatJsonExtractor:
    def test_initialization_with_valid_file(self, valid_json_file):
        extractor = ChatJsonExtractor(valid_json_file)
        assert extractor.file_path == valid_json_file
        assert extractor.data is not None

    def test_initialization_with_invalid_file(self):
        with pytest.raises(DocumentExtractionError) as exc_info:
            ChatJsonExtractor("nonexistent_file.json")
        assert "Failed to load JSON file" in str(exc_info.value)

    def test_initialization_with_invalid_json(self, tmp_path):
        invalid_json_file = tmp_path / "invalid.json"
        with invalid_json_file.open('w') as f:
            f.write("invalid json content")

        with pytest.raises(DocumentExtractionError) as exc_info:
            ChatJsonExtractor(str(invalid_json_file))
        assert "Failed to load JSON file" in str(exc_info.value)

    def test_extract_metadata(self, chat_extractor):
        metadata = chat_extractor.extract_metadata()
        assert isinstance(metadata, ChatMetadata)
        assert metadata.version == "1"
        assert metadata.type == "chat_history"

    def test_extract_content_with_valid_data(self, chat_extractor):
        messages = chat_extractor.extract_content()
        assert len(messages) == 2
        assert all(isinstance(msg, ChatMessage) for msg in messages)
        
        # Verify first message
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[0].message_number == 1
        assert messages[0].chat_id == "chat-123"
        assert messages[0].folder == "Test Folder"
        assert messages[0].title == "Test Chat"

        # Verify second message
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there"
        assert messages[1].message_number == 2

    def test_extract_content_with_missing_folder(self, tmp_path, valid_chat_data):
        # Modify data to test missing folder scenario
        valid_chat_data["chats"][0]["folder"] = "non-existent-folder"
        
        test_file = tmp_path / "test_missing_folder.json"
        with test_file.open('w') as f:
            json.dump(valid_chat_data, f)

        extractor = ChatJsonExtractor(str(test_file))
        messages = extractor.extract_content()
        
        assert messages[0].folder == "No Folder"

    def test_extract_content_with_missing_title(self, tmp_path, valid_chat_data):
        # Remove title from chat
        del valid_chat_data["chats"][0]["title"]
        
        test_file = tmp_path / "test_missing_title.json"
        with test_file.open('w') as f:
            json.dump(valid_chat_data, f)

        extractor = ChatJsonExtractor(str(test_file))
        messages = extractor.extract_content()
        
        assert messages[0].title == "Untitled Chat"

    def test_extract_content_with_empty_but_valid_structure(self, tmp_path):
        valid_empty_data = {
            "version": "1",
            "chats": [],
            "folders": {}
        }

        test_file = tmp_path / "test_empty.json"
        with test_file.open('w') as f:
            json.dump(valid_empty_data, f)

        extractor = ChatJsonExtractor(str(test_file))
        messages = extractor.extract_content()
        assert len(messages) == 0

    @pytest.mark.parametrize("invalid_data, expected_error", [
        (
            {"version": "1"},  # Missing chats
            "'chats' must be a list"
        ),
        (
            {"chats": []},     # Missing version but valid structure
            None  # This should actually pass validation
        ),
        (
            None,              # None data
            "Root element must be a dictionary"
        ),
    ])
    def test_extract_content_with_invalid_data(self, tmp_path, invalid_data, expected_error):
        test_file = tmp_path / "test_invalid.json"
        with test_file.open('w') as f:
            json.dump(invalid_data if invalid_data is not None else "null", f)

        if expected_error:
            with pytest.raises(DocumentExtractionError) as exc_info:
                ChatJsonExtractor(str(test_file))
            assert expected_error in str(exc_info.value)
        else:
            extractor = ChatJsonExtractor(str(test_file))
            messages = extractor.extract_content()
            assert len(messages) == 0

    @pytest.mark.parametrize("malformed_data, expected_error", [
        (
            {"version": "1", "chats": "invalid_string"},
            "'chats' must be a list"
        ),
        (
            {"version": "1", "chats": [{"messages": "invalid"}]},
            "Chat messages must be a list"
        ),
        (
            {"version": "1", "chats": [{"messages": [{"role": 123, "content": "test"}]}]},
            "Message role must be a string"
        ),
        (
            {"version": "1", "chats": [{"messages": [{"role": "user", "content": 123}]}]},
            "Message content must be a string"
        ),
        (
            {"version": "1", "chats": [{"messages": [{}]}]},
            "Message role must be a string"
        ),
    ])
    def test_extract_content_with_malformed_data(self, tmp_path, malformed_data, expected_error):
        test_file = tmp_path / "test_malformed.json"
        with test_file.open('w') as f:
            json.dump(malformed_data, f)

        with pytest.raises(DocumentExtractionError) as exc_info:
            if "chats" not in malformed_data or not isinstance(malformed_data["chats"], list):
                ChatJsonExtractor(str(test_file))
            else:
                extractor = ChatJsonExtractor(str(test_file))
                extractor.extract_content()
        assert expected_error in str(exc_info.value)


    def test_extract_content_with_minimal_valid_structure(self, tmp_path):
        minimal_valid_data = {
            "chats": [
                {
                    "id": "test-id",
                    "messages": [
                        {
                            "role": "user",
                            "content": "test message"
                        }
                    ]
                }
            ]
        }

        test_file = tmp_path / "test_minimal.json"
        with test_file.open('w') as f:
            json.dump(minimal_valid_data, f)

        extractor = ChatJsonExtractor(str(test_file))
        messages = extractor.extract_content()
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "test message"