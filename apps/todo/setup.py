from setuptools import setup, find_packages

setup(
    name="todo",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dateutil",
        "todoist-api-python",
        "google-api-python-client",
    ],
    python_requires=">=3.9",
)