#!/usr/bin/env python3
import time
import re
from datetime import timedelta
from collections import deque, defaultdict
import curses

class Train:
    def __init__(self, id, location):
        self.id = id
        self.location = location

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

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

def update_screen(stdscr, delays, early, recent, active_trains, active_train_pos):
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

    idx = 0
    for contract, trains in sorted(active_trains.items()):
        idx += 1
        contract_pad.addstr(idx, 0, f"{contract}:")
        for train in trains:
            idx += 1
            contract_pad.addstr(idx, 4, f"{train.id}: {train.location}")

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
    active_trains = defaultdict(set)
    recent_delays = UniqueDeque(maxlen = 12)
    active_train_pos = 0
    page_size = 0

    try:
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.01)
            else:
                parsed = parse_log_line(line)
                if parsed:
                    id, location, delay = parsed
                    type, contract_id = get_contract_id(id)
                    active_trains[contract_id].add(Train(id, location))
                    if delay > 60:
                        recent_delays.appendleft((id, location, delay))
                        delays[contract_id] = (id, location, delay)  # Update the existing ID or add a new one
                        early.pop(contract_id, None)
                    elif delay <= -120:
                        early[contract_id] = (id, location, delay)
                        delays.pop(contract_id, None)
                    else:
                        delays.pop(contract_id, None)
                        early.pop(contract_id, None)

                    sorted_delays = sorted(delays.values(), key=lambda x: x[2], reverse=True)
                    sorted_early = sorted(early.values(), key=lambda x: x[2], reverse=False)

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

            active_train_pos, page_size = update_screen(stdscr, sorted_delays, sorted_early, list(recent_delays), active_trains, active_train_pos)


    finally:
        file.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python monitor_log.py <log file path>")
        sys.exit(1)

    filepath = sys.argv[1]
    curses.wrapper(monitor_log, filepath)
