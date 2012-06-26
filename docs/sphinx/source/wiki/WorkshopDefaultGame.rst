**Status Update**:*There does not seem to be any active development on
this by the original initiator (rcaskey). As far as I know there is no
active game code written apart from a Smaug area converter (how
complete?). If anyone is willing to continue with this particular idea,
they are welcome to do so. I will help out but I don't know anything
about Smaug myself. In the interim I will chalk this one down as being a
stalled project. /Griatch*

Introduction
============

This is(was?) an initiative to create a "base" game system to be shipped
with Evennia in a "contrib" folder. The game is an independent
re-implementation of the basic stuff of the
`SMAUG <http://www.smaug.org>`_ system. No code from the original will
be used, and no licensed content will be included in the release. For
easy testing of content, rcaskey's SMAUG importer will be used.

TODO, first prototype
=====================

The first stage serves to establish a prototype implementation -
something that shows the parts hanging together, but with only a subset
of the functionality.

#. Create custom `TypeClasses <Objects.html>`_ supporting the SMAUG
   system:

   -  Object->SmaugObject->SmaugBeing->SmaugCharacter,Character
   -  Object->SmaugObject->SmaugBeing->SmaugMob-> ...
   -  Object->SmaugObject->SmaugThing-> ...

#. Create limited subclasses or attributes on objects

   -  Limited classes/races (1-2?)
   -  Skills (<lvl 5?) - not too many!

#. Behind-the-scenes SMAUG engine

   -  Contest resolution
   -  Mobs moving around, "AI"
   -  Base combat system

#. Import of small data set, testing.

SMAUG specifics
===============

Code Availability By Lvl
~~~~~~~~~~~~~~~~~~~~~~~~

