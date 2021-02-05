# Client Support Grid

This grid tries to gather info about different MU clients when used with Evennia.
If you want to report a problem, update an entry or add a client, make a 
new [documentation issue](github:issue) for it. Everyone's encouraged to report their findings.

##### Legend: 

 - **Name**: The name of the client. Also note if it's OS-specific.
 - **Version**: Which version or range of client versions were tested.
 - **Comments**: Any quirks on using this client with Evennia should be added here.

## Client Grid

```eval_rst

+----------------------------+-----------+----------------------------------------------------------------+
| Name                       | Version   | Comments                                                       |
+============================+===========+================================================================+
| `Evennia Webclient`_       | 0.9       | Evennia-specific                                               |
+----------------------------+-----------+----------------------------------------------------------------+
| `tintin++`_                | 2.0+      | No MXP support                                                 |
+----------------------------+-----------+----------------------------------------------------------------+
| tinyfugue_                 | 5.0+      | No UTF-8 support                                               |
+----------------------------+-----------+----------------------------------------------------------------+
| MUSHclient_ (Win)          | 4.94      | NAWS reports full text area                                    |
+----------------------------+-----------+----------------------------------------------------------------+
| Zmud_ (Win)                | 7.21      | *UNTESTED*                                                     |
+----------------------------+-----------+----------------------------------------------------------------+
| Cmud_ (Win)                | v3        | *UNTESTED*                                                     |
+----------------------------+-----------+----------------------------------------------------------------+
| Potato_                    | 2.0.0b16  | No MXP, MCCP support. Win 32bit does not understand            |
|                            |           | "localhost", must use `127.0.0.1`.                             |
+----------------------------+-----------+----------------------------------------------------------------+
| Mudlet_                    | 3.4+      | No known issues. Some older versions showed <> as html         |
|                            |           | under MXP.                                                     |
+----------------------------+-----------+----------------------------------------------------------------+
| SimpleMU_ (Win)            | full      | Discontinued. NAWS reports pixel size.                         |
+----------------------------+-----------+----------------------------------------------------------------+
| Atlantis_ (Mac)            | 0.9.9.4   | No known issues.                                               |
+----------------------------+-----------+----------------------------------------------------------------+
| GMUD_                      | 0.0.1     | Can't handle any telnet handshakes. Not recommended.           |
+----------------------------+-----------+----------------------------------------------------------------+
| BeipMU_ (Win)              | 3.0.255   | No MXP support. Best to enable "MUD prompt handling", disable  |
|                            |           | "Handle HTML tags".                                            |
+----------------------------+-----------+----------------------------------------------------------------+
| MudRammer_ (IOS)           | 1.8.7     | Bad Telnet Protocol compliance: displays spurious characters.  |
+----------------------------+-----------+----------------------------------------------------------------+
| MUDMaster_                 | 1.3.1     | *UNTESTED*                                                     |
+----------------------------+-----------+----------------------------------------------------------------+
| BlowTorch_ (Andr)          | 1.1.3     | Telnet NOP displays as spurious character.                     |
+----------------------------+-----------+----------------------------------------------------------------+
| Mukluk_ (Andr)             | 2015.11.20| Telnet NOP displays as spurious character. Has UTF-8/Emoji     |
|                            |           | support.                                                       |
+----------------------------+-----------+----------------------------------------------------------------+
| Gnome-MUD_ (Unix)          | 0.11.2    | Telnet handshake errors. First (only) attempt at logging in    |
|                            |           | fails.                                                         |
+----------------------------+-----------+----------------------------------------------------------------+
| Spyrit_                    | 0.4       | No MXP, OOB support.                                           |
+----------------------------+-----------+----------------------------------------------------------------+
| JamochaMUD_                | 5.2       | Does not support ANSI within MXP text.                         |
+----------------------------+-----------+----------------------------------------------------------------+
| DuckClient_ (Chrome)       | 4.2       | No MXP support. Displays Telnet Go-Ahead and                   |
|                            |           | WILL SUPPRESS-GO-AHEAD as ù character. Also seems to run       |
|                            |           | the `version` command on connection, which will not work in    |
|                            |           | `MULTISESSION_MODES` above 1.                                  |
+----------------------------+-----------+----------------------------------------------------------------+
| KildClient_                | 2.11.1    | No known issues.                                               |
+----------------------------+-----------+----------------------------------------------------------------+

.. _Evennia Webclient: ../Components/Webclient.html
.. _tintin++: http://tintin.sourceforge.net/
.. _tinyfugue: http://tinyfugue.sourceforge.net/
.. _MUSHclient: http://mushclient.com/
.. _Zmud: http://forums.zuggsoft.com/index.php?page=4&action=file&file_id=65
.. _Cmud: http://forums.zuggsoft.com/index.php?page=4&action=category&cat_id=11
.. _Potato: http://www.potatomushclient.com/
.. _Mudlet: http://www.mudlet.org/
.. _SimpleMU: https://archive.org/details/tucows_196173_SimpleMU_MU_Client
.. _Atlantis: http://www.riverdark.net/atlantis/
.. _GMUD: https://sourceforge.net/projects/g-mud/
.. _BeipMU: http://www.beipmu.com/
.. _MudRammer: https://itunes.apple.com/us/app/mudrammer-a-modern-mud-client/id597157072
.. _MUDMaster: https://itunes.apple.com/us/app/mudmaster/id341160033
.. _BlowTorch: http://bt.happygoatstudios.com/
.. _Mukluk: https://play.google.com/store/apps/details?id=com.crap.mukluk
.. _Gnome-MUD: https://github.com/GNOME/gnome-mud
.. _Spyrit: https://spyrit.ierne.eu.org/
.. _JamochaMUD: http://jamochamud.org/
.. _DuckClient: http://duckclient.com/
.. _KildClient: https://www.kildclient.org/

```
## Workarounds for client issues:

### Issue: Telnet NOP displays as spurious character.

Known clients:

* BlowTorch (Andr)
* Mukluk (Andr)

Workaround:

* In-game: Use `@option NOPKEEPALIVE=off` for the session, or use the `/save`
parameter to disable it for that Evennia account permanently.
* Client-side: Set a gag-type trigger on the NOP character to make it invisible to the client.


