from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print
import typer
import httpx
import auth

app = typer.Typer(help="CLI tool to manage and update shared GitHub repos with GitGlimpse.", no_args_is_help=True)
API_BASE = "http://127.0.0.1:5000/cli"

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
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="[bold green]Verifying token...[/bold green]", total=None)
        try:
            response = httpx.get(
                f"{API_BASE}/user", 
                headers={"Authorization": f"Bearer {token}"}, 
                timeout=10.0
            )
        except httpx.RequestError:
            print("[bold red]Connection error: Could not reach the server.")
            raise typer.Exit(1)
    if response.status_code == 200:
        auth.save_token(token)
        username =  response.json().get("username")
        print(f"[bold green]Success![/bold green] Authenticated as [cyan]{username}[/cyan].")
    else:
        print("[bold red]Authentication failed: Invalid or revoked token.[/bold red]")
        if response.text: print(f"[dim]Error reason: {response.text}[/dim]")
        raise typer.Exit(code=1)

@app.command()
def whoami():
    """Check the currently logged-in user."""
    token = auth.load_token()
    if not token:
        print("[yellow]Not logged in. Run 'python -m gitgl.main login' first[/yellow]")
        raise typer.Exit(1)
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="[bold green]Connecting to the server...[/bold green]", total=None)
        try:
            response = httpx.get(
                f"{API_BASE}/user", 
                headers={"Authorization": f"Bearer {token}"}, 
                timeout=10.0
            )
        except httpx.RequestError:
            print("[bold red]Connection error: Could not reach the server.")
            raise typer.Exit(1)
    if response.status_code == 200:
        username =  response.json().get("username")
        print(f"Authenticated as [cyan]{username}[/cyan].")
    else:
        print("[bold red]Authentication failed: Invalid or revoked token.[/bold red]")
        if response.text: print(f"[dim]Error reason: {response.text}[/dim]")
        raise typer.Exit(code=1)


@app.command()
def logout():
    """Clear stored local credentials."""
    if not auth.load_token():
        print("[yellow]You are not currently logged in.[/yellow]")
        raise typer.Exit(0)
    auth.remove_token()
    print("[bold green]Logged out successfully. Stored credentials removed.[/bold green]")

if __name__ == "__main__":
    app()

# c567dde96a2cb35304af1c3816c21143a5028e7a6f9d9b4be369c516fa2819fe