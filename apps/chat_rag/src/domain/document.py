from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ChatMessage:
    role: str
    content: str
    message_number: int
    chat_id: str
    folder: str
    title: str

@dataclass
class ChatMetadata:
    version: str
    type: str
    folder: Optional[str] = None
    title: Optional[str] = None
    chat_id: Optional[str] = None