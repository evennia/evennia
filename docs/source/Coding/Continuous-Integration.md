# Continuous Integration (CI)

[Continuous Integration (CI)](https://www.thoughtworks.com/continuous-integration) is a development practice that requires developers to integrate code into a shared repository. Each check-in is then verified by an automated build, allowing teams to detect problems early. This  can be set up to safely deploy data to a production server only after tests have passed, for example. 

For Evennia, continuous integration allows an automated build process to:

* Pull down a latest build from Source Control.
* Run migrations on the backing SQL database.
* Automate additional unique tasks for that project.
* Run unit tests.
* Publish those files to the server directory
* Reload the game.

## Continuous-Integration guides

There are a lot of tools and services providing CI functionality. Here are a few that people have used  with Evennia: 

```{toctree} 
:maxdepth: 1

Continuous-Integration-Travis.md
Continuous-Integration-TeamCity.md

```

- Evennia is itself making heavy use of [github actions]()

[This is an overview of other tools](https://www.atlassian.com/continuous-delivery/continuous-integration/tools)  (external link).