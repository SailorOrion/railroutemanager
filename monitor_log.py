#!/usr/bin/env python3
import time
import re
from datetime import timedelta
from collections import deque, defaultdict, namedtuple
import curses

Stop = namedtuple("Stop",["location", "delay"])

class Contract:
    def __init__(self, contract_id, contract_type):
        self.cid = contract_id
        self.ctype = contract_type
        self.route = []
        self.trains = {}
        self.route_complete = False

    def add_train(self, train):
        self.trains[train.tid] = train

    def del_train(self, tid):
        t = self.trains[tid]
        del self.trains[tid]
        return t

    def start_of_route(self):
        if len(self.route) > 0:
            return self.route[0]
        return "N/A"

    def end_of_route(self):
        if len(self.route) > 0:
            return self.route[-1]
        return "N/A"

    def check_for_complete_route(self):
        handled_routes = {}
        for train_id, train in self.trains.items():
            tuple_list = tuple(train.locations())
            if tuple_list in handled_routes:
                self.route = train.locations()
                self.route_complete = True
                for train_id, train in self.trains.items():
                    train.finalize(self.end_of_route())
                return
            else:
                handled_routes[tuple_list] = True

    def update_route(self):
        longest_route_length = 0
        longest_route_id = None
        for train_id, train in self.trains.items():
            if train.num_locations() > longest_route_length:
                longest_route_length = train.num_locations()
                longest_route_id = train.tid

        if longest_route_length > 0:
            self.route_complete = False
            self.route = self.trains[longest_route_id].locations()
            for train_id, train in self.trains.items():
                train.done = False
            self.check_for_complete_route()

    def new_location_for_train(self, tid, location, delay):
        if tid not in self.trains:
            self.trains[tid] = Train(tid, location, delay)
            return None
        else:
            self.trains[tid].new_location(location, delay)
            self.update_route()
            if self.route_complete:
                self.trains[tid].finalize(self.end_of_route())

    def purge_trains(self):
        trains_to_delete = [tid for tid,t in self.trains.items() if t.done]
        return [self.del_train(tid) for tid in trains_to_delete]

    def __str__(self):
        return f"Contract {self.cid}" + str(self.trains)

class Train:
    def __init__(self, train_id, location, delay):
        self.tid = train_id
        self._locations = []
        self._locations.append((location, delay))
        self.done = False

    def __hash__(self):
        return hash(self.tid)

    def __eq__(self, other):
        return self.tid == other.tid

    def locations(self):
        return [l[0] for l in self._locations]

    def new_location(self, location, delay):
        self._locations.append((location, delay))

    def num_locations(self):
        return len(self._locations)

    def current_location(self):
        return self._locations[-1][0]

    def current_delay(self):
        return self._locations[-1][1]

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

def update_screen(stdscr, delays, early, recent, contracts, active_train_pos, removed_trains):
    #stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    delay_pad = curses.newpad(1000, max_x // 2 - 2)
    early_pad = curses.newpad(1000, max_x // 2 - 2)
    recent_pad = curses.newpad(1000, max_x // 2 - 2)
    contract_pad = curses.newpad(1000, max_x // 2 - 2)

    stdscr.addstr(max_y // 3 * 0, 0, "Train Delays (sorted by delay):")
    stdscr.addstr(max_y // 3 * 1, 0, "Early trains:")
    stdscr.addstr(max_y // 3 * 2, 0, "Recent delays:")

    for idx, (id, location, delay) in enumerate(delays):
        delay_pad.addstr(idx, 0, '{:8}: {:12s} at {}'.format(delay, id, location))
    for idx, (id, location, early) in enumerate(early):
        early_pad.addstr(idx, 0, '{:8}: {:12s} at {}'.format(early, id, location))
    for idx, (id, location, delay) in enumerate(recent):
        recent_pad.addstr(idx, 0, '{:8}: {:12s} at {}'.format(delay, id, location))

    for idx, train in enumerate(removed_trains, start = 15):
        recent_pad.addstr(idx, 0, f"{train.tid} at {train.current_location()} ({train.current_delay()})")

    idx = 0
    for contract_id, contract in sorted(contracts.items()):
        idx += 1
        #contract_pad.addstr(idx, 0, f"{contract_id}: {len(contract.trains)} from {contract.start_of_route()} to {contract.end_of_route()}: {contract.route_complete}")
        contract_pad.addstr(idx, 0, f"{contract_id} (to {contract.end_of_route()} (Final: {contract.route_complete}):")
        for train_id, train in contract.trains.items():
            idx += 1
            contract_pad.addstr(idx, 4, f"{train_id}: ({train.done}) {train.current_location()}, {train._locations}")

    stdscr.addstr(0, max_x // 2, f"Active trains for contract and last seen location: {idx}, {max_y}, {active_train_pos}")


    delay_pad.refresh(0, 0, 1, 0, max_y // 3 - 2, max_x // 2 - 2)
    early_pad.refresh(0, 0, max_y // 3 + 1, 0, max_y // 3 * 2 - 2, max_x // 2 - 2)
    recent_pad.refresh(0, 0, max_y // 3 * 2 + 1, 0, max_y // 3 * 3 - 2, max_x // 2 - 2)
    if active_train_pos < 0:
        active_train_pos = 0

    if idx > max_y and active_train_pos > idx - max_y + 1:
        active_train_pos = idx - max_y + 1
    contract_pad.refresh(active_train_pos, 0, 0, max_x // 2, max_y - 1, max_x - 1)
    stdscr.refresh()
    return active_train_pos, max_y

def get_contract_id(id):
    match = re.search(r'([A-Za-z]+)(\d{3})', id)
    if match:
        if match.group(1) == 'Reg':
            return match.group(1), match.group(2) + id[6]
        else:
            return match.group(1), match.group(2)

    raise ValueError

def monitor_log(stdscr, filepath):
    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(True)  # Make getch non-blocking

    file = open(filepath, "r")
    #file.seek(0, 2)  # Move the cursor to the end of the file
    delays = {}
    early = {}
    sorted_delays = []
    sorted_early = []
    removed_trains = []
    contracts = {}
    recent_delays = UniqueDeque(maxlen = 12)
    recent_lines = UniqueDeque(maxlen = 200)
    active_train_pos = 0
    page_size = 0

    try:
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)
            else:
                if not recent_lines.appendleft(line):
                    continue
                parsed = parse_log_line(line)
                if parsed:
                    train_id, location, delay = parsed
                    contract_type, contract_id = get_contract_id(train_id)
                    if not contract_id in contracts:
                        contracts[contract_id] = Contract(contract_id, contract_type)

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

                    sorted_delays = sorted(delays.values(), key=lambda x: x[2], reverse=True)
                    sorted_early = sorted(early.values(), key=lambda x: x[2], reverse=False)

                    removed_trains.extend(contracts[contract_id].purge_trains())
            ch = stdscr.getch()
            if ch == ord('q'):  # Exit loop if 'q' is pressed
                break
            elif ch == ord('w'):
                active_train_pos -= 1
            elif ch == ord('s'):
                active_train_pos += 1
            elif ch == curses.KEY_PPAGE:
                active_train_pos -= page_size // 2
            elif ch == curses.KEY_NPAGE:
                active_train_pos += page_size // 2

            active_train_pos, page_size = update_screen(stdscr, sorted_delays, sorted_early, list(recent_delays), contracts, active_train_pos, removed_trains)


    finally:
        file.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python monitor_log.py <log file path>")
        sys.exit(1)

    filepath = sys.argv[1]
    curses.wrapper(monitor_log, filepath)
