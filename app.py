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

PAGES = {
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
        # Get absolute paths
        app_path = Path(f"apps/{module_name}").absolute()
        app_test_path = app_path / "tests"

        if not app_test_path.exists():
            return True, "No tests directory found"

        try:
            # Find all test files
            test_files = list(app_test_path.glob("test_*.py"))
            test_files.extend(app_test_path.glob("**/test_*.py"))  # Include subdirectories

            if not test_files:
                return True, f"No test files found in {app_test_path}"

            # Convert test files to strings
            test_files_str = " ".join(str(f) for f in test_files)

            # Prepare environment with correct PYTHONPATH
            env = os.environ.copy()

            # Add project root and app directory to PYTHONPATH
            project_root = Path(__file__).parent.absolute()
            python_path = [
                str(project_root),  # Project root
                str(app_path),      # App directory
                str(app_path.parent)  # apps directory
            ]

            # Append to existing PYTHONPATH if it exists
            if 'PYTHONPATH' in env:
                python_path.append(env['PYTHONPATH'])

            env['PYTHONPATH'] = os.pathsep.join(python_path)

            # Run pytest with explicit test files
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    *test_files_str.split(),  # Pass test files explicitly
                    "-v",
                    "--import-mode=importlib",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(project_root)
            )

            stdout, stderr = process.communicate()
            output = stdout + stderr

            # Debug information
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
{output}
"""
            return process.returncode == 0, debug_info

        except Exception as e:
            return False, f"Error: {str(e)}\nTest path: {app_test_path}"


def run_app_tests(app_name: str, module_name: str) -> None:
    """Run tests for selected app and display results"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Test Results for {app_name}")
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("? Re-run Tests"):
            st.session_state.pop(f'test_result_{app_name}', None)
            st.session_state.pop(f'test_output_{app_name}', None)

    # Check if we have cached results
    result_key = f'test_result_{app_name}'
    output_key = f'test_output_{app_name}'

    if result_key not in st.session_state or output_key not in st.session_state:
        with st.spinner("Running tests..."):
            runner = TestRunner()
            passed, output = runner.run_tests_for_app(app_name, module_name)
            st.session_state[result_key] = passed
            st.session_state[output_key] = output

    # Display results
    if st.session_state[result_key]:
        st.success("? All tests passed!")
    else:
        st.error("? Some tests failed!")

    # Show test output in expandable section
    with st.expander("Test Details", expanded=not st.session_state[result_key]):
        st.code(st.session_state[output_key], language='bash')

    # Add separator
    st.markdown("---")


def main():
    st.set_page_config(
        page_title="Multi-App Dashboard",
        page_icon="?",
        layout="wide"
    )

    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))

    # Get the selected page and module name
    module_name, page = PAGES[selection]

    # Run tests for selected app
    run_app_tests(selection, module_name)

    # Only load page if its tests passed
    result_key = f'test_result_{selection}'
    if st.session_state.get(result_key, True):
        with st.spinner(f"Loading {selection} ..."):
            page.main()
    else:
        st.error(f"Cannot load {selection} due to failed tests.")
        st.warning("Please fix the failing tests before using this app.")

if __name__ == "__main__":
    main()

