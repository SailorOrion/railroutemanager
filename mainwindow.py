import curses

from collections import deque
from pad import Pad, Padsize

DEBUG_TEXT = True

class Window:
    PAD_SIZE = 5000
    NUM_ROWS = 13
    NUM_COLS = 2
    status_messages = deque(maxlen = PAD_SIZE)
    debug_messages = deque(maxlen = PAD_SIZE)
    pads = {}
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.max_y, self.max_x = stdscr.getmaxyx()

        full_width = self.max_x
        half_width = self.max_x // 2

        self.pads['status'] = Pad(self.PAD_SIZE, full_width, "Status", Padsize(11, 0, 2, 2))

        self.pads['delay'] = Pad(self.PAD_SIZE, half_width, "Train Delays (by delay)", Padsize(0, 0, 4, 1))
        self.pads['removed'] = Pad(self.PAD_SIZE, half_width, "Recently finished trains:", Padsize(4, 0, 3, 1))
        self.pads['early'] = Pad(self.PAD_SIZE, half_width, "Early trains:", Padsize(7, 0, 2, 1))
        self.pads['recent'] = Pad(self.PAD_SIZE, half_width, "Recent delays:", Padsize(9, 0, 2, 1))

        self.pads['active_contract'] = Pad(self.PAD_SIZE, half_width, "Active trains for contract and last seen location:", Padsize(0, 1, 7, 1))
        self.pads['inactive_contract'] = Pad(self.PAD_SIZE, half_width, "Contracts without active trains", Padsize(7, 1, 4, 1))
        self.resize(stdscr)

    def resize(self, stdscr):
        self.max_y, self.max_x = stdscr.getmaxyx()
        stdscr.clear()
        for padid, pad in self.pads.items():
            pad.resize(self.max_y, self.max_x, self.NUM_ROWS, self.NUM_COLS)

    def update_status(self, string):
        self.status_messages.appendleft(string)
        self.pads['status'].prepare()
        for idx, line in enumerate(list(self.status_messages)):
            self.pads['status'].addstr(idx, 0, line)

        self.pads['status'].draw()

    def update_debug(self, string):
        if not DEBUG_TEXT:
            return
        self.debug_messages.appendleft(string)
        self.pads['debug'].prepare()
        for idx, line in enumerate(list(self.debug_messages)):
            self.pads['debug'].addstr(idx, 0, line)

        self.pads['debug'].draw()

    def add_trainstr(self, pad, pos, delay, tid, location):
        pad.addstr(pos, 0, '{:8}: {:12s} at {}'.format(delay, tid, location))

    def update_delays(self, delays):
        self.pads['delay'].prepare()

        for idx, (tid, location, delay) in enumerate(delays):
            self.add_trainstr(self.pads['delay'], idx, delay, tid, location)

        self.pads['delay'].draw()

    def update_early_trains(self, early):
        self.pads['early'].prepare()

        for idx, (tid, location, early) in enumerate(early):
            self.add_trainstr(self.pads['early'], idx, early, tid, location)

        self.pads['early'].draw()

    def update_recent_delays(self, recent):
        self.pads['recent'].prepare()

        for idx, (tid, location, delay) in enumerate(list(recent)):
            self.add_trainstr(self.pads['recent'], idx, delay, tid, location)

        self.pads['recent'].draw()

    def update_recent_departed(self, removed_trains):
        self.pads['removed'].prepare()
        for idx, (tid, location, delay) in enumerate(removed_trains):
            self.add_trainstr(self.pads['removed'], idx, delay, tid, location)

        self.pads['removed'].draw()

    def update_contracts(self, contracts, pad):
        pad.prepare()

        idx = 0
        for contract in contracts:
            pad.addstr(idx, 0, contract.print_info())
            idx += 1
            for train_id, train in contract.trains.items():
                trainstr = train.print_info()
                if train.current_delay() >= 120:
                    pad.addcstr(idx, 4, train_id, curses.color_pair(2))
                elif train.current_delay() >= 60:
                    pad.addcstr(idx, 4, train_id, curses.color_pair(1))
                else:
                    pad.addstr(idx, 4, train_id)
                pad.addstr(idx, 13, train.print_info())
                idx += 1

        pad.draw()
