#!/usr/bin/env python3
import time
import re
import curses

from datetime import timedelta

from contract import Contract
from uniquedeque import UniqueDeque
from mainwindow import Window
from pad import Pad

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
