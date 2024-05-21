#!/usr/bin/env python3
import time
import re
import curses
import logging

from datetime import timedelta

from contract import Contract
from uniquedeque import UniqueDeque
from mainwindow import Window
from pad import Pad
from plyer import notification


def parse_log_line(line):
    match = re.search(r'Delay for train (.+?)\[(.+?)]: ([^$]+)', line)
    if match:
        train_id = match.group(1)
        location = match.group(2)
        delay_str = match.group(3).strip()
        multiplier = 1

        try:
            if delay_str[0] == '-':
                multiplier = -1
                delay_str = delay_str[1:]
            delay = timedelta(hours=int(delay_str[0:2]), minutes=int(delay_str[3:5]),
                              seconds=int(delay_str[6:8]))
            delay_in_seconds = delay.total_seconds() * multiplier
        except ValueError:
            delay_in_seconds = 0

        return train_id, location, delay_in_seconds
    return None


def parse_bad_platform(line):
    match = re.search(r'Bad platform for train (.+)', line)
    if match:
        return match.group(1)

    return None


def get_contract_id(train_id):
    match = re.search(r'([A-Za-z]+)(\d{3})', train_id)
    if match:
        if match.group(1) == 'Reg':
            return match.group(1), match.group(2) + train_id[6]
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
    notify = False
    if historypath != "":
        history_file = open(historypath, "r")
    delays = {}
    early = {}
    contracts = {}
    recent_delays = UniqueDeque(maxlen=12)
    recent_lines = UniqueDeque(maxlen=200)
    removed_trains = UniqueDeque(maxlen=200)
    w = Window(stdscr)
    file = None

    try:
        while True:
            if history_file is not None:
                if file != history_file:
                    file = history_file
                    logging.info(f"Reading {file}")
                line = file.readline()
            else:
                if file != current_file:
                    file = current_file
                    logging.info(f"Reading {file}")
                line = file.readline()

            if line:
                parsed = parse_log_line(line)
                if parsed:
                    train_id, location, delay = parsed
                    if not recent_lines.appendleft((train_id, location, delay)):
                        continue
                    contract_type, contract_id = get_contract_id(train_id)
                    if contract_id not in contracts:
                        contracts[contract_id] = Contract(contract_id, contract_type, w)

                    contracts[contract_id].new_location_for_train(train_id, location, delay)

                    if delay > 60:
                        recent_delays.appendleft((train_id, location, delay))
                        delays[train_id] = (train_id, location, delay)  # Update the existing ID or add a new one
                        early.pop(train_id, None)
                        if delay > 120 and notify:
                            notification.notify(title=f'{train_id} delayed',
                                                message=f'{train_id} delayed at {location:16} by {delay}', timeout=10)
                    elif delay <= -120:
                        early[train_id] = (train_id, location, delay)
                        delays.pop(train_id, None)
                    else:
                        delays.pop(train_id, None)
                        early.pop(train_id, None)

                    for train in contracts[contract_id].purge_trains():
                        removed_trains.appendleft((train.tid, train.current_location(), train.current_delay()))
                        delays.pop(train_id, None)
                        early.pop(train_id, None)

                    if file != current_file:
                        continue
                    update_pads(contracts, delays, early, recent_delays, removed_trains, w)
                    if not w.has_popup():
                        w.redraw_all()
                else:
                    tid = parse_bad_platform(line)
                    if tid:
                        w.update_status(f"{tid}: Bad platform!")
            else:
                time.sleep(0.02)
                if history_file is not None:
                    w.update_status("Ending history parsing")
                    history_file.close()
                    history_file = None
                    update_pads(contracts, delays, early, recent_delays, removed_trains, w)
                    w.redraw_all()
                if file == current_file:
                    notify = True

            if handle_input(stdscr, w):
                break

    finally:
        current_file.close()
        if history_file is not None:
            history_file.close()


def update_pads(contracts, delays, early, recent_delays, removed_trains, w):
    w.update_delays(sorted(delays.values(), key=lambda x: x[2], reverse=True))
    w.update_early_trains(sorted(early.values(), key=lambda x: x[2], reverse=False))
    w.update_recent_delays(recent_delays)
    w.update_recent_departed(removed_trains)
    w.update_contracts([c for cid, c in sorted(contracts.items()) if not c.is_active()],
                       w.pads['inactive_contract'])
    w.update_contracts([c for cid, c in sorted(contracts.items()) if c.is_active()],
                       w.pads['active_contract'])


def handle_input(stdscr, w):
    terminate = False
    ch = stdscr.getch()
    if ch == ord('q'):  # Exit loop if 'q' is pressed
        if w.has_popup():
            w.destroy_popup()
            w.redraw_all()
        else:
            terminate = True
    elif ch == ord('w'):
        w.pads['active_contract'].update_displaypos(Pad.ScrollMode.LINE_UP)
    elif ch == ord('s'):
        w.pads['active_contract'].update_displaypos(Pad.ScrollMode.LINE_DOWN)
    elif ch == ord('e'):
        w.pads['inactive_contract'].update_displaypos(Pad.ScrollMode.LINE_UP)
    elif ch == ord('d'):
        w.pads['inactive_contract'].update_displaypos(Pad.ScrollMode.LINE_DOWN)
    elif ch == ord('r'):
        w.pads['active_contract'].set_selection(-1)
    elif ch == ord('f'):
        w.pads['active_contract'].set_selection(+1)
    elif ch == ord('t'):
        w.pads['inactive_contract'].set_selection(-1)
    elif ch == ord('g'):
        w.pads['inactive_contract'].set_selection(+1)
    elif ch == ord('x'):
        ref = w.pads['active_contract'].get_selection_reference()
        if isinstance(ref, Contract):
            title, contents = ref.make_detail_view()
            w.detail_view(title, contents)
    elif ch == ord('z'):
        ref = w.pads['inactive_contract'].get_selection_reference()
        if isinstance(ref, Contract):
            title, contents = ref.make_detail_view()
            w.detail_view(title, contents)
    elif ch == curses.KEY_PPAGE:
        w.pads['active_contract'].update_displaypos(Pad.ScrollMode.PAGE_UP)
    elif ch == curses.KEY_NPAGE:
        w.pads['active_contract'].update_displaypos(Pad.ScrollMode.PAGE_DOWN)
    elif ch == curses.KEY_RESIZE:
        w.resize(stdscr)
    return terminate


logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage: python monitor_log.py <log file path>")
        sys.exit(1)

    filepath = sys.argv[1]
    if len(sys.argv) == 3:
        history_path = sys.argv[2]
    else:
        history_path = ""
    curses.wrapper(monitor_log, filepath, history_path)
