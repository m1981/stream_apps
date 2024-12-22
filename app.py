import streamlit as st
import pytest
from pathlib import Path
import time
import subprocess
import sys
import os
from typing import Tuple

# Your existing imports
from apps.json_format import app as json_format
from apps.chat_converter import app as chat_converter
from apps.json_merge import app as json_merge
from apps.chat1 import app as chat1
from apps.ynab import app as ynab
from apps.wallet import app as wallet
from apps.todo import app as todo

PAGES = {
    "Todo": ("todo", todo),
    "Wallet 2 YNAB": ("wallet", wallet),
    "YNAB converter": ("ynab", ynab),
    "Chat": ("chat1", chat1),
    "Chat Converter": ("chat_converter", chat_converter),
    "Json formatter": ("json_format", json_format),
    "Json merge": ("json_merge", json_merge),
}


class TestRunner:
    def run_tests_for_app(self, app_name: str, module_name: str) -> Tuple[bool, str]:
        """Run tests for specific app"""
        app_path = Path(f"apps/{module_name}").absolute()
        app_test_path = app_path / "tests"

        if not app_test_path.exists():
            return True, "No tests directory found"

        try:
            test_files = list(app_test_path.glob("test_*.py"))
            test_files.extend(app_test_path.glob("**/test_*.py"))

            if not test_files:
                return True, f"No test files found in {app_test_path}"

            test_files_str = " ".join(str(f) for f in test_files)
            env = os.environ.copy()

            project_root = Path(__file__).parent.absolute()
            python_path = [
                str(project_root),
                str(app_path),
                str(app_path.parent)
            ]

            if 'PYTHONPATH' in env:
                python_path.append(env['PYTHONPATH'])

            env['PYTHONPATH'] = os.pathsep.join(python_path)

            # Run pytest with additional options for capturing output
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    *test_files_str.split(),
                    "-v",
                    "--import-mode=importlib",
                    "--capture=tee-sys",  # Capture both stdout and stderr while showing them
                    "-s",  # Don't capture stdout (allows print statements to show)
                    "--log-cli-level=DEBUG",  # Show debug logs
                    "--log-format=%(levelname)s: %(message)s",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(project_root)
            )

            stdout, stderr = process.communicate()
            output = stdout + stderr

            # Format the output for better readability
            formatted_output = self.format_test_output(output)

            debug_info = f"""
Test Execution Details:
----------------------
App: {app_name}
Module: {module_name}
Test Path: {app_test_path}
Found Test Files:
{chr(10).join(f"- {f}" for f in test_files)}
Python Path: {os.pathsep.join(python_path)}
Working Dir: {project_root}

Test Output:
-----------
{formatted_output}
"""
            return process.returncode == 0, debug_info

        except Exception as e:
            return False, f"Error: {str(e)}\nTest path: {app_test_path}"

    @staticmethod
    def format_test_output(output: str) -> str:
        """Format the test output for better readability"""
        lines = output.split('\n')
        formatted_lines = []

        for line in lines:
            # Highlight debug messages
            if 'DEBUG:' in line:
                line = f"? {line}"
            # Highlight print statements
            elif line.strip() and not line.startswith(('===', '___', 'collecting', 'Test')):
                line = f"? {line}"
            # Highlight test results
            elif 'PASSED' in line:
                line = f"? {line}"
            elif 'FAILED' in line:
                line = f"? {line}"
            elif 'SKIPPED' in line:
                line = f"?? {line}"

            formatted_lines.append(line)

        return '\n'.join(formatted_lines)




def run_app_tests(app_name: str, module_name: str) -> None:
    """Run tests for selected app and display results"""
    # Create container for test results
    test_container = st.container()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Test Results for {app_name}")
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🔄 Re-run Tests", key=f"rerun_{app_name}"):
            # Clear previous results
            st.session_state.pop(f'test_result_{app_name}', None)
            st.session_state.pop(f'test_output_{app_name}', None)
            st.rerun()  # Rerun the app

    # Check if we have cached results
    result_key = f'test_result_{app_name}'
    output_key = f'test_output_{app_name}'

    with test_container:
        if result_key not in st.session_state or output_key not in st.session_state:
            with st.spinner("Running tests..."):
                runner = TestRunner()
                passed, output = runner.run_tests_for_app(app_name, module_name)
                st.session_state[result_key] = passed
                st.session_state[output_key] = output

        # Display results
        if st.session_state[result_key]:
            st.success("✅ All tests passed!")
        else:
            st.error("❌ Some tests failed!")

        # Show test output in expandable section
        with st.expander("Test Details", expanded=not st.session_state[result_key]):
            st.code(st.session_state[output_key], language='bash')

def main():
    st.set_page_config(
        page_title="Multi-App Dashboard",
        page_icon="🧪",
        layout="wide"
    )

    # Initialize session state for selected app
    if 'selected_app' not in st.session_state:
        st.session_state.selected_app = list(PAGES.keys())[0]

    st.sidebar.title("Navigation")

    # When selection changes, clear test results for new app
    new_selection = st.sidebar.radio("Go to", list(PAGES.keys()), key='app_selection')
    if new_selection != st.session_state.selected_app:
        result_key = f'test_result_{new_selection}'
        output_key = f'test_output_{new_selection}'
        st.session_state.pop(result_key, None)
        st.session_state.pop(output_key, None)
        st.session_state.selected_app = new_selection
        st.rerun()

    # Get the selected page and module name
    module_name, page = PAGES[st.session_state.selected_app]

    # Run tests for selected app
    run_app_tests(st.session_state.selected_app, module_name)

    # Only load page if its tests passed
    result_key = f'test_result_{st.session_state.selected_app}'
    if st.session_state.get(result_key, True):
        with st.spinner(f"Loading {st.session_state.selected_app} ..."):
            page.main()
    else:
        st.error(f"Cannot load {st.session_state.selected_app} due to failed tests.")
        st.warning("Please fix the failing tests before using this app.")

if __name__ == "__main__":
    main()

