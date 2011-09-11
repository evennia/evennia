Workshop: Default-game whitepage

Introduction
============

This is an initiative to create a "base" game system to be shipped with
Evennia in a "contrib" folder. The game is an independent
re-implementation of the basic stuff of the
`SMAUG <http://www.smaug.org>`_ system. No code from the original will
be used, and no licensed content will be included in the release. For
easy testing of content, rcaskey's SMAUG importer will be used.

TODO, first prototype
=====================

The first stage serves to establish a prototype implementation -
something that shows the parts hanging together, but with only a subset
of the functionality.

Create custom `TypeClasses <Objects.html>`_ supporting the SMAUG system:

-  Object->!SmaugObject->!SmaugBeing->!SmaugCharacter,Character
-  Object->!SmaugObject->!SmaugBeing->!SmaugMob-> ...
-  Object->!SmaugObject->!SmaugThing-> ...

Create limited subclasses or attributes on objects

-  Limited classes/races (1-2?)
-  Skills (<lvl 5?) - not too many!

Behind-the-scenes SMAUG engine

-  Contest resolution
-  Mobs moving around, "AI"
-  Base combat system

Import of small data set, testing.

SMAUG specifics
===============

Code Availability By Lvl
~~~~~~~~~~~~~~~~~~~~~~~~