+-------+-----------------------------+
| Lvl   | Code Bit                    |
+-------+-----------------------------+
| 0     | spell\_disenchant\_weapon   |
+-------+-----------------------------+
| 1     | spell\_cause\_light         |
+-------+-----------------------------+
| 1     | do\_hide                    |
+-------+-----------------------------+
| 1     | spell\_ventriloquate        |
+-------+-----------------------------+
| 1     | do\_cook                    |
+-------+-----------------------------+
| 1     | do\_climb                   |
+-------+-----------------------------+
| 1     | spell\_null                 |
+-------+-----------------------------+
| 1     | do\_pick                    |
+-------+-----------------------------+
| 1     | do\_steal                   |
+-------+-----------------------------+
| 1     | do\_backstab                |
+-------+-----------------------------+
| 1     | spell\_smaug                |
+-------+-----------------------------+
| 1     | do\_kick                    |
+-------+-----------------------------+
| 2     | do\_dig                     |
+-------+-----------------------------+
| 2     | do\_mount                   |
+-------+-----------------------------+
| 2     | spell\_faerie\_fire         |
+-------+-----------------------------+
| 2     | spell\_create\_food         |
+-------+-----------------------------+
| 2     | spell\_create\_water        |
+-------+-----------------------------+
| 2     | spell\_weaken               |
+-------+-----------------------------+
| 2     | spell\_black\_hand          |
+-------+-----------------------------+
| 3     | do\_scan                    |
+-------+-----------------------------+
| 3     | do\_search                  |
+-------+-----------------------------+
| 3     | do\_feed                    |
+-------+-----------------------------+
| 3     | spell\_chill\_touch         |
+-------+-----------------------------+
| 4     | do\_rescue                  |
+-------+-----------------------------+
| 4     | spell\_cure\_blindness      |
+-------+-----------------------------+
| 4     | spell\_invis                |
+-------+-----------------------------+
| 4     | do\_aid                     |
+-------+-----------------------------+
| 4     | spell\_galvanic\_whip       |
+-------+-----------------------------+
| 5     | spell\_blindness            |
+-------+-----------------------------+
| 5     | spell\_cause\_serious       |
+-------+-----------------------------+
| 5     | spell\_detect\_poison       |
+-------+-----------------------------+
| 5     | spell\_burning\_hands       |
+-------+-----------------------------+
| 5     | spell\_know\_alignment      |
+-------+-----------------------------+
| 6     | spell\_locate\_object       |
+-------+-----------------------------+
| 6     | do\_track                   |
+-------+-----------------------------+
| 6     | spell\_remove\_invis        |
+-------+-----------------------------+
| 6     | spell\_poison               |
+-------+-----------------------------+
| 7     | spell\_earthquake           |
+-------+-----------------------------+
| 7     | spell\_shocking\_grasp      |
+-------+-----------------------------+
| 8     | spell\_teleport             |
+-------+-----------------------------+
| 8     | do\_bashdoor                |
+-------+-----------------------------+
| 8     | spell\_summon               |
+-------+-----------------------------+
| 8     | spell\_cure\_poison         |
+-------+-----------------------------+
| 8     | spell\_disruption           |
+-------+-----------------------------+
| 9     | spell\_bethsaidean\_touch   |
+-------+-----------------------------+
| 9     | spell\_cause\_critical      |
+-------+-----------------------------+
| 9     | spell\_lightning\_bolt      |
+-------+-----------------------------+
| 10    | spell\_identify             |
+-------+-----------------------------+
| 10    | spell\_faerie\_fog          |
+-------+-----------------------------+
| 10    | spell\_control\_weather     |
+-------+-----------------------------+
| 10    | spell\_dispel\_evil         |
+-------+-----------------------------+
| 10    | do\_disarm                  |
+-------+-----------------------------+
| 11    | spell\_colour\_spray        |
+-------+-----------------------------+
| 11    | do\_bite                    |
+-------+-----------------------------+
| 11    | spell\_dispel\_magic        |
+-------+-----------------------------+
| 11    | do\_bloodlet                |
+-------+-----------------------------+
| 12    | spell\_sleep                |
+-------+-----------------------------+
| 12    | spell\_curse                |
+-------+-----------------------------+
| 12    | spell\_call\_lightning      |
+-------+-----------------------------+
| 12    | spell\_remove\_curse        |
+-------+-----------------------------+
| 12    | spell\_enchant\_weapon      |
+-------+-----------------------------+
| 12    | spell\_word\_of\_recall     |
+-------+-----------------------------+
| 13    | spell\_harm                 |
+-------+-----------------------------+
| 13    | spell\_fireball             |
+-------+-----------------------------+
| 13    | spell\_expurgation          |
+-------+-----------------------------+
| 13    | spell\_flamestrike          |
+-------+-----------------------------+
| 13    | spell\_midas\_touch         |
+-------+-----------------------------+
| 13    | spell\_energy\_drain        |
+-------+-----------------------------+
| 14    | spell\_spectral\_furor      |
+-------+-----------------------------+
| 14    | spell\_charm\_person        |
+-------+-----------------------------+
| 15    | spell\_remove\_trap         |
+-------+-----------------------------+
| 16    | spell\_farsight             |
+-------+-----------------------------+
| 16    | do\_detrap                  |
+-------+-----------------------------+
| 17    | spell\_transport            |
+-------+-----------------------------+
| 17    | spell\_dream                |
+-------+-----------------------------+
| 18    | spell\_sulfurous\_spray     |
+-------+-----------------------------+
| 18    | spell\_pass\_door           |
+-------+-----------------------------+
| 19    | spell\_sonic\_resonance     |
+-------+-----------------------------+
| 20    | do\_gouge                   |
+-------+-----------------------------+
| 20    | spell\_acid\_blast          |
+-------+-----------------------------+
| 21    | spell\_portal               |
+-------+-----------------------------+
| 23    | spell\_black\_fist          |
+-------+-----------------------------+
| 25    | do\_punch                   |
+-------+-----------------------------+
| 25    | do\_circle                  |
+-------+-----------------------------+
| 25    | do\_brew                    |
+-------+-----------------------------+
| 27    | spell\_magnetic\_thrust     |
+-------+-----------------------------+
| 27    | do\_poison\_weapon          |
+-------+-----------------------------+
| 28    | spell\_scorching\_surge     |
+-------+-----------------------------+
| 30    | do\_scribe                  |
+-------+-----------------------------+
| 30    | do\_bash                    |
+-------+-----------------------------+
| 30    | spell\_astral\_walk         |
+-------+-----------------------------+
| 31    | do\_mistwalk                |
+-------+-----------------------------+
| 32    | spell\_ethereal\_fist       |
+-------+-----------------------------+
| 32    | spell\_knock                |
+-------+-----------------------------+
| 33    | spell\_recharge             |
+-------+-----------------------------+
| 34    | spell\_caustic\_fount       |
+-------+-----------------------------+
| 35    | spell\_sacral\_divinity     |
+-------+-----------------------------+
| 35    | spell\_plant\_pass          |
+-------+-----------------------------+
| 37    | spell\_hand\_of\_chaos      |
+-------+-----------------------------+
| 37    | spell\_acetum\_primus       |
+-------+-----------------------------+
| 39    | spell\_solar\_flight        |
+-------+-----------------------------+
| 41    | do\_broach                  |
+-------+-----------------------------+
| 41    | spell\_frost\_breath        |
+-------+-----------------------------+
| 42    | spell\_helical\_flow        |
+-------+-----------------------------+
| 42    | spell\_animate\_dead        |
+-------+-----------------------------+
| 42    | spell\_lightning\_breath    |
+-------+-----------------------------+
| 43    | spell\_acid\_breath         |
+-------+-----------------------------+
| 44    | spell\_fire\_breath         |
+-------+-----------------------------+
| 45    | spell\_gas\_breath          |
+-------+-----------------------------+
| 46    | spell\_spiral\_blast        |
+-------+-----------------------------+
| 46    | spell\_black\_lightning     |
+-------+-----------------------------+
| 48    | do\_stun                    |
+-------+-----------------------------+
| 48    | spell\_quantum\_spike       |
+-------+-----------------------------+
| 50    | do\_hitall                  |
+-------+-----------------------------+
| 51    | spell\_possess              |
+-------+-----------------------------+
| 51    | spell\_change\_sex          |
+-------+-----------------------------+
| 51    | spell\_gate                 |
+-------+-----------------------------+
| 51    | do\_slice                   |
+-------+-----------------------------+
| 51    | spell\_polymorph            |
+-------+-----------------------------+
| 51    | do\_berserk                 |
+-------+-----------------------------+

( + the affects they apply float, sneak, hide, detect invisibility,
detect magic, detect evil, invisibility)
