# Client Support Grid

This grid tries to gather Evennia-specific knowledge about the various clients and protocols used.
Everyone's welcome to report their findings.

##### Legend: 

 - **Name**: The name of the client. If it's only available for a specific OS, it should be noted
here too.
 - **Version**: Which version or range of client versions were tested.
 - **Comments**: Any comments or quirks on using this client with Evennia should be added here. Also
note if some other protocol than Telnet is used (like Websockets, SSH etc).

## Client Grid

Name                   | Version  | Comments
:----------:------------
[Evennia webclient][1] | 0.6  | Uses WS/AJAX. [Current client issues][2]
[tintin++][3]          | 2.0+ | No MXP support
[tinyfugue][4]         | 5.0+ | No UTF-8 support
[MUSHclient][5] (Win)   | 4.94 | NAWS reports full text area
[Zmud][6] (Win)         | 7.21 | *UNTESTED*              
[Cmud][7] (Win)         | v3   | *UNTESTED*   
[Potato][8]            | 2.0.0b16  | No MXP, MCCP support. Win 32bit does not understand
"localhost", must use `127.0.0.1`. [Newline issue](https://github.com/evennia/evennia/issues/1131).
*Won't send a single blank line on Enter press.
[Mudlet][9]            | 3.4+ | No known issues. Some older versions showed <> as html under MXP.
[SimpleMU][10] (Win)    | full | *UNTESTED*. Discontinued. NAWS reports pixel size.
[Atlantis][11] (Mac)    | 0.9.9.4 | No known issues.
[GMUD][12]             | 0.0.1 | Can't handle any telnet handshakes. Not recommended.
[BeipMU][13] (Win)      | 3.0.255 | No MXP support. Best to enable "MUD prompt handling", disable
"Handle HTML tags".
[MudRammer][14] (IOS)   | 1.8.7 | Bad Telnet Protocol compliance: displays spurious characters.
[MUDMaster][15] (IOS)   | 1.3.1 | *UNTESTED* 
[BlowTorch][16] (Andr)  | 1.1.3 | *Telnet NOP displays as spurious character.
[Mukluk][17] (Andr)     | 2015.11.20| *Telnet NOP displays as spurious character. Has UTF-8/Emoji
support.
[Gnome-MUD][18] (Unix)  | 0.11.2 | Telnet handshake errors. First (only) attempt at logging in
fails.
[Spyrit][19]           | 0.4 | No MXP, OOB support.
[JamochaMUD][20]       | 5.2 | Does not support ANSI within MXP text.
[DuckClient][21] (Chrome)| 4.2 | No MXP support. Displays Telnet Go-Ahead and WILL SUPPRESS-GO-AHEAD
as ù character. Also seems to run the `version` command on connection, which will not work in
`MULTISESSION_MODES` above 1.
[KildClient][22]       | 2.11.1 | No known issues.

## Workarounds for client issues:

### Issue: Telnet NOP displays as spurious character.

Known clients:

* [BlowTorch][16] (Andr)
* [Mukluk][17] (Andr)

Workaround:

* Set the command in game to `@option NOPKEEPALIVE=off` for the session, or use the `/save`
parameter to disable it for that Evennian account permanently.
* Client-side: Set a gag-type trigger on the NOP character to make it invisible to the client.


### Issue: Won't send blank line on Enter key press.

Known clients: 

* [Potato][8]

Workaround: 

* Press Control Enter, then Enter key again to send blank line.


[1]: https://github.com/evennia/evennia/wiki/Web%20features#web-client
[2]: https://github.com/evennia/evennia/issues?utf8=%E2%9C%93&q=client+status%3Dopen+]
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