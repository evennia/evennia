# Batch Command Processor


For an introduction and motivation to using batch processors, see [here](./Batch-Processors.md). This
page describes the Batch-*command* processor. The Batch-*code* one is covered [here](Batch-Code-
Processor).

The batch-command processor is a superuser-only function, invoked by 

     > batchcommand path.to.batchcmdfile

Where `path.to.batchcmdfile` is the path to a *batch-command file* with the "`.ev`" file ending.
This path is given like a python path relative to a folder you define to hold your batch files, set
with `BATCH_IMPORT_PATH` in your settings. Default folder is (assuming your game is in the `mygame`
folder) `mygame/world`. So if you want to run the example batch file in
`mygame/world/batch_cmds.ev`, you could use

     > batchcommand batch_cmds

A batch-command file contains a list of Evennia in-game commands separated by comments. The
processor will run the batch file from beginning to end. Note that *it will not stop if commands in
it fail* (there is no universal way for the processor to know what a failure looks like for all
different commands). So keep a close watch on the output, or use *Interactive mode* (see below) to
run the file in a more controlled, gradual manner.

## The batch file

The batch file is a simple plain-text file containing Evennia commands. Just like you would write
them in-game, except you have more freedom with line breaks.

Here are the rules of syntax of an `*.ev` file. You'll find it's really, really simple:

- All lines having the `#` (hash)-symbol *as the first one on the line* are considered *comments*. All non-comment lines are treated as a command and/or their arguments.
- Comment lines have an actual function -- they mark the *end of the previous command definition*. So never put two commands directly after one another in the file - separate them with a comment, or the second of the two will be considered an argument to the first one. Besides, using plenty of comments is good practice anyway.
- A line that starts with the word `#INSERT` is a comment line but also signifies a special instruction. The syntax is `#INSERT <path.batchfile>` and tries to import a given batch-cmd file into this one. The inserted batch file (file ending `.ev`) will run normally from the point of the `#INSERT` instruction.
- Extra whitespace in a command definition is *ignored*.  - A completely empty line translates in to a line break in texts. Two empty lines thus means a new paragraph (this is obviously only relevant for commands accepting such formatting, such as the `@desc` command).
- The very last command in the file is not required to end with a comment.
- You *cannot* nest another `batchcommand` statement into your batch file. If you want to link many batch-files together, use the `#INSERT` batch instruction instead. You also cannot launch the `batchcode` command from your batch file, the two batch processors are not compatible.

Below is a version of the example file found in `evennia/contrib/tutorial_examples/batch_cmds.ev`. 

```bash
    #
    # This is an example batch build file for Evennia. 
    #
    
    # This creates a red button
    @create button:tutorial_examples.red_button.RedButton
    # (This comment ends input for @create)
    # Next command. Let's create something. 
    @set button/desc = 
      This is a large red button. Now and then 
      it flashes in an evil, yet strangely tantalizing way. 
    
      A big sign sits next to it. It says:

    
    -----------
    
     Press me! 
    
    -----------

    
      ... It really begs to be pressed! You 
    know you want to! 
    
    # This inserts the commands from another batch-cmd file named
    # batch_insert_file.ev.
    #INSERT examples.batch_insert_file
    
      
    # (This ends the @set command). Note that single line breaks 
    # and extra whitespace in the argument are ignored. Empty lines 
    # translate into line breaks in the output.
    # Now let's place the button where it belongs (let's say limbo #2 is 
    # the evil lair in our example)
    @teleport #2
    # (This comments ends the @teleport command.) 
    # Now we drop it so others can see it. 
    # The very last command in the file needs not be ended with #.
    drop button
```

To test this, run `@batchcommand` on the file: 

    > batchcommand contrib.tutorial_examples.batch_cmds

A button will be created, described and dropped in Limbo. All commands will be executed by the user calling the command.

> Note that if you interact with the button, you might find that its description changes, loosing your custom-set description above. This is just the way this particular object works.

## Interactive mode

Interactive mode allows you to more step-wise control over how the batch file is executed. This is useful for debugging and also if you have a large batch file and is only updating a small part of it -- running the entire file again would be a waste of time (and in the case of `create`-ing objects you would to end up with multiple copies of same-named objects, for example). Use `batchcommand` with the `/interactive` flag to enter interactive mode. 

     > @batchcommand/interactive tutorial_examples.batch_cmds

You will see this:

    01/04: @create button:tutorial_examples.red_button.RedButton  (hh for help) 

This shows that you are on the `@create` command, the first out of only four commands in this batch file. Observe that the command `@create` has *not* been actually processed at this point!

To take a look at the full command you are about to run, use `ll` (a batch-processor version of
`look`). Use `pp` to actually process the current command (this will actually `@create` the button) -- and make sure it worked as planned. Use `nn` (next) to go to the next command.  Use `hh` for a list of commands.

If there are errors, fix them in the batch file, then use `rr` to reload the file. You will still be at the same command and can rerun it easily with `pp` as needed. This makes for a simple debug cycle. It also allows you to rerun individual troublesome commands - as mentioned, in a large batch file this can be very useful. Do note that in many cases, commands depend on the previous ones (e.g. if `create` in the example above had failed, the following commands would have had nothing to operate on).

Use `nn` and `bb` (next and back) to step through the file; e.g. `nn 12` will jump 12 steps forward (without processing any command in between). All normal commands of Evennia should work too while working in interactive mode.

## Limitations and Caveats

The main issue with batch-command builds is that when you run a batch-command script you (*you*, as in your character) are actually moving around in the game creating and building rooms in sequence, just as if you had been entering those commands manually, one by one. 

You have to take this into account when creating the file, so that you can 'walk' (or teleport) to the right places in order. It also means that you may be affected by the things you create, such as mobs attacking you or traps immediately hurting you. 

If you know that your rooms and objects are going to be deployed via a batch-command script, you can plan for this beforehand. To help with this, you can use the fact that the non-persistent Attribute `batch_batchmode` is _only_ set while the batch-processor is running. Here's an example of how to use it: 

```python
class HorribleTrapRoom(Room):
    # ... 
    def at_object_receive(self, received_obj, source_location, **kwargs):
        """Apply the horrible traps the moment the room is entered!"""
        if received_obj.ndb.batch_batchmode: 
            # skip if we are currently building the room
            return 
        # commence horrible trap code
```
So we skip the hook if we are currently building the room. This can work for anything, including making sure mobs don't start attacking you while you are creating them. 

There are other strategies, such as adding an on/off switch to actiive objects and make sure it's always set to *off* upon creation.

## Editor highlighting for .ev files

- [GNU Emacs](https://www.gnu.org/software/emacs/) users might find it interesting to use emacs' *evennia mode*. This is an Emacs major mode found in `evennia/utils/evennia-mode.el`. It offers correct syntax highlighting and indentation with `<tab>` when editing `.ev` files in Emacs. See the header of that file for installation instructions.
- [VIM](https://www.vim.org/) users can use amfl's [vim-evennia](https://github.com/amfl/vim-evennia) mode instead, see its readme for install instructions.