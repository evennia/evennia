# Using Travis

Evennia uses [Travis CI](http://travis-ci.org/) to check that it's building successfully after every
commit to its Github repository (you can for example see the `build: passing` badge at the top of
Evennia's [Readme file](https://github.com/evennia/evennia)). If your game is open source on Github
you may use Travis for free. See [the Travis docs](http://docs.travis-ci.com/user/getting-started/)
for how to get started.

After logging in you need to point Travis to your repository on github. One further thing you need
to set up yourself is a Travis config file named `.travis.yml` (note the initial period `.`). This
should be created in the _root_ of your game directory.

``` yaml
dist: xenial
language: python
cache: pip

python:
  - "3.7"
  - "3.8"

install:
  - git clone https://github.com/evennia/evennia.git ../evennia
  - pip install -e ../evennia

script:
  - evennia test --settings settings.py
  
```

Here we tell Travis how to download and install Evennia into a folder a level up from your game dir.
It will then install the server (so the `evennia` command is available) and run the tests only for
your game dir (based on your `settings.py` file in `server/conf/`).

Running this will not actually do anything though, because there are no unit tests in your game dir
yet. [We have a page](./Unit-Testing.md) on how we set those up for Evennia, you should be able to refer
to that for making tests fitting your game.