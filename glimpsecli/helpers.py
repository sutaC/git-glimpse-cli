from glimpsecli import utils, config, api
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
from rich import print
import typer
import time

def get_or_prompt_url(url: str | None = None, detect: bool = True) -> str:
    """Helper to get GitHub repository url.
    
    Args:
        url: GitHub repository url.
        detect: Flag for automatic detection.

    Returns:
        GitHub repository url.
    """
    if detect and not url:
        if not Path(".git").exists():
            print("[red]Error: Current directory is not a Git repository.[/red]")
            raise typer.Exit(1)
        url = utils.get_git_remote_url()
        if not url:
            print("[dim]Could not detect GitHub url.[/dim]")
    if not url:
        while True:
            url = typer.prompt("Enter GitHub repository URL (e.g., https://github.com/user/repo.git)")
            if url: url = url.strip()
            if url and utils.is_valid_repo_url(url): break
            print("[bold red]Invalid url, try again...[/bold red]")
    return url

def finalize_init(repo_id: str) -> None:
    """Helper to save config and update gitignore.
    
    Args:
        repo_id: Repository GitGlimpse id.
    """
    # Add repo id to local file
    config.conf_save({"repo_id": repo_id}, local=True)
    print("[dim]Created local .shared-repo.json configuration file for this repository.[/dim]")
    # Auto-add to .gitignore
    gitignore = Path(".gitignore")
    ignore_entry = "\n.shared-repo.json\n"
    if gitignore.exists():
        if ".shared-repo.json" not in gitignore.read_text():
            with open(gitignore, "a") as f:
                f.write(ignore_entry)
            print("[dim]Added .shared-repo.json to .gitignore[/dim]")
    else:
        gitignore.write_text(ignore_entry)
        print("[dim]Created .gitignore and added .shared-repo.json[/dim]")

def poll_build_status(token: str, repo_id: str) -> None:
    """Helper to poll build status from server.
    
    Args:
        token: GitGlimpse api token.
        repo_id: Repository GitGlimpse id.
    """
    print(f"[dim]Repository build was queued.[/dim]")
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            task_id = progress.add_task(description="Connecting to server...", total=None)
            last_status = None
            while True:
                poll_response = api.request_api(f"/cli/repos/build/{repo_id}/status", token=token, quiet=True) 
                status = poll_response.json().get("status")
                if status != last_status:
                    progress.update(task_id, description=f"Build status: {utils.enrich_status(status)}")
                    last_status = status
                    if status in ["success", "failed", "violation"]: break
                time.sleep(2)
    except KeyboardInterrupt:
        print("\n[yellow]Polling interrupted. The build is still running on the server.[/yellow]")
        print(f"Check status later at: {config.get_api_url()}/repos/details/{repo_id}")
        raise typer.Exit(0)
    print(f"Build has finished with status: {utils.enrich_status(status)}")
    print(f"View details at: {config.get_api_url()}/repos/details/{repo_id}")

def fget_repo_id() -> str:
    """Helper for getting repository config."""
    repo_id = config.get_repo_id()
    if not repo_id:
        print("[yellow]Not initialised. Run 'glimpse init' first.[/yellow]")
        raise typer.Exit(1)
    return repo_id

def fget_token() -> str:
    """Helper for getting api token."""
    token = config.get_token()
    if not token:
        print("[yellow]Not logged in. Run 'glimpse login' first.[/yellow]")
        raise typer.Exit(code=1)
    return token