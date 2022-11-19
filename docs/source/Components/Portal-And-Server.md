# Portal And Server


Evennia consists of two processes, known as *Portal* and *Server*.  They can be controlled from
inside the game or from the command line as described [here](../Setup/Start-Stop-Reload.md).

If you are new to the concept, the main purpose of separating the two is to have accounts connect to the Portal but keep the MUD running on the Server. This way one can restart/reload the game (the Server part) without Accounts getting disconnected.

![portal and server layout](https://474a3b9f-a-62cb3a1a-s-  sites.googlegroups.com/site/evenniaserver/file-cabinet/evennia_server_portal.png)

The Server and Portal are glued together via an AMP (Asynchronous Messaging Protocol) connection. This allows the two programs to communicate seamlessly.