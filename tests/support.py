from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_initialization_script():
    schema = (PROJECT_ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8")
    test_data = (PROJECT_ROOT / "sql" / "02_test_data.sql").read_text(encoding="utf-8")
    return f"{schema}\n{test_data}"
