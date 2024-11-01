import json
from typing import List, Dict, Any
from src.domain.interfaces import DocumentExtractor
from src.domain.document import ChatMessage, ChatMetadata
from src.exceptions import DocumentExtractionError

class ChatJsonExtractor(DocumentExtractor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        try:
            self.data = self._load_json()
            self._validate_data_structure()
        except Exception as e:
            raise DocumentExtractionError(f"Failed to load JSON file: {str(e)}")

    def _load_json(self) -> Dict:
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _validate_data_structure(self) -> None:
        """Validate the basic structure of the loaded JSON data"""
        if not isinstance(self.data, dict):
            raise DocumentExtractionError("Root element must be a dictionary")
        
        chats = self.data.get("chats")
        if not isinstance(chats, list):
            raise DocumentExtractionError("'chats' must be a list")

        folders = self.data.get("folders")
        if folders is not None and not isinstance(folders, dict):
            raise DocumentExtractionError("'folders' must be a dictionary")

    def _get_folder_name(self, chat: Dict[str, Any]) -> str:
        """Extract folder name from chat data safely"""
        try:
            folder_id = chat.get("folder")
            if not folder_id:
                return "No Folder"
            
            folders = self.data.get("folders", {})
            folder = folders.get(folder_id)
            if not folder or not isinstance(folder, dict):
                return "No Folder"
                
            return folder.get("name", "No Folder")
        except Exception as e:
            raise DocumentExtractionError(f"Failed to extract folder name: {str(e)}")

    def _validate_message(self, msg: Dict[str, Any]) -> None:
        """Validate individual message structure"""
        if not isinstance(msg, dict):
            raise DocumentExtractionError("Message must be a dictionary")
        
        if not isinstance(msg.get("role"), str):
            raise DocumentExtractionError("Message role must be a string")
            
        if not isinstance(msg.get("content"), str):
            raise DocumentExtractionError("Message content must be a string")

    def extract_metadata(self) -> ChatMetadata:
        try:
            return ChatMetadata(
                version=str(self.data.get("version", "unknown")),
                type="chat_history"
            )
        except Exception as e:
            raise DocumentExtractionError(f"Failed to extract metadata: {str(e)}")

    def extract_content(self) -> List[ChatMessage]:
        messages = []
        message_counter = 0
        
        try:
            for chat in self.data.get("chats", []):
                if not isinstance(chat, dict):
                    raise DocumentExtractionError("Each chat must be a dictionary")
                
                folder_name = self._get_folder_name(chat)
                
                chat_messages = chat.get("messages", [])
                if not isinstance(chat_messages, list):
                    raise DocumentExtractionError("Chat messages must be a list")
                
                for msg in chat_messages:
                    self._validate_message(msg)
                    message_counter += 1
                    messages.append(
                        ChatMessage(
                            role=msg['role'],
                            content=msg['content'],
                            message_number=message_counter,
                            chat_id=chat.get('id', 'unknown'),
                            folder=folder_name,
                            title=chat.get('title', 'Untitled Chat')
                        )
                    )
        except DocumentExtractionError as e:
            raise e
        except Exception as e:
            raise DocumentExtractionError(f"Failed to extract content: {str(e)}")
            
        return messages
