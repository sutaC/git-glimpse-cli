from pathlib import Path
import json

CONFIG_DIR = Path.home() / ".config" / "gitgl-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

def save_token(token: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f)

def load_token() -> str | None:
    if not CONFIG_FILE.exists():
        return None
    try: 
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("token")
    except Exception:
        return None

def remove_token() -> None:
    CONFIG_FILE.unlink(missing_ok=True)