# Zones

Evennia recommends using [Tags](../Components/Tags.md) to create zones and other groupings. 

Say you create a room named *Meadow* in your nice big forest MUD.  That's all nice and dandy, but
what if you, in the other end of that forest want another *Meadow*? As a game creator, this can
cause all sorts of confusion. For example, teleporting to *Meadow* will now give you a warning that
there are two *Meadow* s and you have to select which one. It's no problem to do that, you just
choose for example to go to `2-meadow`, but unless you examine them you couldn't be sure which of
the two sat in the magical part of the forest and which didn't.

Another issue is if you want to group rooms in geographic regions.  Let's say the "normal" part of
the forest should have separate weather patterns from the magical part. Or maybe a magical
disturbance echoes through all magical-forest rooms. It would then be convenient to be able to
simply find all rooms that are "magical" so you could send messages to them.

## Zones in Evennia

*Zones* try to separate rooms by global location. In our example we would separate the forest into two parts - the magical and the non-magical part. Each have a *Meadow* and rooms belonging to each part should be easy to retrieve.

Many MUD codebases hardcode zones as part of the engine and database.  Evennia does no such
distinction.

All objects in Evennia can hold any number of [Tags](../Components/Tags.md). Tags are short labels that you attach to objects. They make it very easy to retrieve groups of objects. An object can have any number of different tags. So let's attach the relevant tag to our forest: 

```python
     forestobj.tags.add("magicalforest", category="zone")
```

You could add this manually, or automatically during creation somehow (you'd need to modify your
`dig` command for this, most likely). You can also use the default `tag` command during building:

     tag forestobj = magicalforest : zone

Henceforth you can then easily retrieve only objects with a given tag:

```python
     import evennia
     rooms = evennia.search_tag("magicalforest", category="zone")
```

## Using typeclasses and inheritance for zoning

The tagging or aliasing systems above don't instill any sort of functional difference between a magical forest room and a normal one - they are just arbitrary ways to mark objects for quick retrieval later. Any functional differences must be expressed using [Typeclasses](../Components/Typeclasses.md). 

Of course, an alternative way to implement zones themselves is to have all rooms/objects in a zone inherit from a given typeclass parent - and then limit your searches to objects inheriting from that given parent. The effect would be similar but you'd need to expand the search functionality to
properly search the inheritance tree.