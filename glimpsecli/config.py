from functools import partial
from typing import TypedDict
from pathlib import Path
import json

CLI_CONFIG_DIR = Path.home() / ".config" / "glimpsecli"
CLI_CONFIG_FILE = CLI_CONFIG_DIR / "config.json"
CONFIG_FILENAME = ".shared-repo.json"
DEFAULT_API_URL = "https://gitglimpse.sutac.pl"

class CliConfig(TypedDict, total=False):
    token: str
    api_url: str
    debug: bool

class RepoConfig(CliConfig, total=False):
    repo_id: str

# --- repository config
def _repoconf_load() -> RepoConfig | None:
    """Loads repository config from file.
    
    Args:
        path: Path to directory holding config file.    

    Returns:
        RepoConfig if avaliable, else None.
    """
    config_path = Path(".") / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def repoconf_remove() -> None:
    """Removes repository config file if exists.
    
    Args:
        path: Path to directory holding config file.
    """
    config_path = Path(".") / CONFIG_FILENAME
    config_path.unlink(missing_ok=True)        


# --- cli config
def _cliconf_load() -> CliConfig | None:
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

# --- conf update
def conf_save(
        new_conf: CliConfig | RepoConfig | dict, 
        local = False
    ) -> None:
    """Save configuration in ethier local or global context.
    
    Args:
        local: If True saves config to local context, else saves in global context.
    """
    if local:
        conf = _repoconf_load() or {}
        conf_file = Path(".") / CONFIG_FILENAME
    else:
        CLI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        conf = _cliconf_load() or {}
        conf_file = CLI_CONFIG_FILE
    for key, val in new_conf.items():
        if val is not None:
            conf[key] = val
        elif key in conf:
            conf.pop(key)
    with open(conf_file, "w") as f:
        json.dump(conf, f, indent=2)

# --- config getters
def get_api_url() -> str:
    """Returns active api url."""
    if conf := _repoconf_load():
        if user_url := conf.get("api_url"):
            return user_url.rstrip("/")
    if conf := _cliconf_load():
        if user_url := conf.get("api_url"):
            return user_url.rstrip("/")
    return DEFAULT_API_URL

def get_debug_mode() -> bool:
    """Returns True if debug is enabled in user config, else False."""
    if conf := _repoconf_load():
        if debug := conf.get("debug") is not None:
            return debug 
    if conf := _cliconf_load():
        return conf.get("debug", False)
    return False

def get_repo_id() -> str | None:
    """Returns current repo_id."""
    if conf := _repoconf_load():
        return conf.get("repo_id")
    return None

def get_token() -> str | None:
    """Returns current user cli token."""
    if conf := _repoconf_load():
        if token := conf.get("token"):
            return token
    if conf := _cliconf_load():
        if token := conf.get("token"):
            return token
    return None
