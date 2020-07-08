# Parsing command arguments, theory and best practices


This tutorial will elaborate on the many ways one can parse command arguments.  The first step after
[adding a command](Part1/Adding-Commands) usually is to parse its arguments.  There are lots of
ways to do it, but some are indeed better than others and this tutorial will try to present them.

If you're a Python beginner, this tutorial might help you a lot.  If you're already familiar with
Python syntax, this tutorial might still contain useful information.  There are still a lot of
things I find in the standard library that come as a surprise, though they were there all along.
This might be true for others.

In this tutorial we will:

- Parse arguments with numbers.
- Parse arguments with delimiters.
- Take a look at optional arguments.
- Parse argument containing object names.

## What are command arguments?

I'm going to talk about command arguments and parsing a lot in this tutorial.  So let's be sure we
talk about the same thing before going any further:

> A command is an Evennia object that handles specific user input.

For instance, the default `look` is a command.  After having created your Evennia game, and
connected to it, you should be able to type `look` to see what's around.  In this context, `look` is
a command.

> Command arguments are additional text passed after the command.

Following the same example, you can type `look self` to look at yourself.  In this context, `self`
is the text specified after `look`.  `" self"` is the argument to the `look` command.

Part of our task as a game developer is to connect user inputs (mostly commands) with actions in the
game.  And most of the time, entering commands is not enough, we have to rely on arguments for
specifying actions with more accuracy.

Take the `say` command.  If you couldn't specify what to say as a command argument (`say hello!`),
you would have trouble communicating with others in the game.  One would need to create a different
command for every kind of word or sentence, which is, of course, not practical.

Last thing: what is parsing?

> In our case, parsing is the process by which we convert command arguments into something we can
work with.

We don't usually use the command argument as is (which is just text, of type `str` in Python).  We
need to extract useful information.  We might want to ask the user for a number, or the name of
another character present in the same room.  We're going to see how to do all that now.

## Working with strings

In object terms, when you write a command in Evennia (when you write the Python class), the
arguments are stored in the `args` attribute.  Which is to say, inside your `func` method, you can
access the command arguments in `self.args`.

### self.args

To begin with, look at this example:

```python
class CmdTest(Command):

    """
    Test command.

    Syntax:
      test [argument]

    Enter any argument after test.

    """

    key = "test"

    def func(self):
        self.msg(f"You have entered: {self.args}.")
```

If you add this command and test it, you will receive exactly what you have entered without any
parsing:

```
> test Whatever
You have entered:  Whatever.
> test
You have entered: .
```

> The lines starting with `>` indicate what you enter into your client.  The other lines are what
you receive from the game server.

Notice two things here:

1. The left space between our command key ("test", here) and our command argument is not removed.
That's why there are two spaces in our output at line 2.  Try entering something like "testok".
2. Even if you don't enter command arguments, the command will still be called with an empty string
in `self.args`.

Perhaps a slight modification to our code would be appropriate to see what's happening.  We will
force Python to display the command arguments as a debug string using a little shortcut.

```python
class CmdTest(Command):

    """
    Test command.

    Syntax:
      test [argument]

    Enter any argument after test.

    """

    key = "test"

    def func(self):
        self.msg(f"You have entered: {self.args!r}.")
```

The only line we have changed is the last one, and we have added `!r` between our braces to tell
Python to print the debug version of the argument (the repr-ed version).  Let's see the result:

```
> test Whatever
You have entered: ' Whatever'.
> test
You have entered: ''.
> test And something with '?
You have entered: " And something with '?".
```

This displays the string in a way you could see in the Python interpreter.  It might be easier to
read... to debug, anyway.

I insist so much on that point because it's crucial: the command argument is just a string (of type
`str`) and we will use this to parse it.  What you will see is mostly not Evennia-specific, it's
Python-specific and could be used in any other project where you have the same need.

### Stripping

As you've seen, our command arguments are stored with the space.  And the space between the command
and the arguments is often of no importance.

> Why is it ever there?

Evennia will try its best to find a matching command.  If the user enters your command key with
arguments (but omits the space), Evennia will still be able to find and call the command.  You might
have seen what happened if the user entered `testok`.  In this case, `testok` could very well be a
command (Evennia checks for that) but seeing none, and because there's a `test` command, Evennia
calls it with the arguments `"ok"`.

But most of the time, we don't really care about this left space, so you will often see code to
remove it.  There are different ways to do it in Python, but a command use case is the `strip`
method on `str` and its cousins, `lstrip` and `rstrip`.

