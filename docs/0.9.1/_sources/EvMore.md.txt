# EvMore


When sending a very long text to a user client, it might scroll beyond of the height of the client
window. The `evennia.utils.evmore.EvMore` class gives the user the in-game ability to only view one
page of text at a time. It is usually used via its access function, `evmore.msg`.

The name comes from the famous unix pager utility *more* which performs just this function.

### Using EvMore

To use the pager, just pass the long text through it:

```python
from evennia.utils import evmore

evmore.msg(receiver, long_text)
```
Where receiver is an [Object](./Objects) or a [Account](./Accounts). If the text is longer than the
client's screen height (as determined by the NAWS handshake or by `settings.CLIENT_DEFAULT_HEIGHT`)
the pager will show up, something like this:

>[...]
aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur
sint occaecat cupidatat non proident, sunt in culpa qui
officia deserunt mollit anim id est laborum.

>(**more** [1/6] retur**n**|**b**ack|**t**op|**e**nd|**a**bort)


where the user will be able to hit the return key to move to the next page, or use the suggested
commands to jump to previous pages, to the top or bottom of the document as well as abort the
paging.

The pager takes several more keyword arguments for controlling the message output. See the
[evmore-API](github:evennia.utils.evmore) for more info.

