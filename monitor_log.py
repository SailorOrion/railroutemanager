#!/usr/bin/env python3
import time
import re
from datetime import timedelta
from collections import deque, defaultdict, namedtuple
from enum import Enum
import curses

DEBUG_TEXT = False
STATUS_SIZE = 3

Stop = namedtuple("Stop",["location", "delay"])

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
               # self.w.update_status(f"Closing route {self.cid}")
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
        return f"{self.cid} {len(self.trains)} trains: {self.start_of_route()}--{len(self.route)}-->{self.end_of_route()} (Final: {self.route_complete}):"

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
            return f"{self.tid}: Appeared at {self.current_location()}, delay {self.current_delay()}"
        elif self.num_locations() == 2:
            return f"{self.tid}: {self.previous_location()}->{self.current_location()}, delay {self.current_delay()}"
        else:
            return f"{self.tid}: {self.first_location()}--->{self.previous_location()}->{self.current_location()}, delay {self.current_delay()}"


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

    def __init__(self, pad_height, pad_width, description, params):
        self._pad = curses.newpad(pad_height, pad_width)
        self._desc = description
        self._top, self._left, self._bottom, self._right = params
        self._lines = 0
        self._displayfirst = 0

    def update_pos(y_pos, x_pos, height, width):
        return #TODO
        self._top = y_pos
        self._left = x_pos
        self._bottom = y_pos + height
        self._right = x_pos + width

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
        self._displayfirst = max(0, min(self._displayfirst, self._lines - self.height() + 2))

    def draw(self):
        self._pad.border()
        self._pad.addstr(0, 2, self._desc, curses.A_REVERSE)
        self._pad.refresh(self._displayfirst, 1, self._top + 1, self._left, self._bottom, self._right)

    def prepare(self):
        self._pad.erase()
        self._lines = 0

    def addstr(self, y_pos, x_pos, line):
        self._pad.addstr(y_pos + 1, x_pos + 2, line)
        self._lines = max(self._lines, y_pos + 1)

    def height(self):
        return self._bottom - self._top

class Window:
    PAD_SIZE = 5000
    NUM_ROWS = 12
    NUM_COLS = 2
    status_messages = UniqueDeque(maxlen = PAD_SIZE)
    debug_messages = UniqueDeque(maxlen = PAD_SIZE)
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.max_y, self.max_x = stdscr.getmaxyx()

        full_width = self.max_x
        half_width = self.max_x // 2

        self.status_pad = Pad(self.PAD_SIZE, full_width, "Status", self.get_params(11, 0, 1, 2))

        self.delay_pad = Pad(self.PAD_SIZE, half_width, "Train Delays (by delay)", self.get_params(0, 0, 4, 1))
        self.removed_pad = Pad(self.PAD_SIZE, half_width, "Recently finished trains:", self.get_params(4, 0, 3, 1))
        self.early_pad = Pad(self.PAD_SIZE, half_width, "Early trains:", self.get_params(7, 0, 2, 1))
        self.recent_pad = Pad(self.PAD_SIZE, half_width, "Recent delays:", self.get_params(9, 0, 2, 1))

        self.active_contract_pad = Pad(self.PAD_SIZE, half_width, "Active trains for contract and last seen location:", self.get_params(0, 1, 7, 1))
        self.inactive_contract_pad = Pad(self.PAD_SIZE, half_width, "Contracts without active trains", self.get_params(7, 1, 3, 1))
        self.debug_pad = Pad(self.PAD_SIZE, half_width, "Debug messages", self.get_params(10, 1, 1, 1))


    def get_params(self, row, col, rows, cols):
        if row + rows > self.NUM_ROWS or rows <= 0 or col + cols > self.NUM_COLS or cols <= 0:
            raise ValueError
        top = self.max_y * row // self.NUM_ROWS + 1
        bottom = self.max_y * rows // self.NUM_ROWS + top - 2
        left = self.max_x * col // self.NUM_COLS + 1
        right = self.max_x * cols // self.NUM_COLS + left - 2
        return top, left, bottom, right

    def update_status(self, string):
        return
        self.status_messages.appendleft(string)
        self.status_pad.prepare()
        for idx, line in enumerate(list(self.status_messages)):
            self.status_pad.addstr(idx, 0, line)

        self.status_pad.draw()

    def update_debug(self, string):
        if not DEBUG_TEXT:
            return
        self.debug_messages.appendleft(string)
        self.debug_pad.prepare()
        for idx, line in enumerate(list(self.debug_messages)):
            self.debug_pad.addstr(idx, 0, line)

        self.debug_pad.draw()

    def add_trainstr(self, pad, pos, delay, tid, location):
        pad.addstr(pos, 0, '{:8}: {:12s} at {}'.format(delay, tid, location))

    def update_delays(self, delays):
        self.delay_pad.prepare()

        for idx, (tid, location, delay) in enumerate(delays):
            self.add_trainstr(self.delay_pad, idx, delay, tid, location)

        self.delay_pad.draw()

    def update_early_trains(self, early):
        self.early_pad.prepare()

        for idx, (tid, location, early) in enumerate(early):
            self.add_trainstr(self.early_pad, idx, early, tid, location)

        self.early_pad.draw()

    def update_recent_delays(self, recent):
        self.recent_pad.prepare()

        for idx, (tid, location, delay) in enumerate(list(recent)):
            self.add_trainstr(self.recent_pad, idx, delay, tid, location)

        self.recent_pad.draw()

    def update_recent_departed(self, removed_trains):
        self.removed_pad.prepare()
        for idx, (tid, location, delay) in enumerate(removed_trains):
            self.add_trainstr(self.removed_pad, idx, delay, tid, location)

        self.removed_pad.draw()

    def update_contracts(self, contracts, pad):
        pad.prepare()

        idx = 0
        for contract in contracts:
            pad.addstr(idx, 0, contract.print_info())
            idx += 1
            for train_id, train in contract.trains.items():
                pad.addstr(idx, 4, train.print_info())
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
                        w.update_status("{tid}: Bad platform!")

                if skip_update:
                    continue
            ch = stdscr.getch()
            if ch == ord('q'):  # Exit loop if 'q' is pressed
                break
            elif ch == ord('w'):
                w.active_contract_pad.update_displaypos(Pad.ScrollMode.LINE_UP)
            elif ch == ord('s'):
                w.active_contract_pad.update_displaypos(Pad.ScrollMode.LINE_DOWN)
            elif ch == ord('e'):
                w.inactive_contract_pad.update_displaypos(Pad.ScrollMode.LINE_UP)
            elif ch == ord('d'):
                w.inactive_contract_pad.update_displaypos(Pad.ScrollMode.LINE_DOWN)
            elif ch == curses.KEY_PPAGE:
                w.active_contract_pad.update_displaypos(Pad.ScrollMode.PAGE_UP)
            elif ch == curses.KEY_NPAGE:
                w.active_contract_pad.update_displaypos(Pad.ScrollMode.PAGE_DOWN)

            w.update_delays(sorted(delays.values(), key=lambda x: x[2], reverse=True))
            w.update_early_trains(sorted(early.values(), key=lambda x: x[2], reverse=False))
            w.update_recent_delays(recent_delays)
            w.update_recent_departed(removed_trains)

            w.update_contracts([c for cid, c in sorted(contracts.items()) if c.is_active()], w.active_contract_pad)
            w.update_contracts([c for cid, c in sorted(contracts.items()) if not c.is_active()], w.inactive_contract_pad)

            w.stdscr.refresh()
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
