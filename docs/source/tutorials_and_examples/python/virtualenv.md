```python
class Documentation:
    RATING = "Acceptable" # Better structure
```

#Virtualenv
 
- `python -m virtualenv <name>` - initialize a new virtualenv `<name>` in a new folder `<name>` in the current location. Called `evenv` in these docs.
- `python -m virtualenv -p path/to/alternate/python_executable <name>` - create a virtualenv using another Python version than default.
- `source <folder_name>/bin/activate`(linux/mac) - activate the virtualenv in `<folder_name>`.
  - `<folder_name>\Scripts\activate` (windows) 
- `deactivate` - turn off the currently activated virtualenv.

A virtualenv is 'activated' only for the console/terminal it was started in, but it's safe to activate the same virtualenv many times in different windows if you want. Once activated, all Python packages now installed with [pip](#pip) will install to `evenv` rather than to a global location like `/usr/local/bin` or `C:\Program Files`.

> Note that if you have root/admin access you *could* install Evennia globally just fine, without using a virtualenv. It's strongly discouraged and considered bad practice though. Experienced Python developers tend to rather create one new virtualenv per project they are working on, to keep the varying installs cleanly separated from one another. 

When you execute Python code within this activated virtualenv, *only* those packages installed within will be possible to `import` into your code. So if you installed a Python package globally on your computer, you'll need to install it again in your virtualenv.

> Virtualenvs *only* deal with Python programs/packages. Other programs on your computer couldn't care less if your virtualenv is active or not. So you could use `git` without the virtualenv being active, for example.

When your virtualenv is active you should see your console/terminal prompt change to 

    (evenv) ...

... or whatever name you gave the virtualenv when you initialized it. 

> We sometimes say that we are "in" the virtualenv when it's active. But just to be clear - you never have to actually `cd` into the `evenv` folder. You can activate it from anywhere and will still be considered "in" the virtualenv wherever you go until you `deactivate` or close the console/terminal. 

So, when do I *need* to activate my virtualenv? If the virtualenv is not active, none of the Python packages/programs you installed in it will be available to you. So at a minimum, *it needs to be activated whenever you want to use the `evennia` command* for any reason. 