- `strip`: removes one or more characters (either spaces or other characters) from both ends of the
string.
- `lstrip`: same thing but only removes from the left end (left strip) of the string.
- `rstrip`: same thing but only removes from the right end (right strip) of the string.

Some Python examples might help:

```python
>>> '   this is '.strip() # remove spaces by default
'this is'
>>> "   What if I'm right?   ".lstrip() # strip spaces from the left
"What if I'm right?   "
>>> 'Looks good to me...'.strip('.') # removes '.'
'Looks good to me'
>>> '"Now, what is it?"'.strip('"?') # removes '"' and '?' from both ends
'Now, what is it'
```

Usually, since we don't need the space separator, but still want our command to work if there's no
separator, we call `lstrip` on the command arguments:

```python
class CmdTest(Command):

    """
    Test command.

    Syntax:
      test [argument]

    Enter any argument after test.

    """

    key = "test"

    def parse(self):
        """Parse arguments, just strip them."""
        self.args = self.args.lstrip()

    def func(self):
        self.msg(f"You have entered: {self.args!r}.")
```

> We are now beginning to override the command's `parse` method, which is typically useful just for
argument parsing.  This method is executed before `func` and so `self.args` in `func()` will contain
our `self.args.lstrip()`.

Let's try it:

```
> test Whatever
You have entered: 'Whatever'.
> test
You have entered: ''.
> test And something with '?
You have entered: "And something with '?".
> test     And something with lots of spaces
You have entered: 'And something with lots of spaces'.
```

Spaces at the end of the string are kept, but all spaces at the beginning are removed:

> `strip`, `lstrip` and `rstrip` without arguments will strip spaces, line breaks and other common
separators.  You can specify one or more characters as a parameter.  If you specify more than one
character, all of them will be stripped from your original string.

### Convert arguments to numbers

As pointed out, `self.args` is a string (of type `str`).  What if we want the user to enter a
number?

Let's take a very simple example: creating a command, `roll`, that allows to roll a six-sided die.
The player has to guess the number, specifying the number as argument.  To win, the player has to
match the number with the die.  Let's see an example:

```
> roll 3
You roll a die.  It lands on the number 4.
You played 3, you have lost.
> dice 1
You roll a die.  It lands on the number 2.
You played 1, you have lost.
> dice 1
You roll a die.  It lands on the number 1.
You played 1, you have won!
```

If that's your first command, it's a good opportunity to try to write it.  A command with a simple
and finite role always is a good starting choice.  Here's how we could (first) write it... but it
won't work as is, I warn you:

```python
from random import randint

from evennia import Command

class CmdRoll(Command):

    """
    Play random, enter a number and try your luck.

    Usage:
      roll <number>

    Enter a valid number as argument.  A random die will be rolled and you
    will win if you have specified the correct number.

    Example:
      roll 3

    """

    key = "roll"

    def parse(self):
        """Convert the argument to a number."""
        self.args = self.args.lstrip()

    def func(self):
        # Roll a random die
        figure = randint(1, 6) # return a pseudo-random number between 1 and 6, including both
        self.msg(f"You roll a die.  It lands on the number {figure}.")

        if self.args == figure: # THAT WILL BREAK!
            self.msg(f"You played {self.args}, you have won!")
        else:
            self.msg(f"You played {self.args}, you have lost.")
```

If you try this code, Python will complain that you try to compare a number with a string: `figure`
is a number and `self.args` is a string and can't be compared as-is in Python.  Python doesn't do
"implicit converting" as some languages do.  By the way, this might be annoying sometimes, and other
times you will be glad it tries to encourage you to be explicit rather than implicit about what to
do.  This is an ongoing debate between programmers.  Let's move on!

So we need to convert the command argument from a `str` into an `int`.  There are a few ways to do
it.  But the proper way is to try to convert and deal with the `ValueError` Python exception.

Converting a `str` into an `int` in Python is extremely simple: just use the `int` function, give it
the string and it returns an integer, if it could.  If it can't, it will raise `ValueError`.  So
we'll need to catch that.  However, we also have to indicate to Evennia that, should the number be
invalid, no further parsing should be done.  Here's a new attempt at our command with this
converting:

