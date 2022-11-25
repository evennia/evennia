# Portal And Server


Evennia consists of two processes, known as *Portal* and *Server*.  They can be controlled from
inside the game or from the command line as described [in the Running-Evennia doc](../Setup/Running-Evennia.md).

In short, the Portal knows everything about internet protocols (telnet, websockets etc), but knows very little about the game. 

In contrast, the Server knows everything about the game. It knows that a player has connected but now _how_ they connected. 

The effect of this is that you can fully `reload` the Server and have players still connected to the game. One the server comes back up, it will re-connect to the Portal and re-sync all players as if nothing happened. 

```
Internet│  ┌──────────┐ ┌─┐           ┌─┐ ┌─────────┐
        │  │Portal    │ │S│   ┌───┐   │S│ │Server   │
    P   │  │          ├─┤e├───┤AMP├───┤e├─┤         │
    l ──┼──┤ Telnet   │ │s│   │   │   │s│ │         │
    a   │  │ Webclient├─┤s├───┤   ├───┤s├─┤ Game    │
    y ──┼──┤ SSH      │ │i│   │   │   │i│ │ Database│
    e   │  │ ...      ├─┤o├───┤   ├───┤o├─┤         │
    r ──┼──┤          │ │n│   │   │   │n│ │         │
    s   │  │          │ │s│   └───┘   │s│ │         │
        │  └──────────┘ └─┘           └─┘ └─────────┘
        │Evennia 
```

The Server and Portal are glued together via an AMP (Asynchronous Messaging Protocol) connection. This allows the two programs to communicate seamlessly on the same machine.