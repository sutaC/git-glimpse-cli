from rich.progress import Progress, SpinnerColumn, TextColumn
from contextlib import nullcontext
from json import JSONDecodeError
from glimpsecli import auth
from rich import print
import typer
import httpx

API_BASE = "http://127.0.0.1:5000"
API_URL = f"{API_BASE}/cli"

def get_token() -> str:
    token = auth.load_token()
    if not token:
        print("[yellow]Not logged in. Run 'glimpse login' first.[/yellow]")
        raise typer.Exit(code=1)
    return token

def request_api(
        url_path: str,
        method: str = "GET",
        token: str | None = None, 
        handle_codes: list[int] = [200],
        payload: dict | None = None,
        quiet=False
    ) -> httpx.Response:
    if not token:
        token = get_token()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) if not quiet else nullcontext() as progress:
        if progress: 
            progress.add_task(description="[bold green]Connecting to server...[/bold green]", total=None)
        try:
            response = httpx.request(
                method,
                f"{API_URL}{url_path}",
                headers={"Authorization": f"Bearer {token}"}, 
                timeout=10.0,
                json=payload
            )
        except httpx.RequestError:
            print("[bold red]Connection error: Could not reach the server.")
            raise typer.Exit(1)
    if response.status_code in handle_codes:
        return response
    elif response.status_code == 401:
        print("[bold red]Authentication failed: Invalid or revoked token.[/bold red]")
        try:
            error = response.json().get("error")
            if error: print(f"[dim]Error reason: {error}[/dim]")
        except JSONDecodeError: pass
        auth.remove_token()
        print("[yellow]Your session has expired. Please run 'glimpse login' again [/yellow].")
        raise typer.Exit(1)
    elif response.status_code == 403:
        print("[bold red]Authentication failed: Invalid or revoked token.[/bold red]")
        try:
            error = response.json().get("error")
            if error: print(f"[dim]Error reason: {error}[/dim]")
        except JSONDecodeError: pass
        raise typer.Exit(1)
    else: 
        print(f"[bold red]Unexpected error ocurred. [dim](status code: {response.status_code})[/dim][/bold red]")
        try:
            error = response.json().get("error")
            if error: print(f"[dim red]Error reason: {error}[/dim red]")
        except JSONDecodeError: pass
        raise typer.Exit(1)