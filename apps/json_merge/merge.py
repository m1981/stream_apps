import json
import sys
import logging
from typing import Dict, List
from pathlib import Path
from datetime import datetime
from copy import deepcopy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatMerger:
    def __init__(self):
        self.merged_data = {
            "chats": [],
            "folders": {},
            "version": 1
        }
        
    def load_json_file(self, file_path: Path) -> dict:
        """Safely load and validate JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate basic structure
            if not isinstance(data, dict):
                raise ValueError("JSON root must be an object")
            if "chats" not in data or "folders" not in data:
                raise ValueError("JSON must contain 'chats' and 'folders' keys")
                
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    def merge_chats(self, source1: dict, source2: dict) -> None:
        """Merge two chat data structures."""
        # Track existing IDs to avoid duplicates
        existing_chat_ids = set()
        existing_folder_ids = set()

        # Helper function to add chats
        def add_chats(chats: List[dict]):
            for chat in chats:
                if chat['id'] not in existing_chat_ids:
                    self.merged_data['chats'].append(deepcopy(chat))
                    existing_chat_ids.add(chat['id'])
                else:
                    logger.warning(f"Duplicate chat ID found: {chat['id']}, skipping...")

        # Helper function to add folders
        def add_folders(folders: Dict[str, dict]):
            for folder_id, folder in folders.items():
                if folder_id not in existing_folder_ids:
                    self.merged_data['folders'][folder_id] = deepcopy(folder)
                    existing_folder_ids.add(folder_id)
                else:
                    logger.warning(f"Duplicate folder ID found: {folder_id}, keeping original...")

        # Merge data from both sources
        add_chats(source1['chats'])
        add_chats(source2['chats'])
        add_folders(source1['folders'])
        add_folders(source2['folders'])

    def save_merged_file(self, output_path: Path) -> None:
        """Save merged data to a new JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.merged_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved merged data to {output_path}")
        except Exception as e:
            logger.error(f"Error saving merged file: {e}")
            raise

def main():
    if len(sys.argv) != 4:
        print("Usage: python chat_merger.py <file1.json> <file2.json> <output.json>")
        sys.exit(1)

    # Create paths
    file1_path = Path(sys.argv[1])
    file2_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    # Validate input files exist
    if not file1_path.exists() or not file2_path.exists():
        logger.error("One or both input files do not exist!")
        sys.exit(1)

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = output_path.parent / f"backup_{timestamp}_{output_path.name}"

    try:
        merger = ChatMerger()
        
        # Load both files
        logger.info(f"Loading {file1_path}")
        data1 = merger.load_json_file(file1_path)
        logger.info(f"Loading {file2_path}")
        data2 = merger.load_json_file(file2_path)

        # If output file exists, create backup
        if output_path.exists():
            import shutil
            shutil.copy2(output_path, backup_path)
            logger.info(f"Created backup at {backup_path}")

        # Perform merge
        merger.merge_chats(data1, data2)

        # Save result
        merger.save_merged_file(output_path)
        
        logger.info("Merge completed successfully!")
        logger.info(f"Total chats: {len(merger.merged_data['chats'])}")
        logger.info(f"Total folders: {len(merger.merged_data['folders'])}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
