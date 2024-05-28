import curses
import logging

from collections import deque
from pad import Pad, PadSize

DEBUG_TEXT = True


class Window:
    PAD_SIZE = 5000
    PAD_WIDTH = 500
    NUM_ROWS = 13
    NUM_COLS = 2

    def __init__(self, stdscr):
        self.status_messages = deque(maxlen=self.PAD_SIZE)
        self.debug_messages = deque(maxlen=self.PAD_SIZE)
        self.pads = {}
        self.popup = None
        self.stdscr = stdscr
        self.max_y, self.max_x = stdscr.getmaxyx()

        Pad.set_size_params(self.max_y, self.max_x, self.NUM_ROWS, self.NUM_COLS)

        self.pads['status'] = Pad(self.PAD_SIZE, self.PAD_WIDTH, "Status", PadSize(11, 0, 2, 2))

        self.pads['delay'] = Pad(self.PAD_SIZE, self.PAD_WIDTH, "Train Delays (by delay)", PadSize(0, 0, 4, 1))
        self.pads['removed'] = Pad(self.PAD_SIZE, self.PAD_WIDTH, "Recently finished trains:", PadSize(4, 0, 3, 1))
        self.pads['early'] = Pad(self.PAD_SIZE, self.PAD_WIDTH, "Early trains:", PadSize(7, 0, 2, 1))
        self.pads['recent'] = Pad(self.PAD_SIZE, self.PAD_WIDTH, "Recent delays:", PadSize(9, 0, 2, 1))

        self.pads['active_contract'] = Pad(self.PAD_SIZE, self.PAD_WIDTH,
                                           "Active trains for contract and last seen location:", PadSize(0, 1, 7, 1))
        self.pads['inactive_contract'] = Pad(self.PAD_SIZE, self.PAD_WIDTH, "Contracts without active trains",
                                             PadSize(7, 1, 4, 1))

        self.resize(stdscr)

    def resize(self, stdscr):
        logging.info(f'Resizing to {stdscr.getmaxyx()}')
        new_y, new_x = stdscr.getmaxyx()
        if self.max_x != new_x or self.max_y != new_y:
            self.max_y, self.max_x = stdscr.getmaxyx()
            Pad.set_size_params(self.max_y, self.max_x, self.NUM_ROWS, self.NUM_COLS)
        for pad_id, pad in self.pads.items():
            pad.resize()

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

    def _add_train_str(self, pad, pos, delay, tid, location):
        pad.addstr(pos, 0, '{:8}: {:12s} at {}'.format(delay, tid, location))

    def update_delays(self, delays):
        self.pads['delay'].prepare()

        for idx, (tid, location, delay) in enumerate(delays):
            self._add_train_str(self.pads['delay'], idx, delay, tid, location)

        self.pads['delay'].update_pad()

    def update_early_trains(self, early):
        self.pads['early'].prepare()

        for idx, (tid, location, early) in enumerate(early):
            self._add_train_str(self.pads['early'], idx, early, tid, location)

        self.pads['early'].update_pad()

    def update_recent_delays(self, recent):
        self.pads['recent'].prepare()

        for idx, (tid, location, delay) in enumerate(recent):
            self._add_train_str(self.pads['recent'], idx, delay, tid, location)

        self.pads['recent'].update_pad()

    def update_recent_departed(self, removed_trains):
        self.pads['removed'].prepare()
        for idx, (tid, location, delay) in enumerate(removed_trains):
            self._add_train_str(self.pads['removed'], idx, delay, tid, location)

        self.pads['removed'].update_pad()

    def update_contracts(self, contracts, pad):
        pad.prepare()

        idx = 0
        for contract in contracts:
            pad.addstr(idx, 0, contract.print_info(), ref=contract)
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

        pad.update_pad()

    def redraw_all(self):
        for _, pad in self.pads.items():
            pad.draw()

    def has_popup(self):
        return self.popup is not None

    def destroy_popup(self):
        self.popup.erase()
        self.popup = None
        self.redraw_all()

    def open_view(self):
        title = ' Open contract segment '
        height, width = 6, len(title) + 4
        start_y = (self.max_y - height) // 2
        start_x = (self.max_x - width) // 2
        self.popup = curses.newwin(height, width, start_y, start_x)
        self.popup.box()
        self.popup.addstr(0, 2, title)

        string_input = ""
        while True:
            self.popup.addstr(2, 2, string_input + ' ' * (width - len(string_input) - 2))  # Clear remaining line
            self.popup.refresh()
            key = self.popup.getch()

            if key == 27 or key == ord('q'):  # ESC key
                self.destroy_popup()
                return None
            elif key == curses.KEY_ENTER or key == 10:
                if (len(string_input) == 3 and string_input.isdigit()) or len(string_input) == 4 and string_input[0:2].isdigit() and string_input[3].isalpha():
                    self.destroy_popup()
                    return string_input
                else:
                    self.popup.addstr(2, 2, "Err" + ' ' * (width - 4))
                    self.popup.refresh()
            elif key in [curses.KEY_BACKSPACE, 127, 8]:  # Handle backspace
                string_input = string_input[:-1]
            elif len(string_input) < 4:
                string_input += chr(key).upper()

    def detail_view(self, title, message):
        cell_width = 14
        # Calculate the size and position of the window
        height = len(message) + 8
        width = len(message[0]) * cell_width + 6
        y, x = (curses.LINES - height) // 2, (curses.COLS - width) // 2

        self.popup = curses.newwin(height, width, y, x)  # Create a new window
        self.popup.box()  # Draw a box around the edges

        # Add the title and message text
        self.popup.addstr(0, 2, ' ' + title + ' ')

        previous_line = None
        for idx, line in enumerate(message, start=3):
            for pos, cell_info in enumerate(line):
                if cell_info is not None:
                    (text, color_pair_index) = cell_info
                    self.popup.addstr(idx, 3 + pos * cell_width, text, curses.color_pair(color_pair_index))
                else:
                    if previous_line is not None and previous_line[pos] is not None:  # ACS_DARROW A_BLINK
                        marker = '*'
                        self.popup.addstr(idx, 3 + pos * cell_width, f'{marker:>8}')

            previous_line = line
        self.popup.refresh()
        return self.popup
