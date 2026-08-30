from pathlib import Path
import json

CONFIG_FILENAME = ".shared-repo.json"

def save_project_config(repo_id: str, github_url: str, path: Path = Path(".")):
    config_path = path / CONFIG_FILENAME
    data = {"repo_id": repo_id}
    with open(config_path, "w") as f:
        json.dump(data, f)

def load_project_config(path: Path = Path(".")) -> dict | None:
    config_path = path / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return None