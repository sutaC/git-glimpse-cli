from glimpsecli import config, utils, api, helpers
from json import JSONDecodeError
from rich.panel import Panel
from rich import print
import importlib.metadata
import typer
import sys

_DEBUG_MODE = True

app = typer.Typer(help="CLI tool to manage and update shared GitHub repos with GitGlimpse.", no_args_is_help=True)

# --- main
def version_callback(value: bool) -> None:
    """Display version of package."""
    if not value: return
    version = importlib.metadata.metadata("git-glimpse-cli").get("version")
    print(f"GitGlimpse CLI version: {version or "?"}")
    raise typer.Exit(0)

@app.callback()
def main(
        version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Display version of package.")
    ):
    """GitGlimpse CLI."""
    pass

# --- login
@app.command()
def login(
    token: str = typer.Option(
        ..., 
        prompt="Enter your CLI token", 
        hide_input=True, 
        help="Your personal access cli token from dashboard."),
        force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing session without prompting."),
        local: bool = typer.Option(False, "--local", "-l", help="Save config to local repository only.")
    ):
    """Authenticate cli with server."""
    if local: old_token = (config._repoconf_load() or {}).get("token")
    else: old_token = (config._cliconf_load() or {}).get("token")
    if not force and old_token:
        print("[yellow]You are already logged in.[/yellow]")
        if not typer.confirm("Do you want to overwrite your existing session?"):
            print("[dim]Login cancelled.[/dim]")
            raise typer.Exit(0)
    response = api.request_api("/cli/user", token=token)
    config.conf_save({"token": token}, local)
    username =  response.json().get("username")
    print(f"[bold green]Success![/bold green] Authenticated as [cyan]{username}[/cyan].")

# --- whoami
@app.command()
def whoami():
    """Check the currently logged-in user."""
    response = api.request_api("/cli/user")
    username =  response.json().get("username")
    print(f"Authenticated as [cyan]{username}[/cyan].")

# --- logout
@app.command()
def logout(
        local: bool = typer.Option(False, "--local", "-l", help="Alter config in local repository only.")
    ):
    """Clear stored local credentials."""
    if local: token = (config._repoconf_load() or {}).get("token")
    else: token = (config._cliconf_load() or {}).get("token")
    if not token:
        print("[yellow]You are not currently logged in.[/yellow]")
        raise typer.Exit(0)
    config.conf_save({"token": None})
    print("[bold green]Logged out successfully.[/bold green]\nStored credentials removed.")

# --- init
init_app = typer.Typer(help="Link or upload the current Git repository to GitGlimpse server.", no_args_is_help=True)
app.add_typer(init_app, name="init")

@init_app.command("link")
def init_link(
        url: str | None = typer.Option(None, help="GitHub repository URL."),
        detect: bool = typer.Option(True, help="Do you want to detect repository url automatically.")
    ):
    """Link current Git repository to existing one on GitGlimpse."""
    token = helpers.fget_token()
    if config.get_repo_id():
        print("Shared repository already initialised.")
        raise typer.Exit(0)
    url = helpers.get_or_prompt_url(url, detect)
    print("[dim]Linking to existing GitGlimpse repository.[/dim]")
    response = api.request_api("/cli/repos/fetch", method="POST", payload={"url": url}, token=token, handle_codes=[200, 404])
    if response.status_code == 404:
        print(f"[bold red]Could not find this repository ([cyan]'{url}'[/cyan]) on GitGlimpse server, provide a valid url.[/bold red]")
        raise typer.Exit(1)
    # response.status_code == 200
    repo_id = response.json().get('repo_id')
    print("[green]Repo was found on GitGlimpse server.[/green]")
    helpers.finalize_init(repo_id)
    print(f"Repository details: {config.get_api_url()}/repos/details/{repo_id}")

@init_app.command("new")
def init_new(
    url: str | None = typer.Option(None, help="GitHub repository URL."),
    is_private: bool | None = typer.Option(None, "--private/--public", help="Is repository public or private?"),
    force: bool = typer.Option(False, "--force", "-f", help="Upload without prompting about GitHub publish."),
    detect: bool = typer.Option(True, help="Do you want to detect repository url automatically.")
    ):
    """Upload and register current Git repository to GitGlimpse."""
    token = helpers.fget_token()
    if config.get_repo_id():
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
        "/cli/repos/add", 
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
    response = api.request_api("/cli/user/limits")
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
    token = helpers.fget_token()
    repo_id = helpers.fget_repo_id()
    response = api.request_api(f"/cli/repos/build/{repo_id}/status", token=token)
    data = response.json()
    build_status =  data.get("status", "")
    print(f"Repository id: [dark_cyan]{repo_id}[/dark_cyan]")
    print(f"Build status: {utils.enrich_status(build_status)}")
    print(f"Repository details: {config.get_api_url()}/repos/details/{repo_id}")