```python
from random import randint

from evennia import Command, InterruptCommand

class CmdRoll(Command):

    """
    Play random, enter a number and try your luck.

    Usage:
      roll <number>

    Enter a valid number as argument.  A random die will be rolled and you
    will win if you have specified the correct number.

    Example:
      roll 3

    """

    key = "roll"

    def parse(self):
        """Convert the argument to number if possible."""
        args = self.args.lstrip()

        # Convert to int if possible
        # If not, raise InterruptCommand.  Evennia will catch this
        # exception and not call the 'func' method.
        try:
            self.entered = int(args)
        except ValueError:
            self.msg(f"{args} is not a valid number.")
            raise InterruptCommand

    def func(self):
        # Roll a random die
        figure = randint(1, 6) # return a pseudo-random number between 1 and 6, including both
        self.msg(f"You roll a die.  It lands on the number {figure}.")

        if self.entered == figure:
            self.msg(f"You played {self.entered}, you have won!")
        else:
            self.msg(f"You played {self.entered}, you have lost.")
```

Before enjoying the result, let's examine the `parse` method a little more: what it does is try to
convert the entered argument from a `str` to an `int`.  This might fail (if a user enters `roll
something`).  In such a case, Python raises a `ValueError` exception.  We catch it in our
`try/except` block, send a message to the user and raise the `InterruptCommand` exception in
response to tell Evennia to not run `func()`, since we have no valid number to give it.

In the `func` method, instead of using `self.args`, we use `self.entered` which we have defined in
our `parse` method.  You can expect that, if `func()` is run, then `self.entered` contains a valid
number.

If you try this command, it will work as expected this time: the number is converted as it should
and compared to the die roll.  You might spend some minutes playing this game.  Time out!

Something else we could want to address: in our small example, we only want the user to enter a
positive number between 1 and 6.  And the user can enter `roll 0` or `roll -8` or `roll 208` for
that matter, the game still works.  It might be worth addressing.  Again, you could write a
condition to do that, but since we're catching an exception, we might end up with something cleaner
by grouping:

```python
from random import randint

from evennia import Command, InterruptCommand

class CmdRoll(Command):

    """
    Play random, enter a number and try your luck.

    Usage:
      roll <number>

    Enter a valid number as argument.  A random die will be rolled and you
    will win if you have specified the correct number.

    Example:
      roll 3

    """

    key = "roll"

    def parse(self):
        """Convert the argument to number if possible."""
        args = self.args.lstrip()

        # Convert to int if possible
        try:
            self.entered = int(args)
            if not 1 <= self.entered <= 6:
                # self.entered is not between 1 and 6 (including both)
                raise ValueError
        except ValueError:
            self.msg(f"{args} is not a valid number.")
            raise InterruptCommand

    def func(self):
        # Roll a random die
        figure = randint(1, 6) # return a pseudo-random number between 1 and 6, including both
        self.msg(f"You roll a die.  It lands on the number {figure}.")

        if self.entered == figure:
            self.msg(f"You played {self.entered}, you have won!")
        else:
            self.msg(f"You played {self.entered}, you have lost.")
```

Using grouped exceptions like that makes our code easier to read, but if you feel more comfortable
checking, afterward, that the number the user entered is in the right range, you can do so in a
latter condition.

> Notice that we have updated our `parse` method only in this last attempt, not our `func()` method
which remains the same.  This is one goal of separating argument parsing from command processing,
these two actions are best kept isolated.

### Working with several arguments

Often a command expects several arguments.  So far, in our example with the "roll" command, we only
expect one argument: a number and just a number.  What if we want the user to specify several
numbers?  First the number of dice to roll, then the guess?

> You won't win often if you roll 5 dice but that's for the example.

So we would like to interpret a command like this:

    > roll 3 12

(To be understood: roll 3 dice, my guess is the total number will be 12.)

What we need is to cut our command argument, which is a `str`, break it at the space (we use the
space as a delimiter).  Python provides the `str.split` method which we'll use.  Again, here are
some examples from the Python interpreter:

    >>> args = "3 12"
    >>> args.split(" ")
    ['3', '12']
    >>> args = "a command with several arguments"
    >>> args.split(" ")
    ['a', 'command', 'with', 'several', 'arguments']
    >>>

As you can see, `str.split` will "convert" our strings into a list of strings.  The specified
argument (`" "` in our case) is used as delimiter.  So Python browses our original string.  When it
sees a delimiter, it takes whatever is before this delimiter and append it to a list.

