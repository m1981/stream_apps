import streamlit as st
import yaml
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
import time

def generate_uuid() -> str:
    return str(uuid.uuid4())

def create_default_folder() -> Dict[str, Any]:
    folder_id = generate_uuid()
    return {
        "folders": {
            folder_id: {
                "id": folder_id,
                "name": "Default",
                "expanded": True,
                "order": 0,
                "color": "#be123c"
            }
        }
    }, folder_id

def convert_messages_array(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert a plain messages array to format_2"""
    try:
        # Create default folder and get its ID
        folder_structure, folder_id = create_default_folder()
        
        # Convert messages to simplified format
        converted_messages = [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in messages
        ]

        # Get model from the first assistant message, if available
        model = next(
            (msg.get("model", "gpt-4") for msg in messages if msg.get("role") == "assistant"),
            "gpt-4"
        )

        # Create chat object
        converted_chat = {
            "id": generate_uuid(),
            "title": "Imported Chat",  # Default title
            "messages": converted_messages,
            "config": {
                "model": model,
                "max_tokens": 8192,
                "temperature": 0.9,
                "top_p": 1,
                "presence_penalty": 0,
                "frequency_penalty": 0
            },
            "titleSet": True,
            "folder": folder_id,
            "currentChatTokenCount": 0
        }

        # Create the final structure
        result = {
            "chats": [converted_chat],
            **folder_structure,
            "version": 1
        }

        return result
    except Exception as e:
        st.error(f"Messages array conversion error: {str(e)}")
        return None

def convert_chat_format(source_data: Any) -> Dict[str, Any]:
    """Convert from any supported format to format_2"""
    try:
        # If input is a list, treat it as messages array
        if isinstance(source_data, list):
            return convert_messages_array(source_data)
        
        # If input is a dict, use the original conversion logic
        elif isinstance(source_data, dict):
            folder_structure, folder_id = create_default_folder()
            
            converted_chat = {
                "id": generate_uuid(),
                "title": source_data.get("name", "Imported Chat"),
                "messages": [
                    {
                        "role": msg["role"],
                        "content": msg["content"]
                    }
                    for msg in source_data.get("context", [])
                ],
                "config": {
                    "model": source_data.get("modelConfig", {}).get("model", "gpt-4"),
                    "max_tokens": source_data.get("modelConfig", {}).get("max_tokens", 8192),
                    "temperature": source_data.get("modelConfig", {}).get("temperature", 0.9),
                    "top_p": 1,
                    "presence_penalty": source_data.get("modelConfig", {}).get("presence_penalty", 0),
                    "frequency_penalty": source_data.get("modelConfig", {}).get("frequency_penalty", 0)
                },
                "titleSet": True,
                "folder": folder_id,
                "currentChatTokenCount": 0
            }

            result = {
                "chats": [converted_chat],
                **folder_structure,
                "version": 1
            }

            return result
        else:
            raise ValueError("Unsupported input format")
            
    except Exception as e:
        st.error(f"Conversion error: {str(e)}")
        return None

def main():

    st.title("Chat Format Converter ?")
    st.markdown("""
    Convert your chat format from Format 1 to Format 2.
    
    1. Upload your source YAML/JSON file or paste the content
    2. Download the converted format
    """)

    # File upload or text input
    input_method = st.radio(
        "Choose input method:",
        ["Upload File", "Paste Content"]
    )

    source_data = None

    if input_method == "Upload File":
        uploaded_file = st.file_uploader("Upload your chat file (YAML or JSON)", 
                                       type=['yaml', 'yml', 'json'])
        if uploaded_file:
            try:
                content = uploaded_file.read().decode('utf-8')
                if uploaded_file.type in ['application/x-yaml', 'application/yaml'] or uploaded_file.name.endswith(('.yml', '.yaml')):
                    source_data = yaml.safe_load(content)
                else:
                    source_data = json.loads(content)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    else:
        content = st.text_area("Paste your chat content (YAML or JSON format)", height=300)
        if content:
            try:
                source_data = yaml.safe_load(content)
            except:
                try:
                    source_data = json.loads(content)
                except Exception as e:
                    st.error(f"Error parsing content: {str(e)}")

    if source_data:
        st.subheader("Source Data Preview")
        with st.expander("Show source data"):
            st.json(source_data)

        if st.button("Convert Format"):
            with st.spinner("Converting..."):
                converted_data = convert_chat_format(source_data)
                
                if converted_data:
                    st.success("Conversion successful!")
                    
                    st.subheader("Converted Data Preview")
                    with st.expander("Show converted data"):
                        st.json(converted_data)

                    # Prepare download button for JSON instead of YAML
                    json_str = json.dumps(converted_data, indent=2, ensure_ascii=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    st.download_button(
                        label="Download Converted JSON",
                        data=json_str,
                        file_name=f"converted_chat_{timestamp}.json",
                        mime="application/json"
                    )

    # Update the instructions to mention JSON output
    st.markdown("---")
    st.markdown("""
    ### Instructions
    - The converter supports both YAML and JSON input formats
    - The output will be in JSON format
    - All message history and basic configuration will be preserved
    - A default folder will be created for organization
    """)

if __name__ == "__main__":
    main()