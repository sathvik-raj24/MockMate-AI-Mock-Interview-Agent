
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_protects_secrets_and_personal_data():
    gitignore_path = PROJECT_ROOT / ".gitignore"
    env_example_path = PROJECT_ROOT / ".env.example"

    assert gitignore_path.exists()
    assert env_example_path.exists()

    text = gitignore_path.read_text(encoding="utf-8")

    required_patterns = (
        ".env",
        ".env.*",
        "!.env.example",
        "workspace/sessions/*",
        "workspace/weak-topics.md",
        "*.sqlite",
        "*.sqlite3",
        "*.db",
    )

    for pattern in required_patterns:
        assert pattern in text
