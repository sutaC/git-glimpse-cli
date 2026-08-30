from rich.panel import Panel
from pathlib import Path
from rich import print
from enum import Enum
import config
import typer
import utils
import auth
import api

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
    github_url: str | None = typer.Option(
        None, help="GitHub repository URL."
    )):
    """Link the current Git repository to GitGlimpse server id."""
    token = api.get_token()
    if config.load_project_config():
        print("Shared repository already initialised.")
        raise typer.Exit(0)
    if not Path(".git").exists():
        print("[red]Error: Current directory is not a Git repository.[/red]")
        raise typer.Exit(code=1)
    if not github_url:
        github_url = utils.get_git_remote_url()
    if not github_url:
        print("[dim]Could not detect GitHub url.[/dim]")
        while True:
            github_url = typer.prompt("Enter GitHub repository URL (e.g., https://github.com/user/repo.git)")
            if github_url and utils.is_valid_repo_url(github_url): break
            print("[bold red]Invalid url, try again...[/bold red]")
    class InitOption(str, Enum):
        new = "new"
        link = "link"
    selected: str = typer.prompt("Do you want to upload new repository to GitGlimpse or link to repository on the server? [new/link]", type=InitOption)
    repo_id = ""
    if selected in [InitOption.link, InitOption.link[0]]:
        print("[dim]Linking to existing GitGlimpse repository.[/dim]")
        pass
        response = api.request_api("/repos/fetch", method="POST", payload={"url": github_url}, token=token, handle_codes=[200, 404])
        if response.status_code == 200: # Server already has this repo
            repo_id = response.json().get("repo_id")
            if not repo_id:
                print("[bold red]Did not recieve valid repository id from server.[/bold red]")
                raise typer.Exit(1)
            print("[green]Repo was found on GitGlimpse server.[/green]")
        elif response.status_code == 404: # Server does not have this repo
            print(f"[bold red]Could not find this repository ([cyan]'{github_url}'[/cyan]) on GitGlimpse server, provide a valid url.[/bold red]")
            raise typer.Exit(1)
        else:
            print("[bold red]Unexpected server response code.[/bold red]")
            raise typer.Exit(1)
    elif selected in [InitOption.new, InitOption.new[0]]:
        print("[dim]Adding repository to GitGlimpse.[/dim]")
        print("[bold]This repository [orange]have to be uploaded to GitHub[/orange] under given url first.[/bold]")
        # Private/Public
        if typer.confirm("Are you uploading a private repository? (This will require SSH key generation)"): # Private
            print("[dim]Generating local SSH keys at '.git/shared_repo_keys/'.[/dim]")
            try:
                private_key, public_key = utils.generate_local_ssh_key()
            except Exception as e:
                print(f"[red]Failed to generate local SSH key: {e}[/red]")
                raise typer.Exit(code=1)
            print("\n[bold yellow]Action Required:[/bold yellow] Add this deploy key to your GitHub repository settings ([dim]Settings > Deploy keys > Add deploy key[/dim]):")
            print(Panel(public_key, title="Public Deploy Key", border_style="yellow"))
            typer.confirm("Continue?", abort=True)
            if github_url.startswith("https://"):
                github_url = utils.create_alt_repo_url(github_url)
        else: # Public
            if not github_url.startswith("https://"):
                github_url = utils.create_alt_repo_url(github_url)
            private_key = None
        # Upload
        response = api.request_api("/repos/add", method="POST", payload={"url": github_url, "ssh_key": private_key}, token=token, handle_codes=[202, 409])
        if response.status_code == 202:
            data = response.json()
            repo_id = data.get("repo_id")
            print(f"[bold green]Success![/bold green] Repository was linked, view details at: [cyan]{api.API_BASE}/repos/details/{repo_id}[/cyan]")
        elif response.status_code == 409:
            print(f"[yellow]This repository is already registered on the server.[/yellow]")
            raise typer.Exit(1)
        else:
            print("[bold red]Unexpected server response code.[/bold red]")
            raise typer.Exit(1)
    # Add repo id to local file
    config.save_project_config(repo_id, github_url)
    print("[dim]Created local .shared-repo.json configuration file for this repository.[/dim]")
    # gitignore
    gitignore_path = Path(".gitignore")
    if typer.confirm("Do you want to add '.shared-repo.yml' to .gitignore?", default=False):
        ignore_entry = "\n.shared-repo.yml\n"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if ".shared-repo.yml" not in content:
                with open(gitignore_path, "a") as f:
                    f.write(ignore_entry)
        else:
            gitignore_path.write_text(ignore_entry)
        print("[dim]Added .shared-repo.yml to .gitignore[/dim]")

if __name__ == "__main__":
    app()

# Test data
# c567dde96a2cb35304af1c3816c21143a5028e7a6f9d9b4be369c516fa2819fe
# https://github.com/sutaC/git-glimpse.git