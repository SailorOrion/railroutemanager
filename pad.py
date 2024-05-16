import curses
import logging

from collections import namedtuple

from enum import Enum
from math import ceil

Padsize = namedtuple("Padsize",["start_row", "start_column", "rows", "columns"])

class Pad:
    class ScrollMode(Enum):
        LINE_UP   = 0
        LINE_DOWN = 1
        PAGE_UP   = 2
        PAGE_DOWN = 3

    _lines        = 0
    _displayfirst = 0

    def __init__(self, pad_height, pad_width, description, padsize, color = True):
        self._padsize = padsize
        self._desc = description

        if color:
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
           scrollbar_pos = int(self._displayfirst / (self._lines - self.contentheight()) * (self.contentheight() - scrollbar_height))
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

    def draw(self):
        self._borderwin.box()
        self._borderwin.addstr(0, 2, self._desc, curses.A_REVERSE)
        self._borderwin.refresh()
        d = self.draw_scrollbar()
        self._pad.refresh(self._displayfirst, 0, self._top + 1, self._left + 1, self._bottom - 2 , self._right - 3 - d)


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
        self.draw()

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
