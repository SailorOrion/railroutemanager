#!/usr/bin/env python3
import time
import re
from datetime import timedelta
from collections import deque, defaultdict, namedtuple
from enum import Enum
from math import ceil
import curses

DEBUG_TEXT = False
STATUS_SIZE = 3

Stop = namedtuple("Stop",["location", "delay"])
Padsize = namedtuple("Padsize",["start_row", "start_column", "rows", "columns"])

class Contract:
    def __init__(self, contract_id, contract_type, window):
        self.cid = contract_id
        self.ctype = contract_type
        self.route = []
        self.route_source = None
        self.trains = {}
        self.route_complete = False
        self.w = window

    def add_train(self, train):
        self.trains[train.tid] = train

    def del_train(self, tid):
        t = self.trains[tid]
        del self.trains[tid]
        return t

    def length_of_route(self):
        return len(self.route)

    def start_of_route(self):
        if self.length_of_route() > 0:
            return self.route[0]
        return "N/A"

    def end_of_route(self):
        if self.length_of_route() > 0:
            return self.route[-1]
        return "N/A"

    def number_of_trains(self):
        return len(self.trains)

    def is_active(self):
        return self.number_of_trains() > 0

    def check_for_complete_route(self):
        handled_routes = {}
        self.w.update_debug(f"Checking route completion: {len(self.trains)}")
        for train_id, train in self.trains.items():
            tuple_list = tuple(train.locations())
            self.w.update_debug(f"{train_id}: {tuple_list}")
            if tuple_list in handled_routes:
                self.w.update_debug("Route complete!")
                #self.w.update_status(f"Closing route {self.cid}")
                self.route = train.locations()
                self.route_complete = True
                for train_id, train in self.trains.items():
                    train.finalize(self.end_of_route())
                return
            else:
                self.w.update_debug("Incomplete route")
                handled_routes[tuple_list] = True

    def update_route(self, tid):
        longest_route_length = self.length_of_route()
        self.w.update_debug(f"Processing {tid}: Current route length: {len(self.route)}")
        longest_route_id = None
        for train_id, train in self.trains.items():
            if train.num_locations() > longest_route_length:
                longest_route_length = train.num_locations()
                longest_route_id = train.tid

        self.w.update_debug(f"Processing {tid}: New route length: {longest_route_length}")
        if longest_route_length > self.length_of_route():
            self.w.update_debug(f"Processing {tid}: New route length: {self.trains[longest_route_id].num_locations()}, {longest_route_length}")
            self.route_complete = False
            self.route = self.trains[longest_route_id].locations()
            self.w.update_debug(f"Processing {tid}: {self.cid}: {str(self.route)}")
            for train_id, train in self.trains.items():
                train.done = False
        self.check_for_complete_route()

    def new_location_for_train(self, tid, location, delay):
        if tid not in self.trains:
            self.trains[tid] = Train(tid, location, delay)
            self.w.update_debug(f"New train: {tid} at {location}")
        else:
            self.trains[tid].new_location(location, delay)
            self.w.update_debug(f"New location {location} for {tid}")
        self.update_route(tid)
        if self.route_complete:
            self.trains[tid].finalize(self.end_of_route())

    def purge_trains(self):
        trains_to_delete = [tid for tid,t in self.trains.items() if t.done]
        return [self.del_train(tid) for tid in trains_to_delete]

    def print_info(self):
        return f'{"*" if not self.route_complete else " "}{self.cid:>4}: {self.start_of_route()}--{len(self.route)}-->{self.end_of_route()}'

    def __str__(self):
        return f"Contract {self.cid}" + str(self.trains)

