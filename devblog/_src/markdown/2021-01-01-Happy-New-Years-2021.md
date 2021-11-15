title: Happy New Years 2021!

--- 

[![](https://1.bp.blogspot.com/-QtfaDoIwzkA/X-8XYiPQ27I/AAAAAAAALm4/2-EHKh3IaYMNeoj6WykJvhPccJeJ1KD7QCLcBGAsYHQ/s320/1a1-sydney_new_years_eve_2008.jpeg)](https://1.bp.blogspot.com/-QtfaDoIwzkA/X-8XYiPQ27I/AAAAAAAALm4/2-EHKh3IaYMNeoj6WykJvhPccJeJ1KD7QCLcBGAsYHQ/s2048/1a1-sydney_new_years_eve_2008.jpeg)


Another year passed with Evennia, the Python MU* creation system. The past year saw a lot of bug fixing and more gradual additions and in September we released version 0.9.5. This was an intermediary version on our way to 1.0. Time to look forward to next year. 

On my development horizon for 2021 are the main new features planned for v1.0. Some of these are rather big things I've wanted to get around to for a while. They are all happening in the _develop_ branch of Evennia, which is currently _not_ recommended for general use.

-   **SessionDB:** In the current Evennia, Sessions (the representation of a single client connection) is an in-memory entity. This is changing to be a database-backed entity instead. One will be able to typeclass Sessions like other entities for easier overriding. This change also means that there will be one single point of session-id (the django-session), alleviating some reported issues where the Portal- and Server-side sessions have drifted out of sync. It will also make it a lot easier to support auto-logins, also across server reboots. Db-backed Sessions will also simplify the Portal-Session interaction a lot.  
-   **Script refactor:** The Scripts will see some refactoring, mainly because they are used more as general-storage entities compared to the timers they were originally meant to be. These days Evennia also offers a range of other timer-mechanisms (tickers, delays, Events etc), so it's less important to rely on Scripts for this functionality. The most important change will be that the timer will required to be explicitly started (instead of always starting on script-creation). It will also be possible to stop the timer without the script getting deleted (so separating the timer from the Script's life-cycle). 
-   **Channel refactor:** The Channels will also see changes; notably to make it considerably easier to override and customize them per-caller. Today the Channel typeclass has a maze of different hooks being called, but it's harder for devs wanting users to customize their channel output. So one of the changes will be new hooks on the account/object level for allowing to format the channel output per-user. There will also be a cleanup of the existing hooks to make things clearer. 
-   **New starting tutorial:** As part of the new documentation, I'm writing a new starting-tutorial. This will consolidate many of the existing beginner tutorials in a consistent sequence and if following it to the end, the reader will have created a small beginner game with everything in place. I plan to make a few new contribs to support this.
-   **Contrib restructure:** Our contrib/ folder is getting a little cluttered. I'm investigating organizing things a little differently by at least moving things into categorized folders. This will lead to people having to change their imports, but we'll see just how it goes.
-   **Documentation cleanup:** There are a lot of small changes, cleanup and restructuring needed in the docs overall - many of the existing pages are auto-translated from the old wiki and need rewriting both in style and content. The whole idea of moving to the new doc-system is to be able to update the docs alongside the code changes. So hopefully the changes to Sessions, Scripts and Channels etc will all be covered properly from the onset rather than after release (as was the case with the wiki). 
-   **Unittest coverage:** Our current test coverate is 64%, we need to expand this. I hope to get to at least 70% before v1.0 but that is less of a strict goal.
-   **Evennia PYPI package:** This will be one of the last things before the release of 1.0 - Evennia will be put onto PYPI  so you can install with **pip install evennia**. Once we do it will simplify the install instructions dramatically for those not interested in contributing to Evennia proper.

We also have some pull-requests in the making that will be interesting to have in the system, such as Volund's plugin system, making it easier to inject custom settings on the fly (good for contribs wanting to add their own database tables, for example). 

  

A lot of work to do as usual! 

  

**Thanks** for the past year, everyone - thanks to all of you that contributed to Evennia with code or by reporting issues or coming with feedback. Thanks particularly to those of you willing (and able) to chip in with some financial support for Evennia development - that's very encouraging! 

And finally, a big thanks to all of you taking part in community discussions, both you asking questions and you helping to answer them tirelessly and with good cheer - you make the Evennia community the friendly, inviting place it is!

  

May all our game development move forward and our hard drives stay healthy for another year. 

  

Cheers and a Happy new year,

Griatch
