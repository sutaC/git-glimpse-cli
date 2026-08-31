from glimpsecli import config, utils, api, helpers
from json import JSONDecodeError
from rich.panel import Panel
from rich import print
import typer

app = typer.Typer(help="CLI tool to manage and update shared GitHub repos with GitGlimpse.", no_args_is_help=True)

# --- login
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
    conf = config.cliconf_load()
    if not force and conf and "token" in conf:
        print("[yellow]You are already logged in.[/yellow]")
        if not typer.confirm("Do you want to overwrite your existing session?"):
            print("[dim]Login cancelled.[/dim]")
            raise typer.Exit(0)
    response = api.request_api("/user", token=token)
    config.cliconf_save(token)
    username =  response.json().get("username")
    print(f"[bold green]Success![/bold green] Authenticated as [cyan]{username}[/cyan].")

# --- whoami
@app.command()
def whoami():
    """Check the currently logged-in user."""
    response = api.request_api("/user")
    username =  response.json().get("username")
    print(f"Authenticated as [cyan]{username}[/cyan].")

# --- logout
@app.command()
def logout():
    """Clear stored local credentials."""
    conf = config.cliconf_load()
    if not conf or not "token" in conf:
        print("[yellow]You are not currently logged in.[/yellow]")
        raise typer.Exit(0)
    config.cliconf_remove()
    print("[bold green]Logged out successfully. Stored credentials removed.[/bold green]")

# --- init
init_app = typer.Typer(help="Link or upload the current Git repository to GitGlimpse server.", no_args_is_help=True)
app.add_typer(init_app, name="init")

@init_app.command("link")
def init_link(
        url: str | None = typer.Option(None, help="GitHub repository URL."),
        detect: bool = typer.Option(True, help="Do you want to detect repository url automatically.")
    ):
    """Link current Git repository to existing one on GitGlimpse."""
    token = helpers.get_token()
    if config.repoconf_load():
        print("Shared repository already initialised.")
        raise typer.Exit(0)
    url = helpers.get_or_prompt_url(url, detect)
    print("[dim]Linking to existing GitGlimpse repository.[/dim]")
    response = api.request_api("/repos/fetch", method="POST", payload={"url": url}, token=token, handle_codes=[200, 404])
    if response.status_code == 404:
        print(f"[bold red]Could not find this repository ([cyan]'{url}'[/cyan]) on GitGlimpse server, provide a valid url.[/bold red]")
        raise typer.Exit(1)
    # response.status_code == 200
    repo_id = response.json().get('repo_id')
    print("[green]Repo was found on GitGlimpse server.[/green]")
    helpers.finalize_init(repo_id)
    print(f"Repository details: {api.API_BASE}/repos/details/{repo_id}")

@init_app.command("new")
def init_new(
    url: str | None = typer.Option(None, help="GitHub repository URL."),
    is_private: bool | None = typer.Option(None, "--private/--public", help="Is repository public or private?"),
    force: bool = typer.Option(False, "--force", "-f", help="Upload without prompting about GitHub publish."),
    detect: bool = typer.Option(True, help="Do you want to detect repository url automatically.")
    ):
    """Upload and register current Git repository to GitGlimpse."""
    token = helpers.get_token()
    if config.repoconf_load():
        print("Shared repository already initialised.")
        raise typer.Exit(0)
    url = helpers.get_or_prompt_url(url, detect)
    print("[dim]Adding repository to GitGlimpse.[/dim]")
    if not force:
        print("[bold]This repository have to be uploaded to GitHub under given url first.[/bold]")
        typer.confirm("Continue?", abort=True)
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
    if response.status_code == 409:
        print(f"[yellow]This repository is already registered on the server.[/yellow]")
        raise typer.Exit(1)
    elif response.status_code == 420:
        print(f"[yellow]You have reached your usage limits.[/yellow]")
        try:
            error = response.json().get("error")
            if error: print(f"[dim]Error reason: {error}[/dim]")
        except JSONDecodeError: pass
        raise typer.Exit(1)
    # response.status_code == 202
    data = response.json()
    repo_id = data.get('repo_id')
    helpers.finalize_init(repo_id)
    helpers.poll_build_status(token, repo_id)

# --- limits
@app.command()
def limits():
    """Display user build and repository limits."""
    response = api.request_api("/user/limits")
    data = response.json()
    repo_limit = data.get("repo_limit")
    repo_count = data.get("repo_count")
    build_limit = data.get("build_limit")
    build_count = data.get("build_count")
    print("[bold]User limits:[/bold]")
    repo_str = f"[red]{repo_count}[/red]/[red]{repo_limit}[/red]" if repo_count == repo_limit else f"{repo_count}/{repo_limit}"
    print(f"Repositories: {repo_str}")
    build_str = f"[red]{build_count}[/red]/[red]{build_limit}[/red]" if build_count == build_limit else f"{build_count}/{build_limit}"
    print(f"Builds: {build_str}")

# --- status
@app.command()
def status():
    """Display status info of current repository."""
    token = helpers.get_token()
    conf = helpers.get_repo_config()
    response = api.request_api(f"/repos/build/{conf['repo_id']}/status", token=token)
    data = response.json()
    build_status =  data.get("status", "")
    print(f"Repository id: [dark_cyan]{conf['repo_id']}[/dark_cyan]")
    print(f"Build status: {utils.enrich_status(build_status)}")
    print(f"Repository details: {api.API_BASE}/repos/details/{conf['repo_id']}")

# --- remove
@app.command()
def remove(
        force: bool = typer.Option(False, "--force", "-f", help="Remove without prompting.")
    ):
    """Remove current repository from GitGlimpse."""
    token = helpers.get_token()
    conf = helpers.get_repo_config()
    print(f"[dim]Current repository id: '{conf['repo_id']}'[/dim]")
    if not force: typer.confirm(f"Are you sure, you want to remove this repository from GitGlimpse?", abort=True)
    api.request_api(f"/repos/remove/{conf['repo_id']}", method="POST", token=token, handle_codes=[204])
    config.repoconf_remove()
    print("Removed repository from GitGlimpse.")

# --- build
@app.command()
def build(
        force: bool = typer.Option(False, "--force", "-f", help="Schedule without prompting.")
    ):
    """Schedule a build for current repository."""
    token = helpers.get_token()
    conf = helpers.get_repo_config()
    if not force:
        print("Ensure that you pushed recent changes to GitHub.")
        typer.confirm("Continue?", abort=True)
    print(f"[dim]Scheduling a build for current repository (id: '{conf['repo_id']}')[/dim]")
    response = api.request_api(f"/repos/build/{conf['repo_id']}", method="POST", token=token, handle_codes=[202, 420, 425])
    if response.status_code == 420:
        print(f"[yellow]You have reached your usage limits.[/yellow]")
        try:
            error = response.json().get("error")
            if error: print(f"[dim]Error reason: {error}[/dim]")
        except JSONDecodeError: pass
        raise typer.Exit(1)
    elif response.status_code == 425:
        print(f"[yellow]This repository already has a pending build.[/yellow]")
        raise typer.Exit(1)
    # response.status_code == 202
    helpers.poll_build_status(token, conf['repo_id'])

# ---
if __name__ == "__main__":
    app()