class Train:
    def __init__(self, train_id, location, delay):
        self.tid = train_id
        self._locations = []
        self._locations.append(Stop(location, delay))
        self.done = False

    def __hash__(self):
        return hash(self.tid)

    def __eq__(self, other):
        return self.tid == other.tid

    def locations(self):
        return [l.location for l in self._locations]

    def new_location(self, location, delay):
        self._locations.append(Stop(location, delay))

    def num_locations(self):
        return len(self._locations)

    def current_location(self):
        return self._locations[-1].location

    def previous_location(self):
        return self._locations[-2].location

    def first_location(self):
        return self._locations[0].location

    def current_delay(self):
        return self._locations[-1].delay

    def print_info(self):
        if self.num_locations() == 1:
            return f"| {self.current_delay():4.0f} | {self.current_location()}->?"
        elif self.num_locations() == 2:
            return f"| {self.current_delay():4.0f} | {self.previous_location()}->{self.current_location()}"
        else:
            return f"| {self.current_delay():4.0f} | {self.first_location()}--->{self.previous_location()}->{self.current_location()}"


    def finalize(self, terminus):
        if self.current_location() == terminus:
            self.done = True
        else:
            self.done = False

    def __repr__(self):
        return f"{self.tid}: {self.current_location()}({self.num_locations()}: {self._locations})"

class UniqueDeque:
    def __init__(self, maxlen):
        self.deque = deque(maxlen=maxlen)
        self.items_set = set()  # This helps in checking for uniqueness efficiently

    def appendleft(self, item):
        if item not in self.items_set:
            if len(self.deque) >= self.deque.maxlen:
                # Remove the item that will be discarded from the set
                self.items_set.remove(self.deque.pop())
            self.deque.appendleft(item)
            self.items_set.add(item)
            return True
        else:
            return False

    def __iter__(self):
        """Make the deque iterable."""
        return iter(self.deque)
def __repr__(self):
        return str(self.deque)

class Pad:
    class ScrollMode(Enum):
        LINE_UP   = 0
        LINE_DOWN = 1
        PAGE_UP   = 2
        PAGE_DOWN = 3

    _lines        = 0
    _displayfirst = 0

    def __init__(self, pad_height, pad_width, description, padsize):
        self._padsize = padsize
        self._desc = description

        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_RED)

        self._pad = curses.newpad(pad_height, pad_width)

    def resize(self, max_y, max_x, num_rows, num_cols):
        self._top = max_y * self._padsize.start_row // num_rows
        self._bottom = max_y * self._padsize.rows // num_rows + self._top

        self._left = max_x * self._padsize.start_column // num_cols
        self._right = max_x * self._padsize.columns // num_cols + self._left
        self.borderwin()

    def borderwin(self):
        self._borderwin = curses.newwin(self.height(), self.width(), self._top, self._left)
        self._borderwin.box()
        self._borderwin.addstr(0, 2, self._desc, curses.A_REVERSE)
        self._borderwin.refresh()

    def draw_scrollbar(self):
       # Calculate scrollbar slider properties
       if self._lines > self.contentheight():
           scrollbar_height = max(ceil((self.contentheight() / self._lines) * self.contentheight()), 1)
           scrollbar_pos = int((self._displayfirst / self._lines) * (self.contentheight() - scrollbar_height))
       else:
           for y in range(1, self.contentheight()):
               self._borderwin.addch(y, self.width() - 2, ' ')
           return 0

       # Draw the scrollbar
       for y in range(1, self.contentheight()):
           if scrollbar_pos <= y < scrollbar_pos + scrollbar_height:
               self._borderwin.addch(y, self.width() - 2, curses.ACS_CKBOARD)
           else:
               self._borderwin.addch(y, self.width() - 2, ' ')

       return 1


    def draw(self):
        self._borderwin.box()
        self._borderwin.addstr(0, 2, self._desc, curses.A_REVERSE)
        self._borderwin.refresh()
        d = self.draw_scrollbar()
        self._pad.refresh(self._displayfirst, 0, self._top + 1, self._left + 1, self._bottom - 2 , self._right - 2 - d)


    def update_displaypos(self, mode):
        match mode:
            case self.ScrollMode.LINE_UP:
                self._displayfirst -= 1
            case self.ScrollMode.LINE_DOWN:
                self._displayfirst += 1
            case self.ScrollMode.PAGE_UP:
                self._displayfirst -= self.height() // 2
            case self.ScrollMode.PAGE_DOWN:
                self._displayfirst += self.height() // 2
            case _:
                raise ValueError
        self._displayfirst = max(0, min(self._displayfirst, self._lines - self.contentheight()))

    def prepare(self):
        self._pad.erase()
        self._lines = 0

    def addstr(self, y_pos, x_pos, line):
        self._pad.addstr(y_pos, x_pos, line)
        self._lines = max(self._lines, y_pos + 1)

    def addcstr(self, y_pos, x_pos, line, color_pair):
        self._pad.addstr(y_pos, x_pos, line, color_pair)
        self._lines = max(self._lines, y_pos + 1)

    def height(self):
        return self._bottom - self._top

    def contentheight(self):
        return self.height() - 2

    def width(self):
        return self._right - self._left

