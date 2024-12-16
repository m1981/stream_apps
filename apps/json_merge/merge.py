import json
import sys
import logging
import argparse
from typing import Dict, List, Set
from pathlib import Path
from datetime import datetime
from copy import deepcopy

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

    def get_folder_ids_by_names(self, data: dict, folder_names: Set[str]) -> Set[str]:
        """Get folder IDs from folder names."""
        folder_ids = set()
        for folder_id, folder in data['folders'].items():
            if folder['name'] in folder_names:
                folder_ids.add(folder_id)
                logger.info(f"Found folder: {folder['name']} (ID: {folder_id})")
        return folder_ids

    def merge_chats(self, source1: dict, source2: dict, folder_names: Set[str] = None) -> None:
        """Merge chats, optionally filtering by folder names."""
        existing_chat_ids = set()
        existing_folder_ids = set()

        # If folder names specified, get corresponding folder IDs
        selected_folder_ids = set()
        if folder_names:
            selected_folder_ids.update(self.get_folder_ids_by_names(source1, folder_names))
            selected_folder_ids.update(self.get_folder_ids_by_names(source2, folder_names))
            if not selected_folder_ids:
                logger.warning(f"No folders found matching names: {folder_names}")
                return

        def add_chats(chats: List[dict]):
            for chat in chats:
                # Skip if chat doesn't belong to selected folders
                if folder_names and chat.get('folder') not in selected_folder_ids:
                    continue
                
                if chat['id'] not in existing_chat_ids:
                    self.merged_data['chats'].append(deepcopy(chat))
                    existing_chat_ids.add(chat['id'])
                    # Add the associated folder if not already present
                    if chat.get('folder'):
                        existing_folder_ids.add(chat['folder'])
                else:
                    logger.warning(f"Duplicate chat ID found: {chat['id']}, skipping...")

        def add_folders(folders: Dict[str, dict]):
            for folder_id, folder in folders.items():
                # Only add folders that are associated with selected chats
                if folder_id in existing_folder_ids:
                    if folder_id not in self.merged_data['folders']:
                        self.merged_data['folders'][folder_id] = deepcopy(folder)

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

    def list_folders(self, data: dict) -> None:
        """List all folders in the data."""
        logger.info("Available folders:")
        for folder_id, folder in data['folders'].items():
            logger.info(f"- {folder['name']} (ID: {folder_id})")

def main():
    parser = argparse.ArgumentParser(description='Merge chat JSON files with optional folder filtering')
    parser.add_argument('file1', type=str, help='First JSON file')
    parser.add_argument('file2', type=str, help='Second JSON file')
    parser.add_argument('output', type=str, help='Output JSON file')
    parser.add_argument('--folders', type=str, nargs='+', help='Folder names to include in merge')
    parser.add_argument('--list-folders', action='store_true', help='List available folders and exit')
    
    args = parser.parse_args()

    # Create paths
    file1_path = Path(args.file1)
    file2_path = Path(args.file2)
    output_path = Path(args.output)

    # Validate input files exist
    if not file1_path.exists() or not file2_path.exists():
        logger.error("One or both input files do not exist!")
        sys.exit(1)

    try:
        merger = ChatMerger()
        
        # Load both files
        logger.info(f"Loading {file1_path}")
        data1 = merger.load_json_file(file1_path)
        logger.info(f"Loading {file2_path}")
        data2 = merger.load_json_file(file2_path)

        # If --list-folders flag is set, show folders and exit
        if args.list_folders:
            logger.info("\nFolders in first file:")
            merger.list_folders(data1)
            logger.info("\nFolders in second file:")
            merger.list_folders(data2)
            return

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = output_path.parent / f"backup_{timestamp}_{output_path.name}"

        # If output file exists, create backup
        if output_path.exists():
            import shutil
            shutil.copy2(output_path, backup_path)
            logger.info(f"Created backup at {backup_path}")

        # Convert folder names to set if provided
        folder_names = set(args.folders) if args.folders else None
        if folder_names:
            logger.info(f"Filtering chats from folders: {folder_names}")

        # Perform merge
        merger.merge_chats(data1, data2, folder_names)

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