The point here is that `str.split` will be used to split our argument.  But, as you can see from the
above output, we can never be sure of the length of the list at this point:

    >>> args = "something"
    >>> args.split(" ")
    ['something']
    >>> args = ""
    >>> args.split(" ")
    ['']
    >>>

Again we could use a condition to check the number of split arguments, but Python offers a better
approach, making use of its exception mechanism.  We'll give a second argument to `str.split`, the
maximum number of splits to do.  Let's see an example, this feature might be confusing at first
glance:

    >>> args = "that is something great"
    >>> args.split(" ", 1) # one split, that is a list with two elements (before, after)
   ['that', 'is something great']
   >>>

Read this example as many times as needed to understand it.  The second argument we give to
`str.split` is not the length of the list that should be returned, but the number of times we have
to split.  Therefore, we specify 1 here, but we get a list of two elements (before the separator,
after the separator).

> What will happen if Python can't split the number of times we ask?

It won't:

    >>> args = "whatever"
    >>> args.split(" ", 1) # there isn't even a space here...
    ['whatever']
    >>>

This is one moment I would have hoped for an exception and didn't get one.  But there's another way
which will raise an exception if there is an error: variable unpacking.

We won't talk about this feature in details here.  It would be complicated.  But the code is really
straightforward to use.  Let's take our example of the roll command but let's add a first argument:
the number of dice to roll.

```python
from random import randint

from evennia import Command, InterruptCommand

class CmdRoll(Command):

    """
    Play random, enter a number and try your luck.

    Specify two numbers separated by a space.  The first number is the
    number of dice to roll (1, 2, 3) and the second is the expected sum
    of the roll.

    Usage:
      roll <dice> <number>

    For instance, to roll two 6-figure dice, enter 2 as first argument.
    If you think the sum of these two dice roll will be 10, you could enter:

        roll 2 10

    """

    key = "roll"

    def parse(self):
        """Split the arguments and convert them."""
        args = self.args.lstrip()

        # Split: we expect two arguments separated by a space
        try:
            number, guess = args.split(" ", 1)
        except ValueError:
            self.msg("Invalid usage.  Enter two numbers separated by a space.")
            raise InterruptCommand

        # Convert the entered number (first argument)
        try:
            self.number = int(number)
            if self.number <= 0:
                raise ValueError
        except ValueError:
            self.msg(f"{number} is not a valid number of dice.")
            raise InterruptCommand

        # Convert the entered guess (second argument)
        try:
            self.guess = int(guess)
            if not 1 <= self.guess <= self.number * 6:
                raise ValueError
        except ValueError:
            self.msg(f"{self.guess} is not a valid guess.")
            raise InterruptCommand

    def func(self):
        # Roll a random die X times (X being self.number)
        figure = 0
        for _ in range(self.number):
            figure += randint(1, 6)

        self.msg(f"You roll {self.number} dice and obtain the sum {figure}.")

        if self.guess == figure:
            self.msg(f"You played {self.guess}, you have won!")
        else:
            self.msg(f"You played {self.guess}, you have lost.")
```

The beginning of the `parse()` method is what interests us most:

```python
try:
    number, guess = args.split(" ", 1)
except ValueError:
    self.msg("Invalid usage.  Enter two numbers separated by a space.")
    raise InterruptCommand
```

We split the argument using `str.split` but we capture the result in two variables.  Python is smart
enough to know that we want what's left of the space in the first variable, what's right of the
space in the second variable.  If there is not even a space in the string, Python will raise a
`ValueError` exception.

This code is much easier to read than browsing through the returned strings of `str.split`.  We can
convert both variables the way we did previously.  Actually there are not so many changes in this
version and the previous one, most of it is due to name changes for clarity.

> Splitting a string with a maximum of splits is a common occurrence while parsing command
arguments.  You can also see the `str.rspli8t` method that does the same thing but from the right of
the string.  Therefore, it will attempt to find delimiters at the end of the string and work toward
the beginning of it.

We have used a space as a delimiter.  This is absolutely not necessary.  You might remember that
most default Evennia commands can take an `=` sign as a delimiter.  Now you know how to parse them
as well:

    >>> cmd_key = "tel"
    >>> cmd_args = "book = chest"
    >>> left, right = cmd_args.split("=") # mighht raise ValueError!
    >>> left
    'book '
    >>> right
    ' chest'
    >>>

### Optional arguments

Sometimes, you'll come across commands that have optional arguments.  These arguments are not
necessary but they can be set if more information is needed.  I will not provide the entire command
code here but just enough code to show the mechanism in Python:

