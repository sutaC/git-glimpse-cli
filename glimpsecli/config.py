from typing import TypedDict
from pathlib import Path
import json

CLI_CONFIG_DIR = Path.home() / ".config" / "glimpsecli"
CLI_CONFIG_FILE = CLI_CONFIG_DIR / "config.json"
CONFIG_FILENAME = ".shared-repo.json"

# --- repository config
class RepoConfig(TypedDict):
    repo_id: str

def repoconf_save(repo_id: str, path: Path = Path(".")) -> None:
    """Saves repository config to file.
    
    Args:
        repo_id: Repository GitGlimpse id.
        path: Path to directory holding config file.    
    """
    config_path = path / CONFIG_FILENAME
    data = {"repo_id": repo_id}
    with open(config_path, "w") as f:
        json.dump(data, f)

def repoconf_load(path: Path = Path(".")) -> RepoConfig | None:
    """Loads repository config from file.
    
    Args:
        path: Path to directory holding config file.    

    Returns:
        RepoConfig if avaliable, else None.
    """
    config_path = path / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def repoconf_remove(path: Path = Path(".")) -> None:
    """Removes repository config file if exists.
    
    Args:
        path: Path to directory holding config file.
    """
    config_path = path / CONFIG_FILENAME
    config_path.unlink(missing_ok=True)        

# --- cli config
class CliConfig(TypedDict):
    token: str

def cliconf_save(token: str) -> None:
    """Cli config to file.
    
    Args:
        token: GitGlimpse api token.
    """
    CLI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLI_CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f)

def cliconf_load() -> CliConfig | None:
    """Loads cli configfrom  file.
    
    Returns:
        CliConfig if avaliable, else None.
    """
    if not CLI_CONFIG_FILE.exists():
        return None
    try: 
        with open(CLI_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def cliconf_remove() -> None:
    """Removes cli config file."""
    CLI_CONFIG_FILE.unlink(missing_ok=True)