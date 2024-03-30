# Game Quests

A _quest_ is a common feature of games. From classic fetch-quests like retrieving 10 flowers to complex quest chains involving drama and intrigue, quests need to be properly tracked in our game. 

A quest follows a specific development: 

1. The quest is _started_. This normally involves the player accepting the quest, from a quest-giver, job board or other source. But the quest could also be thrust on the player ("save the family from the burning house before it collapses!")
2. A quest may consist of one or more 'steps'. Each step has its own set of finish conditions. 
3. At suitable times the quest is _checked_. This could happen on a timer or when trying to 'hand in' the quest. When checking, the current 'step' is checked against its finish conditions. If ok, that step is closed and the next step is checked until it either hits a step that is not yet complete, or there are no more steps, in which case the entire quest is complete.