# Batch processor examples

Contibution by Griatch, 2012

Simple examples for the batch-processor. The batch processor is used for generating 
in-game content from one or more static files. Files can be stored with version 
control and then 'applied' to the game to create content.

There are two batch processor types:

- Batch-cmd processor: A list of `#`-separated Evennia commands being executed
  in sequence, such as `create`, `dig`, `north` etc. When running a script
  of this type (filename ending with `.ev`), the caller of the script will be
  the one performing the script's actions.
- Batch-code processor: A full Python script (filename ending with `.py`  that
  executes Evennia api calls to build, such as `evennia.create_object` or
  `evennia.search_object` etc. It can be divided up into comment-separated
  chunks so one can execute only parts of the script at a time (in this way it's
  a little different than a normal Python file).

## Usage

To test the two example batch files, you need `Developer` or `superuser`
permissions, be logged into the game and run of

    > batchcommand/interactive tutorials.batchprocessor.example_batch_cmds
    > batchcode/interactive tutorials.batchprocessor.example_batch_code

The `/interactive` drops you in interactive mode so you can follow along what
the scripts do. Skip it to build it all at once.

Both commands produce the same results - they create a red-button object,
a table and a chair. If you run either with the `/debug` switch, the objects will
be deleted afterwards (for quick tests of syntax that you don't want to spam new
objects, for example).


----

<small>This document page is generated from `evennia/contrib/tutorials/batchprocessor/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
