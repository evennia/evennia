# evennia-docs
Documentation for the Evennia MUD creation system.

The live documentation is available at `https://evennia.github.io/evennia/`.

# building the docs

## Prerequisits

- Clone the evennia repository.
- Follow the normal Evennia Getting-Started instructions. Use a virtualenv and create
a new game folder called `gamedir` at the same level as your `evennia` repo and run migrations in it.

```
  (top)
  |
  ----- evennia/
  |
  ----- gamedir/
```

- Make sure you are in your virtualenv. Go to `evennia/docs/` and install the `requirements.txt` or run `make install` to do the same.


## Building the docs.

With your build environment set up as above, stand in the `evennia/docs` directory and run `make local`. This builds the documentation.
