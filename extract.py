import json
import sys
from typing import Dict, List
from pathlib import Path
import argparse
from rich import print as rprint
from rich.console import Console
from rich.prompt import Prompt

console = Console()

class ChatExporter:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.data = self._load_json()

    def _load_json(self) -> dict:
        """Load and validate the JSON file"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Basic validation
                if not all(key in data for key in ['chats', 'folders']):
                    raise ValueError("Invalid JSON structure: missing required keys")
                return data
        except FileNotFoundError:
            console.print(f"[red]Error: File {self.input_file} not found[/red]")
            sys.exit(1)
        except json.JSONDecodeError:
            console.print(f"[red]Error: Invalid JSON in {self.input_file}[/red]")
            sys.exit(1)

    def display_folders(self) -> None:
        """Display available folders with their names and colors"""
        console.print("\n[bold]Available folders:[/bold]")
        for folder_id, folder in self.data['folders'].items():
            console.print(f"- {folder['name']} ({folder_id}) [color={folder['color']}]?[/color]")

    def select_folders(self) -> List[str]:
        """Let user select folders interactively"""
        selected_folders = []
        while True:
            folder_id = Prompt.ask(
                "\nEnter folder ID to export (or press Enter to finish)",
                default=""
            )
            if not folder_id:
                break
            if folder_id in self.data['folders']:
                selected_folders.append(folder_id)
                console.print(f"[green]Added folder: {self.data['folders'][folder_id]['name']}[/green]")
            else:
                console.print("[red]Invalid folder ID[/red]")
        return selected_folders

    def export_chats(self, folder_ids: List[str], output_file: str) -> None:
        """Export chats from selected folders to a new JSON file"""
        exported_data = {
            "chats": [
                chat for chat in self.data['chats']
                if chat.get('folder') in folder_ids
            ],
            "folders": {
                folder_id: folder_data
                for folder_id, folder_data in self.data['folders'].items()
                if folder_id in folder_ids
            },
            "version": self.data.get('version', 1)
        }

        # Save exported data
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(exported_data, f, indent=2, ensure_ascii=False)
            console.print(f"\n[green]Successfully exported to {output_file}[/green]")
            console.print(f"Exported {len(exported_data['chats'])} chats from {len(folder_ids)} folders")
        except Exception as e:
            console.print(f"[red]Error saving file: {str(e)}[/red]")

def main():
    parser = argparse.ArgumentParser(description='Export chats from specific folders')
    parser.add_argument('input_file', help='Input JSON file path')
    parser.add_argument('--output', '-o', default='exported_chats.json',
                        help='Output JSON file path (default: exported_chats.json)')

    args = parser.parse_args()

    # Create exporter instance
    exporter = ChatExporter(args.input_file)

    # Show available folders
    exporter.display_folders()

    # Let user select folders
    selected_folders = exporter.select_folders()

    if not selected_folders:
        console.print("[yellow]No folders selected. Exiting.[/yellow]")
        return

    # Export selected chats
    exporter.export_chats(selected_folders, args.output)

if __name__ == "__main__":
    main()
