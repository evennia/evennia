# PyPy Support

## Notes about PyPy support

Although not actively supported PyPy should work without problems, or at least not too many. Every 
night the official test suite is run against PyPy so if you want to use it you can start checking
the latest [CI results against master branch](https://github.com/evennia/evennia/actions/workflows/github_action_pypy_test_suite.yml).

## Additional requirements

Based on your setup, you could need additional packages to be installed along the normal
requirements.

### PostgreSQL users

Because some lack of functionality, a PsycoPG drop-in replacement named 
[psycopg2cffi](https://github.com/chtd/psycopg2cffi) is currently needed when using PyPy:

```
pip install psycopg2cffi
```

Once installed, Evennia will automatically take care to register a compatibility layer so no other
action is needed.
