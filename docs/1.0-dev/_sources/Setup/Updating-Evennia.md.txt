# Updating Evennia

When Evennia is updated to a new version you will usually see it announced in the [Discussion forum](github:discussions) and in the [dev blog](https://www.evennia.com/devblog/index.html). You can also see the changes on [github](github:) or through one of our other [linked pages](../Links.md).

## If you installed with `pip`

If you followed the [normal install instructions](./Installation.md), here's what you do to upgrade:

1. Read the [changelog](../Coding/Changelog.md) to see what changed and if it means you need to make any changes to your game code.
2. If you use a [virtualenv](#Installation-Git#virtualenv), make sure it's active. 
3. `cd` to your game dir (e.g. `mygame`)
4. `evennia stop`
5. `pip install --upgrade evennia`
6. `cd` tor your game dir 
7. `evennia migrate`  (_ignore_ any warnings about running `makemigrations`, it should _not_ be done)
8. `evennia start`

If the upstream changes are large, you may also need to go into your gamedoor


##  If you installed with `git`

This applies if you followed the [git-install instructions](./Installation-Git.md). Before Evennia 1.0, this was the only way to install Evennia. 

At any time, development is either happening in the `master` branch (latest stable) or `develop` (experimental). Which one is active and 'latest' at a given time depends - after a release,  `master` will see most updates, close to a new release, `develop` will usually be the fastest changing.

1. Read the [changelog](../Coding/Changelog.md) to see what changed and if it means you need to make any changes to your game code.
2. If you use a [virtualenv](#Installation-Git#virtualenv), make sure it's active. 
3. `cd` to your game dir  (e.g. `mygame`)
4. `evennia stop`
5. `cd` to the `evennia` repo folder you cloned during the git installation process.
6. `git pull`
7. `pip install --upgrade -e .`  (remember the `.` at the end!)
9. `cd` back to your game dir
10. `evennia migrate` (_ignore_ any warnings about running `makemigrations` , it should _not_ be done)
11. `evennia start`

## If you installed with `docker`

If you followed the [docker installation instructions] you need to pull the latest docker image for the branch you want: 

- `docker pull evennia/evennia`  (master branch)
- `docker pull evennia/evennia:develop`  (experimental `develop` branch)

Then restart your containers.

## Resetting your database

Should you ever want to start over completely from scratch, there is no need to re-download Evennia. You just need to clear your database. 

First: 

1.  `cd` to your game dir (e.g. `mygame`)
2.  `evennia stop` 

### SQLite3 (default)

```{sidebar} Hint
Make a copy of the `evennia.db3` file once you created your superuser. When you want to reset (and as long as you haven't had to run any new migrations), you can just stop evennia and copy that file back over `evennia.db3`. That way you don't have to run the same migrations and create the superuser every time! 
```

3. delete the file `mygame/server/evennia.db3` 
4. `evennia migrate`
5. `evennia start`

### PostgreSQL 

3. `evennia dbshell`   (opens the psql client interface)
    ```
    psql> DROP DATABASE evennia;
    psql> exit
    ```
 4. You should now follow the [PostgreSQL install instructions](./Choosing-a-Database.md#postgresql) to create a new evennia database.
 5. `evennia migrate`
 6. `evennia start`

### MySQL/MariaDB 

3. `evennia dbshell` (opens the mysql client interface)
   ```
   mysql> DROP DATABASE evennia;
   mysql> exit
   ```
4. You should now follow the [MySQL install instructions](./Choosing-a-Database.md#mysql-mariadb) to create a new evennia database.
5. `evennia migrate`
6. `evennia start`

### What are database migrations?

If and when an Evennia update modifies the database *schema* (that is, the under-the-hood details as to how data is stored in the database), you must update your existing database correspondingly to match the change. If you don't, the updated Evennia will complain that it cannot read the database properly. Whereas schema changes should become more and more rare as Evennia matures, it may still happen from time to time.

One way one could handle this is to apply the changes manually to your database using the database's command line. This often means adding/removing new tables or fields as well as possibly convert existing data to match what the new Evennia version expects. It should be quite obvious that this quickly becomes cumbersome and error-prone.  If your database doesn't contain anything critical yet it's probably easiest to simply reset it and start over rather than to bother converting. 

Enter *migrations*. Migrations keeps track of changes in the database schema and applies them automatically for you. Basically, whenever the schema changes we distribute small files called "migrations" with the source. Those tell the system exactly how to implement the change so you don't have to do so manually. When a migration has been added we will tell you so on Evennia's mailing lists and in commit messages - you then just run `evennia migrate` to be up-to-date again.
