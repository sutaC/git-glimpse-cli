# GitGlimpse CLI

![GitHub release](https://img.shields.io/github/v/release/sutaC/git-glimpse-cli)
![GitHub last commit](https://img.shields.io/github/last-commit/sutaC/git-glimpse-cli)
![License](https://img.shields.io/github/license/sutaC/git-glimpse-cli)

A command-line interface to manage, synchronize, and monitor shared GitHub repositories via the GitGlimpse platform.

---

**GitGlimpse website:** [gitglimpse.sutac.pl](https://gitglimpse.sutac.pl/)

**GitGlimpse on GitHub:** [github.com/sutaC/git-glimpse-cli](https://github.com/sutaC/git-glimpse-cli/)

**Author:** [sutaC](https://github.com/sutaC)

## Installation

Install the latest version globally via pip:

```bash
pip install git-glimpse-cli
```

## Quickstart

1. Log in with your GitGlimpse CLI token. It will be saved to your global user configuration.
    > You will be able to create one on your GitGlimpse user panel at https://gitglimpse.sutac.pl/user#hCliTokens
    ```bash
    glimpse login <YOUR_API_TOKEN>
    ```
2. Initialize a Repository.
    > Navigate to your local Git repository, ensure it is uplaoded to GitHub and link it to GitGlimpse. This creates a .shared-repo.json file to track the project.
    ```bash
    cd my-project
    glimpse init <new/link>
    ```
3. Check status.
    ```bash
    glimpse status
    ```
4. Schedule the build to update GitGlimpse display.
    ```bash
    glimpse build
    ```

## Configuration

GitGlimpse CLI uses holds your configuration at `~/.config/glimpsecli/config.json`, and local repository settings are stored at `./.shared-repo.json`.

Configuration hierarchy:

```
Most important -> Local repo config -> Global cli config
```

### Advanced Settings

| Command                | Description                                                                 |
| ---------------------- | --------------------------------------------------------------------------- |
| `glimpse config debug` | Enables verbose debug mode, printing stack traces.                          |
| `glimpse config url`   | Overrides the default production server with a custom backend or localhost. |

## Development

1. Clone the repository and install it in editable mode:
    ```bash
    git clone https://github.com/sutaC/git-glimpse-cli.git
    cd git-glimpse-cli
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    ```
2. Point the CLI to your local development server (use `--local` to not propagate over your real global config):
    ```bash
    glimpse config url http://localhost:5000 --local
    ```
