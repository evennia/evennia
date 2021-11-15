title: Renaming Django's Auth User and App 

---

[![](https://4.bp.blogspot.com/-DRHk1mmLB0Y/WaCUd8tmYbI/AAAAAAAAHaU/QXkryhYVJBIVWPykT08nSokCHfFc6-2LACLcBGAs/s400/birds-1976981_640.jpg)](https://4.bp.blogspot.com/-DRHk1mmLB0Y/WaCUd8tmYbI/AAAAAAAAHaU/QXkryhYVJBIVWPykT08nSokCHfFc6-2LACLcBGAs/s1600/birds-1976981_640.jpg)

Now that [Evennia's](http://www.evennia.com/) devel branch (what will become Evennia 0.7) is slowly approaching completion, I thought I'd try to document an aspect of it that probably took me the longest to figure out. One change in Evennia 0.7 is that the Django model named "Player" changes name to "Account". Over time it has become clear that the old name didn't properly reflected the intention of the model. Sounds like a simple change, right? Well, it was not.  
  

### Briefly on migrations

  
First some background. A Django _migration_ is a small Python file sitting in migrations/ sub folders throughout Evennia. A migration describes how our database schema changes over time, so as we change or update fields or add new features we add new migrations to describe how to go from the old to the new state. You apply them with the `evennia migrate` command we sometimes ask you to run. If we did not supply migrations, anyone with an existing Evennia database would have to either start from scratch or manually go in and tweak their database to match every upstream change we did.  
  
Each migration file has a sequential number, like migration_name.0002.py etc. Migrations will run in order but each migration can also "depend" on another. This means for example that a migration in the player/ folder (application) knows that it need to wait for the changes done by a migration in the typeclasses/ folder/app before it can run.  Finally, Django stores a table in the database to know which migrations were already run so to not apply them more than once.  
  
_For reference, Evennia is wrapping the django manage commands, so where I refer to evennia migrate below you would use manage.py migrate in most Django applications._  
  

### Our problem

  
So I wanted to migrate the database change "Rename the Player model to Account". We had to do this under a series of additional constraints however:  
  

1.  The Player is the Django Auth user, storing the password. Such a user Django expects to exist from the beginning of the migration history.
2.  The Player model sits in a application (folder) named "players". This folder should also be renamed to "accounts", meaning any in-migration references to this from other apps would become invalid.
3.  Our migration must both work for old _and_ new users. That is, we cannot expect people to all have existing databases to migrate. Some will need to create the database from scratch and must be able to do so without needing to do any changes to the migration structure.
4.  We have a lot of references to "player" throughout the code, all of which must be renamed.
5.  The migration, including renames, should be possible to do by new users with newbie-level Python and database skills.

### Some false starts

There is no lack of tutorials and help online for solving the problem of renaming a model. I think I tested most of them. But none I found actually ended up addressing these restraints. Especially point **2** in combination with point **3** above is a _killer_.  
  

-   One of my first tries wiped the migrations table completely, renamed the folder and just assumed Player never existed. This sounds good on paper and works perfectly for fresh databases. But existing databases will still contain the old Player-related models. With the old migrations gone, this is now all wrong and there is no information on how to migrate it.
-   I tried initiating fresh migrations with a player model state so you can move an existing database over to it. But then fresh databases doesn't work instead, since the player folder is gone. Also, you run into trouble with the auth system.
-   I next tried to keep the old migrations (those we know work both for old and new databases) but to migrate it in-place. I did many different attempts at this, but every time one of the restraints above would get in the way.
-   Eventually I wrote raw SQL code in the migrations to modify the database tables retroactively. That is, I basically manually removed all traces of Player in the database where it was, copying things table by table. This was very work-intensive but overall decently successful. With proper error-checking I could get most of the migration to work from old databases as well as for new databases. The trouble was the migrations themselves. No matter how I tried, I couldn't get the migration history to accept what I had done - the dependencies now longer made sense on the database level (since I had manually edited things) and adding new migrations in the future would have been tricky.

  
In the end I concluded that I had to abandon the notion that users be able to just do a single migrate command. Some more work would be needed on the user's part.  
  

### The solution

  
In the end I needed to combine the power of migrations with the power of Git. Using Git resolved the Gordian knot about the player folder. Basically the process goes like this:  
  

-   First I copied of the `players` folder and renamed it and everything in it to accounts. I added this to settings.INSTALLED_APPS. I also copied the migrations from player and renamed everything in them appropriately - those migrations thus look like Account has always existed - so when you run the migration from scratch the database will be created normally. Note that this also means setting the Account as the auth user from the beginning of the migration history. This would be fine when migrating from scratch except for the fact that it would clash with the still existing Player model saying the same thing. We dodge this problem by the way we run this migration (we'll get to this later).
-   Next I added one new migration in the Account app - this is the migration that copies the data from the player to the equivalent account-named copies in the database. Since Player will not exist if you run this from scratch you have to make sure that the Player model exists at that point in the migration chain. You can't just do this with a normal import and traceback, you need to use the migration infrastructure. This kind of check works:

 
 ```python
  # ...  
  
  def forwards(apps, schema_editor):  
      try:  
          PlayerDB = apps.get_model("players", "PlayerDB")  
      except LookupError:  
          return  
  
      # copy data from player-tables to database tables here  
  
 class Migrations(migrations.Migration):  
     # ...  
     operations = [  
         migrations.RunPython(forwards, migrations.RunPython.noop)  
     ]  
```  

-   Now, a lot of my other apps/models has ForeignKey or Many2Many relations to the Player model. Aided by viewing the tables in the database I visited all of those and added a migration to each where I duplicated the player-relation with a duplicate account relation. So at this point I had set up a parallel, co-existing duplicate of the Player model, named Account.
-   I now made sure to commit my changes to git and tag this position in the version history with a clear git tag for later reference. This is an important step. We are saving the historical point in time where the player- and account-apps coexisted.5. The git position safely saved, I now went about purging player. I removed the player app and its folder.
-   Since the player folder is not there, it's migrations are not there either. So in another app (any would work) I made a migration to remove the player tables from the database. Thing is, the missing player app means other migrations also cannot reference it. It is possible I could have waited to remove the player/ folder so as to be able to do this bit in pure Python. On the other hand, that might have caused issues since you would be trying to migrate with two Auth users - not sure. As it were, I ended up purging the now useless player-tables with raw SQL:

```python
 from django.db import connection  
  
    # ...  
  
    def _table_exists(db_cursor, tablename):  
        "Returns bool if table exists or not"  
        sql_check_exists = "SELECT * from %s;" % tablename  
    ### [Renaming Django's Auth User and App](https://evennia.blogspot.com/2017/08/renaming-djangos-auth-user-and-app.html)
```

[![](https://4.bp.blogspot.com/-DRHk1mmLB0Y/WaCUd8tmYbI/AAAAAAAAHaU/QXkryhYVJBIVWPykT08nSokCHfFc6-2LACLcBGAs/s400/birds-1976981_640.jpg)](https://4.bp.blogspot.com/-DRHk1mmLB0Y/WaCUd8tmYbI/AAAAAAAAHaU/QXkryhYVJBIVWPykT08nSokCHfFc6-2LACLcBGAs/s1600/birds-1976981_640.jpg)

And with this, the migration's design was complete. Below is how to actually _use_ it ...  
  

### Running the final migration

  
In brief, what our users will do after pulling the latest code is as follows:  
  

1.  If they are starting fresh, they just run **evennia migrate** as usual. All migrations referencing player will detect that there is no such app and just be skipped. They are finished, hooray!
2.  If they have an existing database, they should make a copy of my renaming-program, then check out  the tagged point in the git history I created above, a time when players and accounts coexisted in code.
3.  Since an important aspect of Evennia is that users create their own game in a "game" folder, the user can now use my renaming program to interactively rename all occurrencies of `player` into `account` (the term 'player' is so ubiquitous that they may have used in in different places they don't want to rename).
4.  Next they run migrations at that point of the git history. This duplicates player data into its renamed counterparts.
5.  Now they should check out the latest Evennia again, jumping back to a point where the players application is  gone and only accounts exists.
6.  Note that our migration history is wrong at this point. It will still contain references to migrations from the now nonexisting players app. When trying to run from scratch, those will fail. We need to force Django to forget that. So the user must here go into their database of choice and run the single SQL statement **DELETE FROM django_migations;** . This clears the migration history.  This is a step I wanted to avoid (since it requires users to use SQL) but in the end I concluded it must be done (and is hopefully a simple enough instruction).
7.  Next, we trick the database to again think that we have run all the migrations from the beginning (this time without any mention of players). This is done with the **--fake** switch: **evennia migrate --fake** . This fake-applies all migrations and stores in the database that they have run.
8.  However, the last few migrations are the ones I added just above. Those actually remove the player-related tables from the database. We really _do_ want to run those. So we fake-_fake_ undo those with **evennia migrate --fake typeclasses 0007**, which is the application and migration number I used to wipe players. This causes django to forget those migrations so we can run them again.
9.  Finally we run evennia migrate. This runs the previously "forgotten" migrations and purges the last vestigest of players from the database. Done!

### Conclusions

  
And that's it. It's a bit more involved for the end user than I would have liked, and took me much longer than expected to figure out. But it's possible to reproduce and you only need to do it once - and only if you have a database to convert. Whereas this is necessarily specified for Evennia, I hope this might give a hint for other django users aiming to do something like this!