# --- remove
@app.command()
def remove(
        force: bool = typer.Option(False, "--force", "-f", help="Remove without prompting.")
    ):
    """Remove current repository from GitGlimpse."""
    token = helpers.fget_token()
    repo_id = helpers.fget_repo_id()
    print(f"[dim]Current repository id: '{repo_id}'[/dim]")
    if not force: typer.confirm(f"Are you sure, you want to remove this repository from GitGlimpse?", abort=True)
    api.request_api(f"/cli/repos/remove/{repo_id}", method="POST", token=token, handle_codes=[204])
    config.repoconf_remove()
    print("Removed repository from GitGlimpse.")

# --- build
@app.command()
def build(
        force: bool = typer.Option(False, "--force", "-f", help="Schedule without prompting.")
    ):
    """Schedule a build for current repository."""
    token = helpers.fget_token()
    repo_id = helpers.fget_repo_id()
    if not force:
        print("Ensure that you pushed recent changes to GitHub.")
        typer.confirm("Continue?", abort=True)
    print(f"[dim]Scheduling a build for current repository (id: '{repo_id}')[/dim]")
    response = api.request_api(f"/cli/repos/build/{repo_id}", method="POST", token=token, handle_codes=[202, 420, 425])
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
    helpers.poll_build_status(token, repo_id)

# --- config
config_app = typer.Typer(help="Configure your cli.", no_args_is_help=True)
app.add_typer(config_app, name="config")

@config_app.command("list")
def config_list(
        sensitive: bool = typer.Option(False, "--show-sensitive", help="Display sensitive data."),
        local: bool = typer.Option(None, "--local/--global", help="Display only local or global config.")
    ):
    """Get current cli config."""
    sensitive_keys = ["token", "repo_id"]
    lconf = config._repoconf_load() or {}
    gconf = config._cliconf_load() or {}
    if local is None:
        print("[bold]Current cli config[/bold]")
    elif local:
        print("[bold]Current LOCAL cli config[/bold]")
    else:
        print("[bold]Current GLOBAL cli config[/bold]")
    if local != False:
        for key, val in lconf.items():
            val = f"[dim][{key.upper()}][/dim]" if not sensitive and key in sensitive_keys else val
            print(f"{key}: {val}")
    if local != True:
        for key, val in gconf.items():
            if local is None and key in lconf: continue
            val = f"[dim][{key.upper()}][/dim]" if not sensitive and key in sensitive_keys else val
            print(f"{key}: {val}")

@config_app.command("url")
def config_url(
    url: str = typer.Argument(..., help="Api base url (e.g., http://localhost:8000 or https://gitglimpse.sutac.pl)"),
    local: bool = typer.Option(False, "--local", "-l", help="Save config to local repository only.")
):
    """Set the active api server url."""
    config.conf_save({"api_url": (url if url else None)}, local)
    if url:
        print(f"Api url updated to: {url}")
    else:
        print("Api url unset.")

@config_app.command("debug")
def config_debug(
        enabled: bool = typer.Argument(..., help="True to enable debug mode, False to disable."),
        local: bool = typer.Option(False, "--local", "-l", help="Save config to local repository only.")
    ):
    """Enable or disable verbose debug output and full crash stack traces."""
    config.conf_save({"debug": enabled}, local)
    status = "[bold green]enabled[/bold green]" if enabled else "[bold yellow]disabled[/bold yellow]"
    print(f"Debug mode {status}.")

# ---
def cli():
    try:
        app()
    except Exception as exc:
        if isinstance(exc, typer.Exit):
            raise exc
        if config.get_debug_mode(): 
            print("[bold yellow][DEBUG MODE ACTIVE] Full stack trace below:[/bold yellow]\n")
            raise exc
        print(f"[bold red]Fatal Error:[/bold red] {str(exc)}")
        print("[dim]Enable debug with 'glimpse config debug' for full diagnostic details.[/dim]")
        sys.exit(1)

if __name__ == "__main__":
    cli()