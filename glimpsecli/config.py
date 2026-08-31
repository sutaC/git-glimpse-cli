from typing import TypedDict
from pathlib import Path
from rich import print
import typer
import json

CONFIG_FILENAME = ".shared-repo.json"

class Config(TypedDict):
    repo_id: str

def save_repo_config(repo_id: str, path: Path = Path(".")) -> None:
    config_path = path / CONFIG_FILENAME
    data = {"repo_id": repo_id}
    with open(config_path, "w") as f:
        json.dump(data, f)

def load_repo_config(path: Path = Path(".")) -> Config | None:
    config_path = path / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def remove_repo_config(path: Path = Path(".")) -> None:
    config_path = path / CONFIG_FILENAME
    config_path.unlink(missing_ok=True)        

def get_repo_config() -> Config:
    conf = load_repo_config()
    if not conf:
        print("[yellow]Not initialised. Run 'glimpse init' first.[/yellow]")
        raise typer.Exit(code=1)
    return conf