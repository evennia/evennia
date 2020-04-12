```python
class Documentation:
    RATING = "Exceptional"
```

# Installation
Note: You don't need to make anything visible to the 'net in order to run and
test out Evennia. Apart from downloading and updating you don't even need an
internet connection until you feel ready to share your game with the world.

## Linux/Unix

1. Install dependencies: `sudo apt-get install python3 git` 
2. Create a folder you would like Evennia to live in
3. Open a Terminal and navigate to this folder
4. Run the following commands
```linux
git clone https://github.com/evennia/evennia.git
python3 -m virtualenv evenv
source evenv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -e evennia
evennia --init mygame
cd mygame
evennia migrate
evennia start` (make sure to make a  superuser when asked)
```

Related topics:
- [Troubleshooting](../../related_topics/troubleshooting/troubleshooting)
- [Linux troubleshooting](../../related_topics/troubleshooting/linux-troubleshooting)

## MacOS

1. Install [Python 3.8](http://www.python.org) and [Git](http://code.google.com/p/git-osx-installer/)
2. Create a folder you would like Evennia to live in
3. Open a Terminal and navigate to this folder
4. Run the following commands
```linux
git clone https://github.com/evennia/evennia.git
python3 -m virtualenv evenv
source evenv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -e evennia
evennia --init mygame
cd mygame
evennia migrate
evennia start` (make sure to make a  superuser when asked)
```
Related topics:
- [Troubleshooting](../../related_topics/troubleshooting/troubleshooting)

## Windows (Vista, Win7, Win8, Win10)

1. Install [Python 3.8](http://www.python.org) and [Git](http://git-scm.com/)
2. Create a folder you would like Evennia to live in
3. Open a Command Prompt and navigate to this folder
4. Run the following commands

```windows
git clone https://github.com/evennia/evennia.git
python -m virtualenv evenv
source evenv\Scripts\activate
pip install --upgrade pip wheel setuptools
pip install -e evennia
evennia --init mygame
cd mygame
evennia migrate
evennia start` (make sure to make a  superuser when asked)
```

Related topics:
- [Troubleshooting](../../related_topics/troubleshooting/troubleshooting)
- [Windows troubleshooting](../../related_topics/troubleshooting/windows-troubleshooting)

## Docker

We also release [Docker images](../../related_topics/technical/evennia-docker) based on `master` and `develop` branches.
