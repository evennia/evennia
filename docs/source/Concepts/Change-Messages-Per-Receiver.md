# Sending different messages depending on viewpoint and receiver

Sending messages to everyong in a location is handled by the
[msg_contents](evennia.objects.objects.DefaultObject.msg_contents) method on
all [Objects](../Components/Objects.md). It's most commonly called on rooms.

```python
room.msg_contents("Anna walks into the room.")
```

You can also embed references in the string:

```python

room.msg_contents("{anna} walks into the room.",
                  from_obj=caller,
                  mapping={'anna': anna_object})
```

Use `exclude=object_or_list_of_object` to skip sending the message one or more targets.

The advantage of this is that `anna_object.get_display_name(looker)` will be called
for every onlooker; this allows the `{anna}` stanza to be different depending on who
sees the strings. How this is to work depends on the _stance_ of your game.

The stance indicates how your game echoes its messages to the player. Knowing how you want to
handle the stance is important for a text game. There are two main stances that are usually considered,
_Actor stance_ and _Director stance_.

| Stance     | You see    |    Others in the same location see |
| --- | --- | --- |
| Actor stance | You pick up the stone | Anna picks up the stone |
|Director stance | Anna picks up the stone | Anna picks up the stone |

It's not unheard of to mix the two stances - with commands from the game being told
in Actor stance while Director stance is used for complex emoting and roleplaying. One should
usually try to be consistent however.

## Director Stance

While not so common as Actor stance, director stance has the advantage of simplicity, particularly
in roleplaying MUDs where longer roleplaying emotes are used. It is also a pretty simple stance to
implement technically since everyone sees the same text, regardless of viewpoint.

Here's an example of a flavorful text to show the room:

    Tom picks up the gun, whistling to himself.

Everyone will see this string, both Tom and others. Here's how to send it to everyone in
the room.

```python
text = "Tom picks up the gun, whistling to himself."
room.msg_contents(text)
```

One may want to expand on it by making the name `Tom` be seen differently by different people,
but the English grammar of the sentence does not change. Not only is this pretty easy to do
technically, it's also easy to write for the player.

## Actor Stance

This means that the game addresses "you" when it does things. In actor stance, whenever you perform
an action, you should get a different message than those _observing_ you doing that action.

    Tom picks up the gun, whistling to himself.

This is what _others_ should see. The player themselves should see this:

    You pick up the gun, whistling to yourself.

Not only do you need to map "Tom" to "You" above, there are also grammatical differences -
"Tom walks" vs "You walk" and "himself" vs "yourself". This is a lot more complex to handle. For a
developer making simple "You/Tom pick/picks up the stone" messages, you could in principle hand-craft
the strings from every view point, but there's a better way.

The `msg_contents` method helps by parsing the ingoing string with a
[FuncParser functions](../Components/FuncParser.md) with some very specific `$inline-functions`. The inline funcs
basically provides you with a mini-language for building _one_ string that will change
appropriately depending on who sees it.


```python
text = "$You() $conj(pick) up the gun, whistling to $pron(yourself)."
room.msg_contents(text, from_obj=caller, mapping={"gun": gun_object})
```

These are the inline-functions available:

- `$You()/$you()` - this is a reference to 'you' in the text. It will be replaced with "You/you" for
  the one sending the text and with the return from `caller.get_display_name(looker)` for everyone else.
- `$conj(verb)` - this will conjugate the given verb depending on who sees the string (like `pick`
  to `picks`). Enter the root form of the verb.
- `$pron(pronoun[,options])` - A pronoun is a word you want to use instead of a proper noun, like
  _him_, _herself_, _its_, _me_, _I_, _their_ and so on. The `options` is a space- or comma-separated
  set of options to help the system map your pronoun from 1st/2nd person to 3rd person and vice versa.
  See next section.

### More on $pron()

The `$pron()` inline func maps between 1st/2nd person (I/you) to 3rd person (he/she etc). In short,
it translates between this table ...

| |  Subject Pronoun | Object Pronoun | Possessive Adjective | Possessive Pronoun | Reflexive Pronoun |
| --- | --- | --- | --- | --- | --- |
|    **1st person**          |   I    |    me   |    my    |   mine    |  myself      |
|    **1st person plural**   |   we   |    us   |    our   |    ours   |   ourselves  |
|    **2nd person**          |   you  |    you  |    your  |    yours  |   yourself   |
|    **2nd person plural**   |   you  |    you  |    your  |    yours  |   yourselves  |

... to this table (in both directions):

| | Subject Pronoun | Object Pronoun | Possessive Adjective | Possessive Pronoun | Reflexive Pronoun |
| --- | --- | --- | --- | --- | --- |
|    **3rd person male**     |   he   |    him  |    his   |    his    |   himself  |
|    **3rd person female**   |   she  |    her  |    her   |    hers   |   herself  |
|    **3rd person neutral**  |   it   |    it   |    its   |   theirs*  |   itself   |
|    **3rd person plural**   |   they |   them  |    their |    theirs |   themselves |

