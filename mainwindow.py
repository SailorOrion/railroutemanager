import curses
import logging

from collections import deque
from pad import Pad, Padsize

DEBUG_TEXT = True


class Window:
    PAD_SIZE = 5000
    NUM_ROWS = 13
    NUM_COLS = 2

    def __init__(self, stdscr):
        self.status_messages = deque(maxlen=self.PAD_SIZE)
        self.debug_messages = deque(maxlen=self.PAD_SIZE)
        self.pads = {}
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
        self.pads['active_contract']._verbose = 1
        self.pads['inactive_contract'] = Pad(self.PAD_SIZE, half_width, "Contracts without active trains", Padsize(7, 1, 4, 1))
        self.pads['inactive_contract']._verbose = 1

        logging.info(self.pads)
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

        self.pads['status'].update_draw()

    def update_debug(self, string):
        if not DEBUG_TEXT:
            return
        self.debug_messages.appendleft(string)
        self.pads['debug'].prepare()
        for idx, line in enumerate(list(self.debug_messages)):
            self.pads['debug'].addstr(idx, 0, line)

        self.pads['debug'].update_draw()

    def add_trainstr(self, pad, pos, delay, tid, location):
        pad.addstr(pos, 0, '{:8}: {:12s} at {}'.format(delay, tid, location))

    def update_delays(self, delays):
        self.pads['delay'].prepare()

        for idx, (tid, location, delay) in enumerate(delays):
            self.add_trainstr(self.pads['delay'], idx, delay, tid, location)

        self.pads['delay'].update_draw()

    def update_early_trains(self, early):
        self.pads['early'].prepare()

        for idx, (tid, location, early) in enumerate(early):
            self.add_trainstr(self.pads['early'], idx, early, tid, location)

        self.pads['early'].update_draw()

    def update_recent_delays(self, recent):
        self.pads['recent'].prepare()

        for idx, (tid, location, delay) in enumerate(list(recent)):
            self.add_trainstr(self.pads['recent'], idx, delay, tid, location)

        self.pads['recent'].update_draw()

    def update_recent_departed(self, removed_trains):
        self.pads['removed'].prepare()
        for idx, (tid, location, delay) in enumerate(removed_trains):
            self.add_trainstr(self.pads['removed'], idx, delay, tid, location)

        self.pads['removed'].update_draw()

    def update_contracts(self, contracts, pad):
        logging.info(f'preparing pad: {pad._desc}')
        pad.prepare()

        idx = 0
        for contract in contracts:
            pad.addstr(idx, 0, contract.print_info(), ref=contract)
            if idx == 0:
                logging.info(f'   active: {contract.is_active()}')
            idx += 1
            for train_id, train in contract.trains.items():
                color_pair = None
                if train.current_delay() >= 120:
                    color_pair = curses.color_pair(2)
                elif train.current_delay() >= 60:
                    color_pair = curses.color_pair(1)
                pad.addstr(idx, 4, train_id, color_pair=color_pair)
                pad.addstr(idx, 13, train.print_info(), ref=train)
                idx += 1

        pad.update_draw()

    def redraw_all(self):
        for _, pad in self.pads.items():
            pad.draw()

    def detail_view(self, title, message):
        # Calculate the size and position of the window
        height, width = self.max_y - 10, self.max_x - 10
        y, x = (curses.LINES - height) // 2, (curses.COLS - width) // 2

        popup = curses.newwin(height, width, y, x)  # Create a new window
        popup.box()  # Draw a box around the edges

        # Add the title and message text
        popup.addstr(0, 2, ' ' + title + ' ')

        prevline = None
        for idx, line in enumerate(message, start = 3):
            for pos, cellinfo in enumerate(line):
                if cellinfo is not None:
                    (text, color_pair_index) = cellinfo
                    popup.addstr(idx, 2 + pos * 14, text, curses.color_pair(color_pair_index))
                else:
                    if prevline is not None and prevline[pos] is not None: # ACS_DARROW A_BLINK
                        marker = '*'
                        popup.addstr(idx, 2 + pos * 14, f'{marker:>8}')

            prevline = line
        popup.refresh()

        # Wait for user input, then destroy the popup window
        popup.getch()
        popup.clear()
        popup.refresh()
        self.redraw_all()


