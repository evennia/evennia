```python
class Documentation:
    RATING = "Unknown"
```

# Communications

Apart from moving around in the game world and talking, players might need other forms of communication. This is offered by Evennia's `Comm` system. Stock evennia implements a 'MUX-like' system of channels, but there is nothing stopping you from changing things to better suit your taste. 

Comms rely on two main database objects - `Msg` and `Channel`. There is also the `TempMsg` which mimics the API of a `Msg` but has no connection to the database.

- [Channel Reference](channels)
- [Messages (and TempMsg) Reference](messages)

## Third-party communications

Evennia also connects to the following channels:

- [IRC](IRC) - IRC <-> Evennia bridge
- [Grapevine](Grapevine) - MUD <-> MUD bridge (both MUDs must support grapevine)
- [RSS](RSS) - Used for keeping users/admins apprised of evennia core updates or other feeds