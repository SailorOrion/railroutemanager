import curses
import logging

from collections import namedtuple

from enum import Enum
from math import ceil

PadSize = namedtuple("PadSize", ["start_row", "start_column", "rows", "columns"])


class Pad:
    _max_y = None
    _max_x = None
    _num_rows = None
    _num_columns = None

    class ScrollMode(Enum):
        LINE_UP = 0
        LINE_DOWN = 1
        PAGE_UP = 2
        PAGE_DOWN = 3

    @classmethod
    def set_size_params(cls, max_y, max_x, num_rows, num_columns):
        cls._max_y = max_y
        cls._max_x = max_x
        cls._num_rows = num_rows
        cls._num_columns = num_columns
        curses.update_lines_cols()
        curses.resizeterm(curses.LINES, curses.COLS)
        logging.info(f'Max Y: {cls._max_y}, Max X: {cls._max_x},'
                     f'Num Rows: {cls._num_rows}, Num Columns: {cls._num_columns},'
                     f'{curses.COLS}, {curses.LINES}')

    def __init__(self, pad_height, pad_width, description, pad_size, color=True):
        self._top = None
        self._bottom = None
        self._left = None
        self._right = None
        self._borderwin = None

        self._display_first = 0
        self._selected = -1
        self._pad_size = pad_size
        self._desc = description
        self._contents = {}

        if color:
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)

        self._pad = curses.newpad(pad_height, pad_width)

    def resize(self):
        self._top = int(self._max_y * self._pad_size.start_row / self._num_rows)
        self._bottom = int((self._max_y * self._pad_size.rows + self._max_y * self._pad_size.start_row) / self._num_rows)

        self._left = int(self._max_x * self._pad_size.start_column / self._num_columns)
        self._right = int((self._max_x * self._pad_size.columns + self._max_x * self._pad_size.start_column) / self._num_columns)
        self.log_info(f'Resized pad to {self._top}, {self._bottom}, {self._left}, {self._right}')
        if self._right > curses.COLS or self._bottom > curses.LINES:
            raise ValueError

    def lines(self):
        if not self._contents.keys():
            return 0
        temp = max(self._contents.keys()) - min(self._contents.keys())
        return temp

    def draw_scrollbar(self):
        # Calculate scrollbar slider properties
        if self.lines() > self.content_height():
            scrollbar_height = max(ceil((self.content_height() / self.lines()) * self.content_height()), 1)
            scrollbar_pos = int(
                self._display_first / (self.lines() - self.content_height()) * (self.content_height() - scrollbar_height))
        else:
            for y in range(self.content_height()):
                self._borderwin.addch(y + 1, self.width() - 2, ' ')
            return 0

        # Draw the scrollbar
        for y in range(self.content_height()):
            if scrollbar_pos <= y < scrollbar_pos + scrollbar_height:
                self._borderwin.addch(y + 1, self.width() - 2, curses.ACS_CKBOARD)
            else:
                self._borderwin.addch(y + 1, self.width() - 2, ' ')

        return 1

    def update_pad(self):
        for y_pos, contents in self._contents.items():
            for x_pos, line, color_pair in contents['elements']:
                if color_pair is None:
                    if y_pos == self._selected:
                        self._pad.addstr(y_pos, x_pos, line, curses.A_REVERSE)
                    else:
                        self._pad.addstr(y_pos, x_pos, line)
                else:
                    self._pad.addstr(y_pos, x_pos, line, color_pair)

    def update_draw(self):
        self.update_pad()
        self.draw()

    def log_info(self, string):
        logging.info(f'{self._desc[:16]} {string}')

    def adjust_view(self):
        if (self._selected < self._display_first) or (self._selected > self._display_first + self.content_height() - 1):
            self._display_first = max(0, self._selected - self.content_height() // 2)

    def adjust_selected(self):
        if (self._selected < self._display_first) or (self._selected > self._display_first + self.content_height()):
            self._selected = -1

    def draw(self):
        self._borderwin = curses.newwin(self.height(), self.width(), self._top, self._left)
        self._borderwin.box()
        self._borderwin.addstr(0, 2, ' ' + self._desc + ' ', curses.A_REVERSE)
        self._borderwin.refresh()

        d = self.draw_scrollbar()

        self._pad.refresh(self._display_first, 0, self._top + 1, self._left + 1, self._bottom - 2, self._right - 2 - d)

    def set_selection(self, direction):
        if self._selected == -1:
            match direction:
                case 1:
                    self._selected = self._display_first
                case -1:
                    self._selected = self._display_first + self.content_height() - 1
                case _:
                    raise ValueError
        else:
            self._selected = max(0, min(self._selected + direction, self.lines()))
        self.adjust_view()
        self.update_draw()

    def get_selection(self):
        ref = self._contents[self._selected]['reference']
        return ref

    def get_selection_reference(self):
        if self._selected < 0:
            return None
        return self._contents[self._selected]['reference']

    def update_displaypos(self, mode):
        match mode:
            case self.ScrollMode.LINE_UP:
                self._display_first -= 1
            case self.ScrollMode.LINE_DOWN:
                self._display_first += 1
            case self.ScrollMode.PAGE_UP:
                self._display_first -= self.height() // 2
            case self.ScrollMode.PAGE_DOWN:
                self._display_first += self.height() // 2
            case _:
                raise ValueError
        self._display_first = max(0, min(self._display_first, self.lines() - self.content_height()))
        self.adjust_selected()
        self.draw()

    def prepare(self):
        self._contents.clear()
        self._pad.erase()

    def addstr(self, y_pos, x_pos, line, ref=None, color_pair=None):
        if y_pos not in self._contents:
            self._contents[y_pos] = {}
        if 'elements' not in self._contents[y_pos]:
            self._contents[y_pos]['elements'] = list()
        self._contents[y_pos]['elements'].append((x_pos, line, color_pair))
        self._contents[y_pos]['reference'] = ref

    def height(self):
        return self._bottom - self._top

    def content_height(self):
        return self.height() - 2

    def width(self):
        return self._right - self._left
