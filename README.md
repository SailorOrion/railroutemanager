# Rail Route Manager
This is a simple log file parser which will analyse your contracts and trains.

## Disclaimer
This is very much work in progress. It shouldn't break anything, since it does nothing more than read the Player.log file

## Instructions
### Prepraration and Execution
In order to obtain detailed information, Rail Route Manager requires a couple of consecutive game cycles (or hours) worth of log files for a single save game.
At the moment, here are the recommendations to get the most accurate information:
* Every time you want to load a new savegame/map, you'll need to restart the game.
* Once the game is closed (i.e. you're done playing a map), append the game's log file (Player.log) to an arbitrary file (I tend to call it History.log).
To start the manager:
```
./monitor_log <PATH_TO_PLAYER_LOG> <PATH_TO_HISTORY_FILE>
```
if you don't have a history file, just leave out that part

### User Interface
The game has two windows: a primary window and a contract detail view
#### Keyboard Shortcuts
|Key(s)   |Function                  |
|---------|--------------------------|
|w/s      |Scroll active contracts   |
|x        |Open contract detail      |
|q        |Quit                      |
#### Primary Window
#### Contract Detail