> *) The neutral 3rd person possessive pronoun is not actually used in English. We set it to "theirs"
> just to have something to show should someone accidentally ask for a neutral possessive pronoun.

Some mappings are easy. For example, if you write `$pron(yourselves)` then the 3rd-person
form is always `themselves`. But because English grammar is the way it is, not all mappings
are 1:1. For example, if you write
`$pron(you)`, Evennia will not know which 3rd-persion equivalent this should map to - you need to
provide more info to help out. This can either be provided as a second space-separated option
to `$pron` or the system will try to figure it out on its own.

- `pronoun_type` - this is one of the columns in the table and can be set as a `$pron` option.

   - `subject pronoun` (aliases `subject` or `sp`)
   - `object pronoun` (aliases `object` or `op`)
   - `possessive adjective` (aliases `adjective` or `pa`)
   - `possessive pronoun` (aliases `pronoun` or `pp`).

  (There is no need to specify reflexive pronouns since they
  are all uniquely mapped 1:1). Speciying the pronoun-type is mainly needed when using `you`,
  since the same 'you' is used to represent all sorts of things in English grammar.
  If not specified and the mapping is not clear, a 'subject pronoun' (he/she/it/they) is assumed.
- `gender` - set in `$pron` option as

   - `male`, or `m`
   - `female'` or `f`
   - `neutral`, or `n`
   - `plural`, or `p` (yes plural is considered a 'gender' for this purpose).

  If not set as an option the system will
  look for a callable or property `.gender` on the current `from_obj`. A callable will be called
  with no arguments and is expected to return a string 'male/female/neutral/plural'. If none
  is found, a neutral gender is assumed.
- `viewpoint`- set in `$pron` option as

   - `1st person` (aliases `1st` or `1`)
   - `2nd person` (aliases `2nd` or `2`)

   This is only needed if you want to have 1st person perspective - if
   not, 2nd person is assumed wherever the viewpoint is unclear.

`$pron()` examples:

| Input            |   you see  |  others see |  note |
| --- | --- | ---| --- |
| `$pron(I, male)`    |         I           |     he       |   |
| `$pron(I, f)`    |         I           |     she       |   |
| `$pron(my)` | my | its | figures out it's an possessive adjective, assumes neutral |
| `$pron(you)`   |         you         |  it     | assumes neutral subject pronoun |
| `$pron(you, f)`   |        you         |     she  | female specified, assumes subject pronoun |
| `$pron(you,op f)`   |      you         |     her | |
| `$pron(you,op p)`   |      you         |     them | |
| `$pron(you, f op)` | you | her | specified female and objective pronoun|
| `$pron(yourself)`  |       yourself    |     itself | |
| `$pron(its)`        |      your        |     its  | |
| `$Pron(its)`        |      Your        |     Its | Using $Pron always capitalizes |
| `$pron(her)`        |      you        |     her  | 3rd person -> 2nd person |
| `$pron(her, 1)`        |   I        |       her  | 3rd person -> 1st person |
| `$pron(its, 1st)`      |  my        |       its  | 3rd person -> 1st person  |


Note the three last examples - instead of specifying the 2nd person form you
can also specify the 3rd-person and do a 'reverse' lookup - you will still see the proper 1st/2nd text.
So writing `$pron(her)` instead of `$pron(you, op f)` gives the same result.

The [$pron inlinefunc api is found here](evennia.utils.funcparser.funcparser_callable_pronoun)

# Referencing other objects

There is one more inlinefunc understood by `msg_contents`. This can be used natively to spruce up
your strings (for both director- and actor stance):

- `$Obj(name)/$obj(name)` references another entity, which must be supplied
  in the `mapping` keyword argument to `msg_contents`. The object's `.get_display_name(looker)` will be
  called and inserted instead. This is essentially the same as using the `{anna}` marker we used
  in the first example at the top of this page, but using `$Obj/$obj` allows you to easily
  control capitalization.

This is used like so:

```python
# director stance
text = "Tom picks up the $obj(gun), whistling to himself"

# actor stance
text = "$You() $conj(pick) up the $obj(gun), whistling to $pron(yourself)"

room.msg_contents(text, from_obj=caller, mapping={"gun": gun_object})
```
Depending on your game, Tom may now see himself picking up `A rusty old gun`, whereas an onlooker
with a high gun smith skill may instead see him picking up `A rare-make Smith & Wesson model 686
in poor condition" ...`

# Recog systems and roleplaying

The `$funcparser` inline functions are very powerful for the game developer, but they may
be a bit too much to write for the regular player.

The [rpsystem contrib](evennia.contrib.rpg.rpsystem) implements a full dynamic emote/pose and recognition
system with short-descriptions and disguises. It uses director stance with a custom markup
language, like `/me` `/gun` and `/tall man` to refer to players and objects in the location. It can be
worth checking out for inspiration.
