# Continuous Integration (CI)

[Continuous Integration (CI)](https://en.wikipedia.org/wiki/Continuous_integration) is a development practice that requires developers to integrate code into a shared repository. Each check-in is then verified by an automated build, allowing teams to detect problems early. This  can be set up to safely deploy data to a production server only after tests have passed, for example. 

For Evennia, continuous integration allows an automated build process to:

* Pull down a latest build from Source Control.
* Run migrations on the backing SQL database.
* Automate additional unique tasks for that project.
* Run unit tests.
* Publish those files to the server directory
* Reload the game.

## Continuous-Integration guides

Evennia itself is making heavy use of [github actions](https://github.com/features/actions). This is integrated with Github and is probably the one to go for most people, especially if your code is on Github already. You can see and analyze how Evennia's actions are running [here](https://github.com/evennia/evennia/actions).

There are however a lot of tools and services providing CI functionality.   [Here is a blog overview](https://www.atlassian.com/continuous-delivery/continuous-integration/tools)  (external link).