class Window:
    PAD_SIZE = 5000
    NUM_ROWS = 12
    NUM_COLS = 2
    status_messages = UniqueDeque(maxlen = PAD_SIZE)
    debug_messages = UniqueDeque(maxlen = PAD_SIZE)
    pads = {}
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.max_y, self.max_x = stdscr.getmaxyx()

        full_width = self.max_x
        half_width = self.max_x // 2

        self.pads['status'] = Pad(self.PAD_SIZE, full_width, "Status", Padsize(11, 0, 1, 2))

        self.pads['delay'] = Pad(self.PAD_SIZE, half_width, "Train Delays (by delay)", Padsize(0, 0, 4, 1))
        self.pads['removed'] = Pad(self.PAD_SIZE, half_width, "Recently finished trains:", Padsize(4, 0, 3, 1))
        self.pads['early'] = Pad(self.PAD_SIZE, half_width, "Early trains:", Padsize(7, 0, 2, 1))
        self.pads['recent'] = Pad(self.PAD_SIZE, half_width, "Recent delays:", Padsize(9, 0, 2, 1))

        self.pads['active_contract'] = Pad(self.PAD_SIZE, half_width, "Active trains for contract and last seen location:", Padsize(0, 1, 7, 1))
        self.pads['inactive_contract'] = Pad(self.PAD_SIZE, half_width, "Contracts without active trains", Padsize(7, 1, 3, 1))
        self.pads['debug'] = Pad(self.PAD_SIZE, half_width, "Debug messages", Padsize(10, 1, 1, 1))
        self.resize(stdscr)

    def resize(self, stdscr):
        self.max_y, self.max_x = stdscr.getmaxyx()
        for padid, pad in self.pads.items():
            pad.resize(self.max_y, self.max_x, self.NUM_ROWS, self.NUM_COLS)

    def update_status(self, string):
        return
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

def parse_log_line(line):
    match = re.search(r'Delay for train (.+?)\[(.+?)\]: ([^$]+)', line)
    if match:
        id = match.group(1)
        location = match.group(2)
        delay_str = match.group(3).strip()
        multiplier = 1

        try:
            if (delay_str[0] == '-'):
                multiplier = -1
                delay_str = delay_str[1:]
            delay = timedelta(hours=int(delay_str[0:2]), minutes=int(delay_str[3:5]),
                       seconds=int(delay_str[6:8]))
            delay_in_seconds = delay.total_seconds() * multiplier
        except ValueError:
            delay_in_seconds = 0

        return (id, location, delay_in_seconds)
    return None

def parse_bad_platform(line):
    match = re.search(r'Bad platform for train (.+)', line)
    if match:
        return match.group(1)

    return None

def get_contract_id(id):
    match = re.search(r'([A-Za-z]+)(\d{3})', id)
    if match:
        if match.group(1) == 'Reg':
            return match.group(1), match.group(2) + id[6]
        else:
            return match.group(1), match.group(2)

    raise ValueError

