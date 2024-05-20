import curses
import logging
import traceback

from collections import namedtuple, defaultdict

from enum import Enum
from math import ceil

Padsize = namedtuple("Padsize", ["start_row", "start_column", "rows", "columns"])


class Pad:
    class ScrollMode(Enum):
        LINE_UP = 0
        LINE_DOWN = 1
        PAGE_UP = 2
        PAGE_DOWN = 3


    def __init__(self, pad_height, pad_width, description, padsize, color=True):
        self._displayfirst = 0
        self._selected = -1
        self._verbose = 0
        self._padsize = padsize
        self._desc = description
        self.__contents = {}
        self._dirty = True

        if color:
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)

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

    def lines(self):
        if not self.__contents.keys():
            return 0
        temp = max(self.__contents.keys()) - min(self.__contents.keys())
        return temp

    def draw_scrollbar(self):
        # Calculate scrollbar slider properties
        if self.lines() > self.contentheight():
            scrollbar_height = max(ceil((self.contentheight() / self.lines()) * self.contentheight()), 1)
            scrollbar_pos = int(self._displayfirst / (self.lines() - self.contentheight()) * (self.contentheight() - scrollbar_height))
        else:
            for y in range(self.contentheight()):
                self._borderwin.addch(y + 1, self.width() - 2, ' ')
            return 0

        # Draw the scrollbar
        for y in range(self.contentheight()):
            if scrollbar_pos <= y < scrollbar_pos + scrollbar_height:
                self._borderwin.addch(y + 1, self.width() - 2, curses.ACS_CKBOARD)
            else:
                self._borderwin.addch(y + 1, self.width() - 2, ' ')

        return 1

    def update_pad(self):
        dirty = True
        for y_pos, contents in self.__contents.items():
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

    def loginfo(self, string):
        if not self._verbose:
            return
        logging.info(f'{self._desc[:16]} {string}')

    def adjust_view(self):
        if (self._selected < self._displayfirst) or (self._selected > self._displayfirst + self.contentheight() - 1):
            self._displayfirst = max(0, self._selected - self.contentheight() // 2)

    def adjust_selected(self):
        if (self._selected < self._displayfirst) or (self._selected > self._displayfirst + self.contentheight()):
            self._selected = -1

    def draw(self):
        self._borderwin.box()
        self._borderwin.addstr(0, 2, self._desc, curses.A_REVERSE)
        self._borderwin.refresh()
        d = self.draw_scrollbar()
        self._pad.refresh(self._displayfirst, 0, self._top + 1, self._left + 1, self._bottom - 2, self._right - 2 - d)

    def set_selection(self, direction):
        if self._selected == -1:
            match direction:
                case 1:
                    self._selected = self._displayfirst
                case -1:
                    self._selected = self._displayfirst + self.contentheight() - 1
                case _:
                    raise ValueError
        else:
            self._selected = max(0, min(self._selected + direction, self.lines()))
        self.adjust_view()
        self.update_draw()

    def get_selection(self):
        ref = self.__contents[self._selected]['reference']
        return ref

    def get_selection_reference(self):
        if self._selected < 0:
            return None
        return self.__contents[self._selected]['reference']

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
        self._displayfirst = max(0, min(self._displayfirst, self.lines() - self.contentheight()))
        self.adjust_selected()
        self.draw()

    def prepare(self):
        self.__contents.clear()
        self._pad.erase()

    def addstr(self, y_pos, x_pos, line, ref=None, color_pair=None):
        if not y_pos in self.__contents:
            self.__contents[y_pos] = {}
        if not 'elements' in self.__contents[y_pos]:
            self.__contents[y_pos]['elements'] = list()
        self.__contents[y_pos]['elements'].append((x_pos, line, color_pair))
        self.__contents[y_pos]['reference'] = ref

    def height(self):
        return self._bottom - self._top

    def contentheight(self):
        return self.height() - 2

    def width(self):
        return self._right - self._left
