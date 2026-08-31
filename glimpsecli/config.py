from typing import TypedDict
from pathlib import Path
import json
import os

CLI_CONFIG_DIR = Path.home() / ".config" / "glimpsecli"
CLI_CONFIG_FILE = CLI_CONFIG_DIR / "config.json"
CONFIG_FILENAME = ".shared-repo.json"
DEFAULT_API_URL = "https://gitglimpse.sutac.pl"

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
    conf: RepoConfig = {"repo_id": repo_id}
    with open(config_path, "w") as f:
        json.dump(conf, f, indent=2)

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
class CliConfig(TypedDict, total=False):
    token: str
    api_url: str

def cliconf_save(
        token: str | None = None, 
        api_url: str | None = None
    ) -> None:
    """Saves or updates cli config safely.
    
    Args:
        token: GitGlimpse api token.
    """
    CLI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conf = cliconf_load() or {}
    if token is not None:
        if token: conf["token"] = token
        else: conf.pop("token")
    if api_url is not None:
        if api_url: conf["api_url"] = api_url.rstrip("/")
        else: conf.pop("api_url")
    with open(CLI_CONFIG_FILE, "w") as f:
        json.dump(conf, f, indent=2)

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

def get_api_url() -> str:
    """Resolves active api url using hierarchy: Env Var > User Config > Default.
    
    Returns:
        Active api url.
    """
    if env_url := os.getenv("GITGLIMPSE_API_URL"):
        return env_url.rstrip("/")
    if conf := cliconf_load():
        if user_url := conf.get("api_url"):
            return user_url.rstrip("/")
    return DEFAULT_API_URL