Again, we'll use `str.split`, knowing that we might not have any delimiter at all.  For instance,
the player could enter the "tel" command like this:

    > tel book
    > tell book = chest

The equal sign is optional along with whatever is specified after it.  A possible solution in our
`parse` method would be:

```python
    def parse(self):
        args = self.args.lstrip()

        # = is optional
        try:
            obj, destination = args.split("=", 1)
        except ValueError:
            obj = args
            destination = None
```

This code would place everything the user entered in `obj` if she didn't specify any equal sign.
Otherwise, what's before the equal sign will go in `obj`, what's after the equal sign will go in
`destination`.  This makes for quick testing after that, more robust code with less conditions that
might too easily break your code if you're not careful.

> Again, here we specified a maximum numbers of splits.  If the users enters:

    > tel book = chest = chair

Then `destination` will contain: `" chest = chair"`.  This is often desired, but it's up to you to
set parsing however you like.

## Evennia searches

After this quick tour of some `str` methods, we'll take a look at some Evennia-specific features
that you won't find in standard Python.

One very common task is to convert a `str` into an Evennia object.  Take the previous example:
having `"book"`  in a variable is great, but we would prefer to know what the user is talking
about... what is this `"book"`?

To get an object from a string, we perform an Evennia search.  Evennia provides a `search` method on
all typeclassed objects (you will most likely use the one on characters or accounts).  This method
supports a very wide array of arguments and has [its own tutorial](Part1/Searching-Things).
Some examples of useful cases follow:

### Local searches

When an account or a character enters a command, the account or character is found in the `caller`
attribute.  Therefore, `self.caller` will contain an account or a character (or a session if that's
a session command, though that's not as frequent).  The `search` method will be available on this
caller.

Let's take the same example of our little "tel" command.  The user can specify an object as
argument:

```python
    def parse(self):
        name = self.args.lstrip()
```

We then need to "convert" this string into an Evennia object.  The Evennia object will be searched
in the caller's location and its contents by default (that is to say, if the command has been
entered by a character, it will search the object in the character's room and the character's
inventory).

```python
    def parse(self):
        name = self.args.lstrip()

        self.obj = self.caller.search(name)
```

We specify only one argument to the `search` method here: the string to search.  If Evennia finds a
match, it will return it and we keep it in the `obj` attribute.  If it can't find anything, it will
return `None` so we need to check for that:

```python
    def parse(self):
        name = self.args.lstrip()

        self.obj = self.caller.search(name)
        if self.obj is None:
            # A proper error message has already been sent to the caller
            raise InterruptCommand
```

That's it.  After this condition, you know that whatever is in `self.obj` is a valid Evennia object
(another character, an object, an exit...).

### Quiet searches

By default, Evennia will handle the case when more than one match is found in the search.  The user
will be asked to narrow down and re-enter the command.  You can, however, ask to be returned the
list of matches and handle this list yourself:

```python
    def parse(self):
        name = self.args.lstrip()

        objs = self.caller.search(name, quiet=True)
        if not objs:
            # This is an empty list, so no match
            self.msg(f"No {name!r} was found.")
            raise InterruptCommand
        
        self.obj = objs[0] # Take the first match even if there are several
```

All we have changed to obtain a list is a keyword argument in the `search` method: `quiet`.  If set
to `True`,  then errors are ignored and a list is always returned, so we need to handle it as such.
Notice in this example, `self.obj` will contain a valid object too, but if several matches are
found, `self.obj` will contain the first one, even if more matches are available.

### Global searches

By default, Evennia will perform a local search, that is, a search limited by the location in which
the caller is.  If you want to perform a global search (search in the entire database), just set the
`global_search` keyword argument to `True`:

```python
    def parse(self):
        name = self.args.lstrip()
        self.obj = self.caller.search(name, global_search=True)
```

## Conclusion

Parsing command arguments is vital for most game designers.  If you design "intelligent" commands,
users should be able to guess how to use them without reading the help, or with a very quick peek at
said help.  Good commands are intuitive to users.  Better commands do what they're told to do.  For
game designers working on MUDs, commands are the main entry point for users into your game.  This is
no trivial.  If commands execute correctly (if their argument is parsed, if they don't behave in
unexpected ways and report back the right errors), you will have happier players that might stay
longer on your game.  I hope this tutorial gave you some pointers on ways to improve your command
parsing.  There are, of course, other ways you will discover, or ways you are already using in your
code.