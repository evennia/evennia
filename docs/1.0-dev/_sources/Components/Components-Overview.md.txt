# Core Components

These are the 'building blocks' out of which Evennia is built. This documentation is complementary to, and often goes deeper
than, the doc-strings of each component in the [API](../Evennia-API).

## Database entites 

- [Typeclasses](./Typeclasses)
  - [Sessions](./Sessions)
  - [Acccounts](./Accounts)
    - [Guests](../Concepts/Guest-Logins)
  - [Objects](./Objects)
  - [Scripts](./Scripts)
  - [Channels and Messages](./Communications)
- [Attributes](./Attributes)
- [Nicks](./Nicks)
- [Tags](./Tags)
- [Spawner and prototypes](./Prototypes)
- [Help entries](./Help-System)

## Commands 

- [Command system](./Command-System)
    - [Commands](./Commands)
    - [Command-Sets](./Command-Sets)
    - [The Connection Screen](./Connection-Screen)
    - [Available default Commands](api:evennia.commands.default#modules)
- [Batch-Processors](./Batch-Processors)
  - [Batch-Code-Processor](./Batch-Code-Processor)
  - [Batch-Command-Processor](./Batch-Command-Processor)

## Utils and tools

- [Misc Utils](./Coding-Utils)
- [EvEditor](./EvEditor)
- [EvMenu](./EvMenu)
- [EvMore](./EvMore)
- [MonitorHandler](./MonitorHandler)
- [TickerHandler](./TickerHandler)
- [Lock system](./Locks)
- [FuncParser](./FuncParser)

## Server and network

- [Portal](./Portal-And-Server)
  - [Inputfuncs](./Inputfuncs)
  - [Outputfuncs](./Outputfuncs)
  - [Protocols](../Concepts/Custom-Protocols)
- [Server](./Server)
  - [Server conf object](./Server-Conf)
- [Webserver](./Webserver)
  - [Webclient](./Webclient)
  - [Bootstrap](./Bootstrap-Components-and-Utilities)
- [Signals](./Signals)
