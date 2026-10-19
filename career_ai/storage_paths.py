"""Resolve mutable application data paths, including persistent deployment volumes."""
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.abspath(
    os.environ.get("CAREER_AI_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
)


def data_file(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)
