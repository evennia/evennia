# PyPy Support

## Notes about PyPy support

Although not actively supported PyPy should work without problems, or at least not too many. Every 
night the official test suite is run against PyPy so if you want to use it you can start checking
the latest [CI results against master branch](https://github.com/evennia/evennia/actions/workflows/github_action_pypy_test_suite.yml).

## PyPy Install

Evennia requires an interpreter compatible with Python 3.9. Some Linux distributions include it
(currently only Fedora), but for most others the easiest method is to use Pyenv:

1. install `Git` and other required [build dependencies](https://github.com/pyenv/pyenv/wiki#suggested-build-environment)
2. install Pyenv by following official [docs here](https://github.com/pyenv/pyenv-installer#install)
  (it's one command). **Remember to follow the instructions given at the end of the install!**
3. checking which pypy3.9 versions are available excluding `src` flavors:

    pyenv install -l | grep pypy3.9 | grep -v src

4. choose one by setting an env var (depends on output you get with the command before):

    EVENNIA_PYPY_VERSION=pypy3.9-7.3.9

5. install choosen version:

    pyenv install $EVENNIA_PYPY_VERSION

6. create and activate a virtualenv with choosen version

    pyenv virtualenv $EVENNIA_PYPY_VERSION evennia-venv
    pyenv activate evennia-venv

7. now you can continue following summary from [here](https://www.evennia.com/docs/1.0-dev/Setup/Installation-Git.html#summary), point `5.`


## Additional requirements

Based on your setup, you could need additional packages to be installed along the normal
requirements.

### PostgreSQL users

Because some lack of functionality, a PsycoPG drop-in replacement named 
[psycopg2cffi](https://github.com/chtd/psycopg2cffi) is currently needed when using PyPy so
you have to install it within your pypy virtualenv:

```
# install build dependencies
sudo apt-get install libpq-dev
# install actual package
pip install psycopg2cffi
```

Once installed, Evennia will automatically take care to register a compatibility layer so no other
action is needed.
