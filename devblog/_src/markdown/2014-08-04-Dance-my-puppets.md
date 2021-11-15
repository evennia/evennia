[![](https://lh3.googleusercontent.com/proxy/hraqnaf9pLN_5rYSN5vnqysZwOaipiA32vImwp1-TWic6HtbYxqlwtRLjJgl9WQd6IY0TsCGPiPaEw8HEEgcxx_yy9S3E3KRKRk0Ksdm50RDLgAtNaftkVdS2EGU0nuOqdIeUHIWmijKMWNtknEj7891LEFUgjaTDCcsvenRq7f3032soPG_mfUz5bXw7PMGiyQd42PSnvbBh4ufwvzvlQZp-93GVKsTH40MN5vgQm0SfEDVp4fNY49Yyo16MLMQM5MVEfWA9EKmy_HxCPwX07NmWLwIRbRD1_q821tQXDaYeJzzj40If2hJrB1EKPTzo41A7HKfsPbRnla48S9wtqcny_kTO88AdcF1=s0-d)](http://upload.wikimedia.org/wikipedia/commons/thumb/7/70/5016_-_Archaeological_Museum,_Athens_-_Dolls_-_Photo_by_Giovanni_Dall%27Orto,_Nov_13_2009.jpg/374px-5016_-_Archaeological_Museum,_Athens_-_Dolls_-_Photo_by_Giovanni_Dall%27Orto,_Nov_13_2009.jpg)

In many traditional multiplayer text engines for MUD/MUSH/MU*, the player connects to the game with an account name that also becomes their character's in-game name. When they log into the game they immediately "become" that character. If they want to play with another character, they need to create a new account.  
  
A single-login system is easy to implement but many code bases try to expand with some sort of "account system" where a single login "account" will allow you to manage one or more game characters. Matthew “Chaos” Sheahan  beautifully argues for the benefits of an account system in the April issue of [Imaginary Realities](http://journal.imaginary-realities.com/volume-06/issue-01/index.html); you can read his article [here](http://journal.imaginary-realities.com/volume-06/issue-01/your-mud-should-have-an-account-system/index.html).  
  
  

### Evennia and account systems

First a brief show of how Evennia handles this. We use the following separation:  
  

**Session(s) <-> Player <-> Objects/Characters(s)**

  
The _Session_ object represents individual client connections to Evennia. The _Player_ is our "account" object. It holds the password hash and your login name but has no in-game existence. Finally we have _Objects_, the most common being a subclass of Object we call _Character._ Objects exist in the game. They are "puppeted" by Sessions via the Player account.  
  
From this separation an account system follows naturally. Evennia also offers fully flexible puppeting out of the box: Changing characters (or for staff to puppet an NPC) is simply a matter of "disconnecting" from one Character and connecting to another (presuming you have permission to do so).  
  

### The Multisession modes of Evennia

This is the main gist of this entry since we just added another of these (mode 3). Evennia now offers four different _multisession modes_ for the game designer to choose between. They affect how you gamers may control their characters and can be changed with just a server reload.   

#### Mode 0

This is emulates the "traditional" mud codebase style. In mode 0 a Session controls one Character and one character only. Only one Session per account is allowed - that is, if a user try to connect to their Player account with a different client the old connection will be disconnected. In the default command set a new Character is created with the same name as the Player account and the two are automatically connected whenever they log in. To the user this makes Player and Character seem to be virtually the same thing.  

#### Mode 1

In this mode, multiple Sessions are allowed per Player account. You still only have one Character per account but you can control that Character from any number of simultaneously connected clients. This is a requirement from MUSHes and some slower-moving games where there are communities of gamers who want to conveniently track the progress of the game continuously on multiple clients and computers.   

#### Mode 2

In multisession mode 2, multiple Characters are allowed per Player account. No Characters are created by default in this mode, rather the default command set will drop you to a simplified OOC management screen where you can create new characters, list the ones you already have and puppet them. This mode offers true multiplaying, where you can connect via several clients simultaneously, each Session controlling a different Character.  

#### Mode 3

This mode allows gamers not only to play multiple Characters on the same Player account (as in mode 2) but to also connect _multiple Sessions to each Character._ This is a multi-character version of Mode 1, where players can control the same Character via Player logins from several different clients on different machines in any combination.  
  
  
  
It's interesting that some of these modes may seem silly or superfluous to people used to a certain type of MU* yet are killer features for other communities. It goes to show how different the needs are for users of different game styles.