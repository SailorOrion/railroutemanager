# Rail Route Manager
This is a simple log file parser which will analyse your contracts and trains.

## Disclaimer
This is very much work in progress. It shouldn't break anything, since it does nothing more than read the Player.log file

## Instructions
### Requirements
* python 3.11 or higher
* python-curses
* python-plyer
### Prepraration and Execution
In order to obtain detailed information, Rail Route Manager requires a couple of consecutive game cycles (or hours) worth of log files for a single save game.
To start the manager:
```
./monitor_log <PATH_TO_PLAYER_LOG> <PATH_TO_HISTORY_FILE>
```
if you want to have a history file, just leave out that part.
Once a line from the log file is processed, it is appended to the history file. If you close the manager it will write a marker until what point the Player.log file has been read, and upon next start will resume reading from that point on.

Here's the recommended order:
1. Start Rail Route and open your savegame or start a new game
1. Start The Manager
1. Play
1. End Rail Route
1. End The Manager

It is possible to run this with multiple maps/savegames if you write a different history file for every map. It's much easier to manage if you do the steps shown above every time you switch maps.

### User Interface
The game has two windows: a primary window and a contract detail view
#### Primary Window
The primary window contains 7 subwindows (from top to bottom and left to right)
1. Currently delayed trains on the map (if delayed more than 60 seconds)
1. Trains that have recently left the map and their delay
1. Trains which are running early (they might mess up your schedule as well)
1. Most recent delays (the first window is order by delay, this one by time)
1. Contracts with active trains on the map. There are four characters describing the delay status of the contract.
    1. Delayed in previous trains (? means greater than 60 seconds, ! means greater than 120 seconds)
    1. Early arrival in previous trains (+ means greater than 60 seconds, * means greater than 120 seconds)
    1. Delayed in current trains (? means greater than 60 seconds, ! means greater than 120 seconds)
    1. Early arrival in current trains (+ means greater than 60 seconds, * means greater than 120 seconds)
1. Contrants without active trains
1. Status window
#### Keyboard Shortcuts
|Key(s)   |Function                  |
|---------|--------------------------|
|w/s      |Scroll active contracts   |
|e/d      |Scroll inactive contracts |
|r/f      |Select active contracts   |
|t/g      |Select inactive contracts |
|x        |Open contract detail      |
|q        |Quit                      |
#### Primary Window
#### Contract Detail

