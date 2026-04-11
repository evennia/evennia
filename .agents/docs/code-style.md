# Code Style

## Formatting

Do not manually format code. Run `make format` (black + isort) after editing. It handles line length (100 chars), indentation, and import sorting. Use `make lint` to check without modifying.

## Docstrings

All modules, classes, functions, and methods must have docstrings. Use Google-style with Markdown formatting.

Import order (isort handles this, but be aware): stdlib → Twisted → Django → `evennia` → `evennia.contrib`

### Command Docstrings

Command class docstrings double as in-game help text. They use a special format with **2-space indentation**:

```python
"""
Short header

Usage:
  key[/switches] <mandatory args> [optional]

Switches:
  switch1    - description
  switch2    - description

Examples:
  usage example and output

Longer documentation.

"""
```

- `[ ]` for optional args, `< >` for descriptions of what to type, `||` to separate choices
- Commands requiring arguments should return a `Usage:` message when called with no args

### Function/Method Docstrings

Google-style with indented blocks:

```python
def funcname(a, b, d=False, **kwargs):
    """
    Brief description.

    Args:
        a (str): Description over
            multiple lines.
        b (int or str): Another argument.
        d (bool, optional): An optional keyword argument.

    Returns:
        str: The result.

    Raises:
        RuntimeException: If there is an error.

    Notes:
        Additional context.

    """
```
