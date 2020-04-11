```python
class Documentation:
    RATING = "Acceptable"
```

# Client Support Grid

This grid tries to gather Evennia-specific knowledge about the various clients and protocols used. Everyone's welcome to report their findings.

##### Legend: 

 - **Name**: The name of the client. If it's only available for a specific OS, it should be noted here too.
 - **Version**: Which version or range of client versions were tested.
 - **Comments**: Any comments or quirks on using this client with Evennia should be added here. Also note if some other protocol than Telnet is used (like Websockets, SSH etc). 

## Client Grid

Name                    |   OS      |      Version     |   Comments
------------------------|:---------:|:----------------:|:---------------:
[Evennia Webclient][1]  | All       | 0.6              | Websocket/AJAX. [Known Issues][webclient_issues]
[Mudlet][9]             | All       | 3.4+             | No known issues.
[Atlantis][11]          | Mac       | 0.9.9.4          | No known issues.
[KildClient][22]        |           | 2.11.1           | No known issues.
[Axmud][23]             |           | 1.+              | No known issues.
[tintin++][3]           | Win/*nix  | 2.0+             | No MXP support.
[tinyfugue][4]          | *nix      | 5.0+             | No UTF-8 support.
[MUSHclient][5]         | Win       | 4.94             | NAWS reports full text area.
[Potato][8]             | Win       | 2.0.0            | No MXP, MCCP. Win32 does not understand "localhost". Workaround to send blank lines.
[BeipMU][13]            | Win       | 3.0.255          | No MXP support. Enable 'MUD prompt handling' and disable 'Handle HTML tags'
[Blowtorch][16]         | Android   | 1.1.3            | Telnet NOP displays as surious character.
[Mukluk][17]            | Android   | 2015.11.20       | Telnet NOP displays as spurious character. Has UTF-8/Emoji support.
[Spyrit][19]            |           | 0.4              | No MXP, OOB support.
[JamochaMUD][20]        |           | 5.2              | Does not support ANSI within MXP text.
[MUDMaster][15]         | iOS       | Untested         |
[ZMud][6]               | Win       | Untested         |
[CMud][7]               | Win       | Untested         |
[GMUD][12]              |           |                  | Unsupported. Multiple critical issues.
[MudRammer][14]         | iOS       | 1.8.7            | Unsupported. Multiple critical issues.
[Gnome-MUD][18]         | Unix      | 0.11.2           | Unsupported. Telnet handshake errors. Login seems to fail
[DuckClient][21]        | Chrome    | 4.2              | Unsupported. Multiple critical issues.


[1]: https://github.com/evennia/evennia/wiki/Web%20features#web-client
[webclient_issues]: https://github.com/evennia/evennia/issues?utf8=%E2%9C%93&q=client+status%3Dopen+]
[3]: http://tintin.sourceforge.net/
[4]: http://tinyfugue.sourceforge.net/
[5]: http://mushclient.com/
[6]: http://forums.zuggsoft.com/index.php?page=4&action=file&file_id=65
[7]: http://forums.zuggsoft.com/index.php?page=4&action=category&cat_id=11
[8]: http://www.potatomushclient.com/
[9]: http://www.mudlet.org/
[10]: https://archive.org/details/tucows_196173_SimpleMU_MU_Client
[11]: http://www.riverdark.net/atlantis/
[12]: https://sourceforge.net/projects/g-mud/
[13]: http://www.beipmu.com/
[14]: https://itunes.apple.com/us/app/mudrammer-a-modern-mud-client/id597157072
[15]: https://itunes.apple.com/us/app/mudmaster/id341160033
[16]: http://bt.happygoatstudios.com/
[17]: https://play.google.com/store/apps/details?id=com.crap.mukluk
[18]: https://github.com/GNOME/gnome-mud
[19]: https://spyrit.ierne.eu.org/
[20]: http://jamochamud.org/
[21]: http://duckclient.com/
[22]: https://www.kildclient.org/
[23]: https://axmud.sourceforge.io/

## Workarounds for client issues:

### Issue: Telnet NOP displays as spurious character.

#### Known Clients
* [BlowTorch][16]
* [Mukluk][17]

#### Workarounds
* Set the command in game to `@option NOPKEEPALIVE=off` for the session, or use the `/save` parameter to disable it for that Evennian account permanently.
* Client-side: Set a gag-type trigger on the NOP character to make it invisible to the client.


### Issue: Won't send blank line on Enter key press.

#### Known Clients
* [Potato][8]

#### Workaround
* Press Control Enter, then Enter key again to send blank line.
