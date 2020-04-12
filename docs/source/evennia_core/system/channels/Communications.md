# Communications


Apart from moving around in the game world and talking, players might need other forms of communication. This is offered by Evennia's `Comm` system. Stock evennia implements a 'MUX-like' system of channels, but there is nothing stopping you from changing things to better suit your taste. 

Comms rely on two main database objects - `Msg` and `Channel`. There is also the `TempMsg` which mimics the API of a `Msg` but has no connection to the database.

- [Channel Reference](channels)
- [Messages (and TempMsg) Reference](messages)



```python
class Documentation:
    RATING = "Unknown"
```