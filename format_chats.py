import json
import sys
from typing import Dict, List
from operator import itemgetter

def format_message(msg: Dict) -> str:
    """Format a single message with minimal line breaks."""
    # Properly escape content
    content = msg["content"].replace('"', '\\"').replace('\n', '\\n')
    return f'{{"role": "{msg["role"]}", "content": "{content}"}}'

def format_messages(messages: List[Dict]) -> str:
    """Format messages array with minimal line breaks."""
    formatted_messages = [format_message(msg) for msg in messages]
    return f'[{", ".join(formatted_messages)}]'

def format_chat(chat: Dict) -> str:
    """Format a single chat entry with minimal line breaks."""
    # Basic chat properties
    result = f'{{"id": "{chat["id"]}", "title": "{chat["title"]}"'
    
    # Messages
    result += f', "messages": {format_messages(chat["messages"])}'
    
    # Config
    if "config" in chat:
        config = chat["config"]
        result += f', "config": {json.dumps(config)}'
    
    # Optional properties
    if "titleSet" in chat:
        result += f', "titleSet": {str(chat["titleSet"]).lower()}'
    if "folder" in chat:
        result += f', "folder": "{chat["folder"]}"'
    if "currentChatTokenCount" in chat:
        result += f', "currentChatTokenCount": {chat["currentChatTokenCount"]}'
    
    result += '}'
    return result

def format_json_file(input_file: str, output_file: str) -> None:
    """
    Read JSON file, sort chats by title, and write formatted output.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Sort chats by title
        if "chats" in data:
            data["chats"].sort(key=itemgetter("title"))
        
        # Format output
        result = "{\n  \"chats\": [\n"
        
        # Format each chat
        if "chats" in data:
            formatted_chats = [f"    {format_chat(chat)}" for chat in data["chats"]]
            result += ",\n".join(formatted_chats)
        
        result += "\n  ]"
        
        # Add folders and version
        if "folders" in data:
            result += f',\n\n  "folders": {json.dumps(data["folders"], indent=4)}'
        if "version" in data:
            result += f',\n  "version": {data["version"]}'
        
        result += "\n}\n"
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
            
        print(f"Successfully formatted JSON from {input_file} to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python format_json.py <input_file> <output_file>")
        sys.exit(1)
    
    format_json_file(sys.argv[1], sys.argv[2])
