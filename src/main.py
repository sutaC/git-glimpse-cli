from json import JSONDecodeError

from rich.panel import Panel
from pathlib import Path
from rich import print
from enum import Enum
import config
import typer
import utils
import auth
import api

class InitType(str, Enum):
    new = "new"
    link = "link"

app = typer.Typer(help="CLI tool to manage and update shared GitHub repos with GitGlimpse.", no_args_is_help=True)

@app.command()
def login(
    token: str = typer.Option(
        ..., 
        prompt="Enter your CLI token", 
        hide_input=True, 
        help="Your personal access cli token from dashboard."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing session without prompting.")
    ):
    """Authenticate CLI with server."""
    existing_token = auth.load_token()
    if existing_token and not force:
        print("[yellow]You are already logged in.[/yellow]")
        if not typer.confirm("Do you want to overwrite your existing session?"):
            print("[dim]Login cancelled.[/dim]")
            raise typer.Exit(0)
    response = api.request_api("/user", token=token)
    auth.save_token(token)
    username =  response.json().get("username")
    print(f"[bold green]Success![/bold green] Authenticated as [cyan]{username}[/cyan].")

@app.command()
def whoami():
    """Check the currently logged-in user."""
    response = api.request_api("/user")
    username =  response.json().get("username")
    print(f"Authenticated as [cyan]{username}[/cyan].")

@app.command()
def logout():
    """Clear stored local credentials."""
    if not auth.load_token():
        print("[yellow]You are not currently logged in.[/yellow]")
        raise typer.Exit(0)
    auth.remove_token()
    print("[bold green]Logged out successfully. Stored credentials removed.[/bold green]")

@app.command()
def init(
    url: str | None = typer.Option(None, help="GitHub repository URL."),
    type: InitType | None = typer.Option(None, help="Initialise new repository or link to existing one."),
    is_private: bool | None = typer.Option(None, "--private/--public", help="Is repository public or private? (only with '--type new')"),
    detect: bool = typer.Option(True, help="Do you want to detect repository url automatically.")
    ):
    """Link or upload the current Git repository to GitGlimpse server."""
    token = api.get_token()
    if config.load_repo_config():
        print("Shared repository already initialised.")
        raise typer.Exit(0)
    if detect and not url:
        if not Path(".git").exists():
            print("[red]Error: Current directory is not a Git repository.[/red]")
            raise typer.Exit(code=1)
        url = utils.get_git_remote_url()
        if not url:
            print("[dim]Could not detect GitHub url.[/dim]")
    if not url:
        while True:
            url = typer.prompt("Enter GitHub repository URL (e.g., https://github.com/user/repo.git)")
            if url and utils.is_valid_repo_url(url): break
            print("[bold red]Invalid url, try again...[/bold red]")
    if not type:
        type = typer.prompt(
            "Do you want to upload new repository to GitGlimpse or link to repository on the server? [new/link]",
            type=InitType
        )
    if type == InitType.link:
        print("[dim]Linking to existing GitGlimpse repository.[/dim]")
        if is_private is not None:
            print("[dim]Used --private/--public option is beeing omited.[/dim]")
        response = api.request_api("/repos/fetch", method="POST", payload={"url": url}, token=token, handle_codes=[200, 404])
        if response.status_code == 200: # Server already has this repo
            repo_id = response.json().get("repo_id")
            if not repo_id:
                print("[bold red]Did not recieve valid repository id from server.[/bold red]")
                raise typer.Exit(1)
            print("[green]Repo was found on GitGlimpse server.[/green]")
        elif response.status_code == 404: # Server does not have this repo
            print(f"[bold red]Could not find this repository ([cyan]'{url}'[/cyan]) on GitGlimpse server, provide a valid url.[/bold red]")
            raise typer.Exit(1)
        else:
            print(f"[bold red]Unexpected server response code {response.status_code}.[/bold red]")
            raise typer.Exit(1)
    elif type == InitType.new:
        print("[dim]Adding repository to GitGlimpse.[/dim]")
        print("[bold]This repository [orange]have to be uploaded to GitHub[/orange] under given url first.[/bold]")
        # Private/Public
        if is_private is None:
            is_private = typer.confirm("Are you uploading a private repository? (This will require SSH key generation)")
        if is_private: # Private
            print("[dim]Generating local SSH keys at '.git/shared_repo_keys/'.[/dim]")
            try:
                private_key, public_key = utils.generate_local_ssh_key()
            except Exception as e:
                print(f"[red]Failed to generate local SSH key: {e}[/red]")
                raise typer.Exit(code=1)
            print("\n[bold yellow]Action Required:[/bold yellow] Add this deploy key to your GitHub repository settings ([dim]Settings > Deploy keys > Add deploy key[/dim]):")
            print(Panel(public_key, title="Public Deploy Key", border_style="yellow"))
            typer.confirm("Continue?", abort=True)
            if url.startswith("https://"):
                url = utils.create_alt_repo_url(url)
        else: # Public
            if not url.startswith("https://"):
                url = utils.create_alt_repo_url(url)
            private_key = None
        # Upload
        response = api.request_api(
            "/repos/add", 
            method="POST", 
            payload={"url": url, "ssh_key": private_key}, 
            token=token, 
            handle_codes=[202, 409, 420]
        )
        if response.status_code == 202:
            data = response.json()
            repo_id = data.get("repo_id")
            print(f"[bold green]Success![/bold green] Repository was linked, view details at: [cyan]{api.API_BASE}/repos/details/{repo_id}[/cyan]")
        elif response.status_code == 409:
            print(f"[yellow]This repository is already registered on the server.[/yellow]")
            raise typer.Exit(1)
        elif response.status_code == 420:
            print(f"[yellow]You have reached your usage limits.[/yellow]")
            try:
                error = response.json().get("error")
                if error: print(f"[dim]Error reason: {error}[/dim]")
            except JSONDecodeError: pass
            raise typer.Exit(1)
        else:
            print(f"[bold red]Unexpected server response code {response.status_code}.[/bold red]")
            raise typer.Exit(1)
    else:
        print("[red]Unexpected init option.[/red]")
        raise typer.Exit(1)
    # Add repo id to local file
    config.save_repo_config(repo_id)
    print("[dim]Created local .shared-repo.json configuration file for this repository.[/dim]")

@app.command()
def limits():
    """Display user build and repository limits."""
    response = api.request_api("/user/limits")
    data = response.json()
    repo_limit = data.get("repo_limit")
    repo_count = data.get("repo_count")
    build_limit = data.get("build_limit")
    build_count = data.get("build_count")
    print("User limits:")
    print(f"Repositories: {f"[red]{repo_count}[/red]/[red]{repo_limit}[/red]" if repo_count == repo_limit else f"{repo_count}/{repo_limit}"}")
    print(f"Builds: {f"[red]{build_count}[/red]/[red]{build_limit}[/red]" if build_count == build_limit else f"{build_count}/{build_limit}"}")

@app.command()
def status():
    """Display status info of current repository."""
    conf = config.get_repo_config()
    print(f"Repository GitGlimpse id: [dark_cyan]{conf["repo_id"]}[/dark_cyan]")
    print(f"Link to repository details: {api.API_BASE}/repos/details/{conf["repo_id"]}")

@app.command()
def remove(
        force: bool = typer.Option(False, "--force", "-f", help="Remove without prompting.")
    ):
    """Remove current repository from GitGlimpse."""
    token = api.get_token()
    conf = config.get_repo_config()
    print(f"[dim]Current repository id: '{conf['repo_id']}'[/dim]")
    if not force: typer.confirm(f"Are you sure, you want to remove this repository from GitGlimpse?", abort=True)
    api.request_api(f"/repos/remove/{conf['repo_id']}", method="POST", token=token, handle_codes=[204])
    config.remove_repo_config()
    print("Removed repository from GitGlimpse.")

@app.command()
def build(
        force: bool = typer.Option(False, "--force", "-f", help="Schedule without prompting.")
    ):
    """Schedule a build for current repository."""
    token = api.get_token()
    conf = config.get_repo_config()
    if not force:
        print("Ensure that you pushed recent changes to GitHub.")
        typer.confirm("Continue?", abort=True)
    print(f"[dim]Scheduling a build for current repository (id: '{conf['repo_id']}')[/dim]")
    response = api.request_api(f"/repos/build/{conf['repo_id']}", method="POST", token=token, handle_codes=[202, 420, 425])
    if response.status_code == 202:
        print(f"[bold green]Success![/bold green] Repository build was scheduled, view details at: [cyan]{api.API_BASE}/repos/details/{conf['repo_id']}[/cyan]")
    elif response.status_code == 420:
        print(f"[yellow]You have reached your usage limits.[/yellow]")
        try:
            error = response.json().get("error")
            if error: print(f"[dim]Error reason: {error}[/dim]")
        except JSONDecodeError: pass
        raise typer.Exit(1)
    elif response.status_code == 425:
        print(f"[yellow]This repository already has a pending build.[/yellow]")
        raise typer.Exit(1)
    else:
        print(f"[bold red]Unexpected server response code {response.status_code}.[/bold red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
