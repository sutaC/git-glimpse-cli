from pathlib import Path
import subprocess
import re

_GITHUB_URL_REGEX = re.compile(r'^(?:https:\/\/github\.com\/|git@github\.com:)[\w\-]+\/[\w\-]+(?:\.git)?$')
_GITHUB_URL_OWNER_REPO = r"(?:https?://github\.com/|git@github\.com:)([\w-]+)/([\w-]+?)(?:\.git)?$"

def get_git_remote_url() -> str | None:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def is_valid_repo_url(url: str) -> bool:
    """Validate repository URL.
    
    Valid URL will follow this pattern: 
    - `https://github.com/user/repo.git`
    - `git@github.com:user/repo.git`.

    Args:
        url: URL to validate.
    
    Returns:
        True if URL is valid.

    Notes:
        This function checks only format. It does not verify
        URL resource existence. 
    """
    return bool(_GITHUB_URL_REGEX.match(url))

def _parse_github_owner_repo(url: str) -> tuple[str, str]:
    match = re.match(_GITHUB_URL_OWNER_REPO, url.strip())
    assert match
    owner, repo = match.groups()
    return owner, repo

def create_alt_repo_url(url: str):
    assert is_valid_repo_url(url)
    owner, repo = _parse_github_owner_repo(url)
    if url.startswith("https://"):
        return f"git@github.com:{owner}/{repo}.git"
    else:
        return f"https://github.com/{owner}/{repo}.git"

def generate_local_ssh_key() -> tuple[str, str]:
  """Generates a temporary project-specific SSH key pair locally if it doesn't exist."""
  key_dir = Path(".git") / "shared_repo_keys"
  key_dir.mkdir(parents=True, exist_ok=True)
  private_key_path = key_dir / "id_rsa"
  public_key_path = key_dir / "id_rsa.pub"

  if not private_key_path.exists():
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "rsa",
            "-N",
            "",
            "-f",
            str(private_key_path),
            "-C",
            "shared-repo-cli",
        ],
        check=True,
        capture_output=True,
    )

  private_key = private_key_path.read_text()
  public_key = public_key_path.read_text().strip()
  return private_key, public_key
