# Batch Code Processor


For an introduction and motivation to using batch processors, see [here](./Batch-Processors.md). This
page describes the Batch-*code* processor. The Batch-*command* one is covered [here](Batch-Command-
Processor).

## Basic Usage

The batch-code processor is a superuser-only function, invoked by 

     > @batchcode path.to.batchcodefile

Where `path.to.batchcodefile` is the path to a *batch-code file*. Such a file should have a name
ending in "`.py`" (but you shouldn't include that in the path). The path is given like a python path
relative to a folder you define to hold your batch files, set by `BATCH_IMPORT_PATH` in your
settings. Default folder is (assuming your game is called "mygame") `mygame/world/`. So if you want
to run the example batch file in `mygame/world/batch_code.py`, you could simply use

     > @batchcode batch_code

This will try to run through the entire batch file in one go. For more gradual, *interactive*
control you can use the `/interactive` switch.  The switch `/debug` will put the processor in
*debug* mode. Read below for more info.

## The batch file

A batch-code file is a normal Python file. The difference is that since the batch processor loads
and executes the file rather than importing it, you can reliably update the file, then call it
again, over and over and see your changes without needing to `@reload` the server. This makes for
easy testing. In the batch-code file you have also access to the following global variables:

- `caller` - This is a reference to the object running the batchprocessor.
- `DEBUG` - This is a boolean that lets you determine if this file is currently being run in debug-
mode or not. See below how this can be useful.

Running a plain Python file through the processor will just execute the file from beginning to end.
If you want to get more control over the execution you can use the processor's *interactive* mode.
This runs certain code blocks on their own, rerunning only that part until you are happy with it. In
order to do this you need to add special markers to your file to divide it up into smaller chunks.
These take the form of comments, so the file remains valid Python.

Here are the rules of syntax of the batch-code `*.py` file. 

- `#CODE` as the first on a line marks the start of a *code* block. It will last until the beginning
of another marker or the end of the file. Code blocks contain functional python code. Each `#CODE`
block will be run in complete isolation from other parts of the file, so make sure it's self-
contained.
- `#HEADER` as the first on a line marks the start of a *header* block. It lasts until the next
marker or the end of the file. This is intended to hold imports and variables you will need for all
other blocks .All python code defined in a header block will always be inserted at the top of every
`#CODE` blocks in the file. You may have more than one `#HEADER` block, but that is equivalent to
having one big one. Note that you can't exchange data between code blocks, so editing a header-
variable in one code block won't affect that variable in any other code block!
- `#INSERT path.to.file` will insert another batchcode (Python) file at that position.
- A `#` that is not starting a `#HEADER`, `#CODE` or `#INSERT` instruction is considered a comment.
- Inside a block, normal Python syntax rules apply. For the sake of indentation, each block acts as
a separate python module.

Below is a version of the example file found in `evennia/contrib/tutorial_examples/`. 

```python
    #
    # This is an example batch-code build file for Evennia. 
    #
    
    #HEADER
    
    # This will be included in all other #CODE blocks
    
    from evennia import create_object, search_object
    from evennia.contrib.tutorial_examples import red_button
    from typeclasses.objects import Object
    
    limbo = search_object('Limbo')[0]
    
    
    #CODE 
 
    red_button = create_object(red_button.RedButton, key="Red button", 
                               location=limbo, aliases=["button"])
    
    # caller points to the one running the script
    caller.msg("A red button was created.")
    
    # importing more code from another batch-code file
    #INSERT batch_code_insert
    
    #CODE
    
    table = create_object(Object, key="Blue Table", location=limbo)
    chair = create_object(Object, key="Blue Chair", location=limbo)
    
    string = f"A {table} and {chair} were created."
    if DEBUG:
        table.delete()
        chair.delete()
        string += " Since debug was active, they were deleted again." 
    caller.msg(string)
```

This uses Evennia's Python API to create three objects in sequence. 

## Debug mode

Try to run the example script with 

     > @batchcode/debug tutorial_examples.example_batch_code

The batch script will run to the end and tell you it completed. You will also get messages that the
button and the two pieces of furniture were created.  Look around and you should see the button
there. But you won't see any chair nor a table! This is because we ran this with the `/debug`
switch, which is directly visible as `DEBUG==True` inside the script. In the above example we
handled this state by deleting the chair and table again.

The debug mode is intended to be used when you test out a batchscript. Maybe you are looking for
bugs in your code or try to see if things behave as they should. Running the script over and over
would then create an ever-growing stack of chairs and tables, all with the same name. You would have
to go back and painstakingly delete them later.

## Interactive mode

Interactive mode works very similar to the [batch-command processor counterpart](Batch-Command-
Processor). It allows you more step-wise control over how the batch file is executed. This is useful
for debugging or for picking and choosing only particular blocks to run.  Use `@batchcode` with the
`/interactive` flag to enter interactive mode.

     > @batchcode/interactive tutorial_examples.batch_code

You should see the following:

    01/02: red_button = create_object(red_button.RedButton, [...]         (hh for help) 

This shows that you are on the first `#CODE` block, the first of only two commands in this batch
file. Observe that the block has *not* actually been executed at this point!

To take a look at the full code snippet you are about to run, use `ll` (a batch-processor version of
`look`).

```python
    from evennia.utils import create, search
    from evennia.contrib.tutorial_examples import red_button
    from typeclasses.objects import Object
    
    limbo = search.objects(caller, 'Limbo', global_search=True)[0]

    red_button = create.create_object(red_button.RedButton, key="Red button", 
                                      location=limbo, aliases=["button"])
    
    # caller points to the one running the script
    caller.msg("A red button was created.")
```

Compare with the example code given earlier. Notice how the content of `#HEADER` has been pasted at
the top of the `#CODE` block. Use `pp` to actually execute this block (this will create the button
and give you a message). Use `nn` (next) to go to the next command. Use `hh` for a list of commands.

If there are tracebacks, fix them in the batch file, then use `rr` to reload the file. You will
still be at the same code block and can rerun it easily with `pp` as needed. This makes for a simple
debug cycle. It also allows you to rerun individual troublesome blocks - as mentioned, in a large
batch file this can be very useful (don't forget the `/debug` mode either).

Use `nn` and `bb` (next and back) to step through the file; e.g. `nn 12` will jump 12 steps forward
(without processing any blocks in between). All normal commands of Evennia should work too while
working in interactive mode.

## Limitations and Caveats

The batch-code processor is by far the most flexible way to build a world in Evennia. There are
however some caveats you need to keep in mind.

### Safety
Or rather the lack of it. There is a reason only *superusers* are allowed to run the batch-code
processor by default. The code-processor runs **without any Evennia security checks** and allows
full access to Python. If an untrusted party could run the code-processor they could execute
arbitrary python code on your machine, which is potentially a very dangerous thing.  If you want to
allow other users to access the batch-code processor you should make sure to run Evennia as a
separate and very limited-access user on your machine (i.e. in a 'jail'). By comparison, the batch-
command processor is much safer since the user running it is still 'inside' the game and can't
really do anything outside what the game commands allow them to.

### No communication between code blocks
Global variables won't work in code batch files, each block is executed as stand-alone environments.
`#HEADER` blocks are literally pasted on top of each `#CODE` block so updating some header-variable
in your block will not make that change available in another block. Whereas a python execution
limitation, allowing this would also lead to very hard-to-debug code when using the interactive mode
- this would be a classical example of "spaghetti code".

The main practical issue with this is when building e.g. a room in one code block and later want to
connect that room with a room you built in the current block. There are two ways to do this:

- Perform a database search for the name of the room you created (since you cannot know in advance
which dbref it got assigned). The problem is that a name may not be unique (you may have a lot of "A
dark forest" rooms). There is an easy way to handle this though - use [Tags](./Tags.md) or *Aliases*. You
can assign any number of tags and/or aliases to any object. Make sure that one of those tags or
aliases is unique to the room (like "room56") and you will henceforth be able to always uniquely
search and find it later.
- Use the `caller` global property as an inter-block storage. For example, you could have a
dictionary of room references in an `ndb`:
    ```python
    #HEADER 
    if caller.ndb.all_rooms is None:
        caller.ndb.all_rooms = {}

    #CODE 
    # create and store the castle
    castle = create_object("rooms.Room", key="Castle")
    caller.ndb.all_rooms["castle"] = castle

    #CODE 
    # in another node we want to access the castle
    castle = caller.ndb.all_rooms.get("castle")
    ```
Note how we check in `#HEADER` if `caller.ndb.all_rooms` doesn't already exist before creating the
dict. Remember that `#HEADER` is copied in front of every `#CODE` block. Without that `if` statement
we'd be wiping the dict every block!

### Don't treat a batchcode file like any Python file 
Despite being a valid Python file, a batchcode file should *only* be run by the batchcode processor.
You should not do things like define Typeclasses or Commands in them, or import them into other
code. Importing a module in Python will execute base level of the module, which in the case of your
average batchcode file could mean creating a lot of new objects every time.
### Don't let code rely on the batch-file's real file path

When you import things into your batchcode file, don't use relative imports but always import with
paths starting from the root of your game directory or evennia library. Code that relies on the
batch file's "actual" location *will fail*. Batch code files are read as text and the strings
executed. When the code runs it has no knowledge of what file those strings where once a part of.