+-------+---------------------------+
| Lvl   | Code Bit                  |
+-------+---------------------------+
| 0     | spell*disenchant*weapon   |
+-------+---------------------------+
| 1     | spell*cause*light         |
+-------+---------------------------+
| 1     | dohide                    |
+-------+---------------------------+
| 1     | spellventriloquate        |
+-------+---------------------------+
| 1     | docook                    |
+-------+---------------------------+
| 1     | doclimb                   |
+-------+---------------------------+
| 1     | spellnull                 |
+-------+---------------------------+
| 1     | dopick                    |
+-------+---------------------------+
| 1     | dosteal                   |
+-------+---------------------------+
| 1     | dobackstab                |
+-------+---------------------------+
| 1     | spellsmaug                |
+-------+---------------------------+
| 1     | dokick                    |
+-------+---------------------------+
| 2     | dodig                     |
+-------+---------------------------+
| 2     | domount                   |
+-------+---------------------------+
| 2     | spell*faerie*fire         |
+-------+---------------------------+
| 2     | spell*create*food         |
+-------+---------------------------+
| 2     | spell*create*water        |
+-------+---------------------------+
| 2     | spellweaken               |
+-------+---------------------------+
| 2     | spellblackhand            |
+-------+---------------------------+
| 3     | doscan                    |
+-------+---------------------------+
| 3     | dosearch                  |
+-------+---------------------------+
| 3     | dofeed                    |
+-------+---------------------------+
| 3     | spell*chill*touch         |
+-------+---------------------------+
| 4     | dorescue                  |
+-------+---------------------------+
| 4     | spellcureblindness        |
+-------+---------------------------+
| 4     | spellinvis                |
+-------+---------------------------+
| 4     | doaid                     |
+-------+---------------------------+
| 4     | spellgalvanicwhip         |
+-------+---------------------------+
| 5     | spellblindness            |
+-------+---------------------------+
| 5     | spell*cause*serious       |
+-------+---------------------------+
| 5     | spell*detect*poison       |
+-------+---------------------------+
| 5     | spell*burning*hands       |
+-------+---------------------------+
| 5     | spell*know*alignment      |
+-------+---------------------------+
| 6     | spell*locate*object       |
+-------+---------------------------+
| 6     | dotrack                   |
+-------+---------------------------+
| 6     | spellremoveinvis          |
+-------+---------------------------+
| 6     | spellpoison               |
+-------+---------------------------+
| 7     | spellearthquake           |
+-------+---------------------------+
| 7     | spellshockinggrasp        |
+-------+---------------------------+
| 8     | spellteleport             |
+-------+---------------------------+
| 8     | dobashdoor                |
+-------+---------------------------+
| 8     | spellsummon               |
+-------+---------------------------+
| 8     | spell*cure*poison         |
+-------+---------------------------+
| 8     | spelldisruption           |
+-------+---------------------------+
| 9     | spellbethsaideantouch     |
+-------+---------------------------+
| 9     | spellcausecritical        |
+-------+---------------------------+
| 9     | spelllightningbolt        |
+-------+---------------------------+
| 10    | spellidentify             |
+-------+---------------------------+
| 10    | spell*faerie*fog          |
+-------+---------------------------+
| 10    | spell*control*weather     |
+-------+---------------------------+
| 10    | spell*dispel*evil         |
+-------+---------------------------+
| 10    | dodisarm                  |
+-------+---------------------------+
| 11    | spellcolourspray          |
+-------+---------------------------+
| 11    | dobite                    |
+-------+---------------------------+
| 11    | spell*dispel*magic        |
+-------+---------------------------+
| 11    | dobloodlet                |
+-------+---------------------------+
| 12    | spellsleep                |
+-------+---------------------------+
| 12    | spellcurse                |
+-------+---------------------------+
| 12    | spellcalllightning        |
+-------+---------------------------+
| 12    | spellremovecurse          |
+-------+---------------------------+
| 12    | spellenchantweapon        |
+-------+---------------------------+
| 12    | spellword*of*recall       |
+-------+---------------------------+
| 13    | spellharm                 |
+-------+---------------------------+
| 13    | spellfireball             |
+-------+---------------------------+
| 13    | spellexpurgation          |
+-------+---------------------------+
| 13    | spellflamestrike          |
+-------+---------------------------+
| 13    | spell*midas*touch         |
+-------+---------------------------+
| 13    | spell*energy*drain        |
+-------+---------------------------+
| 14    | spell*spectral*furor      |
+-------+---------------------------+
| 14    | spell*charm*person        |
+-------+---------------------------+
| 15    | spell*remove*trap         |
+-------+---------------------------+
| 16    | spellfarsight             |
+-------+---------------------------+
| 16    | dodetrap                  |
+-------+---------------------------+
| 17    | spelltransport            |
+-------+---------------------------+
| 17    | spelldream                |
+-------+---------------------------+
| 18    | spell*sulfurous*spray     |
+-------+---------------------------+
| 18    | spell*pass*door           |
+-------+---------------------------+
| 19    | spell*sonic*resonance     |
+-------+---------------------------+
| 20    | dogouge                   |
+-------+---------------------------+
| 20    | spellacidblast            |
+-------+---------------------------+
| 21    | spellportal               |
+-------+---------------------------+
| 23    | spell*black*fist          |
+-------+---------------------------+
| 25    | dopunch                   |
+-------+---------------------------+
| 25    | docircle                  |
+-------+---------------------------+
| 25    | dobrew                    |
+-------+---------------------------+
| 27    | spellmagneticthrust       |
+-------+---------------------------+
| 27    | dopoisonweapon            |
+-------+---------------------------+
| 28    | spellscorchingsurge       |
+-------+---------------------------+
| 30    | doscribe                  |
+-------+---------------------------+
| 30    | dobash                    |
+-------+---------------------------+
| 30    | spellastralwalk           |
+-------+---------------------------+
| 31    | domistwalk                |
+-------+---------------------------+
| 32    | spell*ethereal*fist       |
+-------+---------------------------+
| 32    | spellknock                |
+-------+---------------------------+
| 33    | spellrecharge             |
+-------+---------------------------+
| 34    | spell*caustic*fount       |
+-------+---------------------------+
| 35    | spell*sacral*divinity     |
+-------+---------------------------+
| 35    | spell*plant*pass          |
+-------+---------------------------+
| 37    | spell*hand*ofchaos        |
+-------+---------------------------+
| 37    | spellacetumprimus         |
+-------+---------------------------+
| 39    | spellsolarflight          |
+-------+---------------------------+
| 41    | dobroach                  |
+-------+---------------------------+
| 41    | spell*frost*breath        |
+-------+---------------------------+
| 42    | spell*helical*flow        |
+-------+---------------------------+
| 42    | spell*animate*dead        |
+-------+---------------------------+
| 42    | spell*lightning*breath    |
+-------+---------------------------+
| 43    | spell*acid*breath         |
+-------+---------------------------+
| 44    | spell*fire*breath         |
+-------+---------------------------+
| 45    | spell*gas*breath          |
+-------+---------------------------+
| 46    | spell*spiral*blast        |
+-------+---------------------------+
| 46    | spell*black*lightning     |
+-------+---------------------------+
| 48    | dostun                    |
+-------+---------------------------+
| 48    | spellquantumspike         |
+-------+---------------------------+
| 50    | dohitall                  |
+-------+---------------------------+
| 51    | spellpossess              |
+-------+---------------------------+
| 51    | spellchangesex            |
+-------+---------------------------+
| 51    | spellgate                 |
+-------+---------------------------+
| 51    | doslice                   |
+-------+---------------------------+
| 51    | spellpolymorph            |
+-------+---------------------------+
| 51    | do\_berserk               |
+-------+---------------------------+

+ the affects they apply float, sneak, hide, detect invisibility, detect
magic, detect evil, invisibility
