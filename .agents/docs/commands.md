# Development Commands

## Installation

Prefer `uv` over `pip` for faster installs.

```bash
uv pip install -e .          # or `make install`
uv pip install -e .[extra]   # optional deps (crypto, SSL, Jupyter, scipy, etc.)
```

## Game Lifecycle

```bash
evennia --init mygame    # create new game directory
cd mygame && evennia migrate
evennia start / stop / reload
evennia shell            # Django-aware Python shell
evennia istart           # interactive mode (for debugging with set_trace)
```

## Testing

```bash
make test                                        # full suite
make testp                                       # parallel (4 cores)
make tests=evennia.objects.tests test             # specific module
make tests=evennia.commands.tests.test_command test  # specific test file
```

## Formatting

```bash
make format   # black + isort
make lint     # black --check
```

## PR Conventions

- Feature PRs and contribs go against the `develop` branch
- Critical fixes go against `main`
- Keep unrelated changes in separate branches/PRs