def monitor_log(stdscr, filepath, historypath):
    curses.curs_set(0)  # Hide the cursor
    if curses.has_colors():
        curses.start_color()
    stdscr.nodelay(True)  # Make getch non-blocking

    current_file = open(filepath, "r")
    history_file = None
    if historypath != "":
        history_file = open(historypath, "r")
    delays = {}
    early = {}
    removed_trains = []
    contracts = {}
    recent_delays = UniqueDeque(maxlen = 12)
    recent_lines = UniqueDeque(maxlen = 200)
    removed_trains = UniqueDeque(maxlen = 200)
    active_train_pos = 0
    inactive_train_pos = 0
    active_page_size = 0
    inactive_page_size = 0
    skip_update = True
    w = Window(stdscr)

    try:
        while True:
            if history_file is not None:
                file = history_file
            else:
                file = current_file
            w.update_status(f"Reading {file}")
            line = file.readline()
            if not line:
                time.sleep(0.1)
                if history_file is not None:
                    w.update_status(f"Ending history parsing")
                    history_file.close()
                    history_file = None
                else:
                    skip_update = False
            else:
                if not recent_lines.appendleft(line):
                    continue
                parsed = parse_log_line(line)
                if parsed:
                    train_id, location, delay = parsed
                    contract_type, contract_id = get_contract_id(train_id)
                    if not contract_id in contracts:
                        contracts[contract_id] = Contract(contract_id, contract_type, w)

                    contracts[contract_id].new_location_for_train(train_id, location, delay)

                    if delay > 60:
                        recent_delays.appendleft((train_id, location, delay))
                        delays[contract_id] = (train_id, location, delay)  # Update the existing ID or add a new one
                        early.pop(contract_id, None)
                    elif delay <= -120:
                        early[contract_id] = (train_id, location, delay)
                        delays.pop(contract_id, None)
                    else:
                        delays.pop(contract_id, None)
                        early.pop(contract_id, None)

                    for train in contracts[contract_id].purge_trains():
                        removed_trains.appendleft((train.tid, train.current_location(), train.current_delay()))
                else:
                    tid = parse_bad_platform(line)
                    if tid:
                        w.update_status(f"{tid}: Bad platform!")

                if skip_update:
                    continue
            ch = stdscr.getch()
            if ch == ord('q'):  # Exit loop if 'q' is pressed
                break
            elif ch == ord('w'):
                w.pads['active_contract'].update_displaypos(Pad.ScrollMode.LINE_UP)
            elif ch == ord('s'):
                w.pads['active_contract'].update_displaypos(Pad.ScrollMode.LINE_DOWN)
            elif ch == ord('e'):
                w.pads['inactive_contract'].update_displaypos(Pad.ScrollMode.LINE_UP)
            elif ch == ord('d'):
                w.pads['inactive_contract'].update_displaypos(Pad.ScrollMode.LINE_DOWN)
            elif ch == curses.KEY_PPAGE:
                w.pads['active_contract'].update_displaypos(Pad.ScrollMode.PAGE_UP)
            elif ch == curses.KEY_NPAGE:
                w.pads['active_contract'].update_displaypos(Pad.ScrollMode.PAGE_DOWN)
            elif ch == curses.KEY_RESIZE:
                w.resize(stdscr)

            w.update_delays(sorted(delays.values(), key=lambda x: x[2], reverse=True))
            w.update_early_trains(sorted(early.values(), key=lambda x: x[2], reverse=False))
            w.update_recent_delays(recent_delays)
            w.update_recent_departed(removed_trains)

            w.update_contracts([c for cid, c in sorted(contracts.items()) if c.is_active()], w.pads['active_contract'])
            w.update_contracts([c for cid, c in sorted(contracts.items()) if not c.is_active()], w.pads['inactive_contract'])

            #w.stdscr.refresh()
    finally:
        current_file.close()
        if history_file is not None:
            history_file.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage: python monitor_log.py <log file path>")
        sys.exit(1)

    filepath = sys.argv[1]
    if len(sys.argv) == 3:
        historypath = sys.argv[2]
    else:
        historypath = ""
    curses.wrapper(monitor_log, filepath, historypath)
