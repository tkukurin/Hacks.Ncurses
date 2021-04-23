#!/usr/bin/python

'''Emulates fzf-like behavior.
My attempt at learning Python ncurses.
Example:
  $ python fuzzyselect.py -f .
  $ python fuzzyselect.py **/*py
  $ ls | python fuzzyselect.py
  $ vim (python fuzzyselect.py *py)
'''
import itertools as it
import os
import curses

from utils import uiutils
from utils import yx


def fuzzymatch(search_term_cased: str):
  search_term = search_term_cased.lower()
  def fuzzy_inner(test_against: str):
    iterm = 0
    for letter in test_against.lower():
      if iterm == len(search_term): break
      iterm += (letter == search_term[iterm])
    return iterm == len(search_term)
  return fuzzy_inner


class ListOption:
  def __init__(self, items, listeners=None):
    self.items = items
    self.listeners = listeners or []
    self.choice = 0

  def apply(self, filter_str: str):
    self.active = list(filter(fuzzymatch(filter_str), self.items))
    if self.choice >= len(self.active):
      self.choice = 0
    [l(self.active, self.choice) for l in self.listeners]
    return self.active

  def handle(self, dir_):
    if dir_ == curses.KEY_DOWN: self.choice = self.choice + 1
    if dir_ == curses.KEY_UP: self.choice = self.choice - 1
    self.choice = (self.choice + len(self.active)) % len(self.active)
    [l(self.active, self.choice) for l in self.listeners]
    return self.choice

  def get(self):
    return self.active[self.choice] if self.active else None


class WidthAware:
  def __init__(self, stdscr, bounds):
    self.stdscr = stdscr
    # indices are assumed inclusive.
    (self.y0, self.x0), (self.y1, self.x1) = bounds

  @property
  def width(self): return self.x1 - self.x0 + 1

  @property
  def height(self): return self.y1 - self.y0 + 1

  @property
  def rows(self): return range(self.y0, self.y1 + 1)

  def _guardx(self, x):
    return max(self.x0, min(self.x1, x))

  def _guardy(self, y):
    return max(self.y0, min(self.y1, y))

  def _guardw(self, w, x=None):
    x = x or self.x0
    return max(0, min(self.x1 - x, w))

  def _guardh(self, h, y=None):
    y = y or self.y0
    return max(0, min(self.y1 - y, h))

  def _display(self, y, x, s, *a, **kw):
    y = self._guardy(y)
    x = self._guardx(x)
    w = self._guardw(len(s), x)
    return self.stdscr.addstr(y, x, s[:w], *a, **kw)


class ListRenderer(WidthAware):
  def __init__(self, items, stdscr, bounds):
    super().__init__(stdscr, bounds)
    self.items = items

  def __call__(self, active: list, chosen_ix: int):
    blanking = ' ' * self.width
    [self._display(y, self.x0, blanking) for y in self.rows]

    items_shown = self.height
    start_ix = max(0, chosen_ix - items_shown + 1)
    stop_ix = start_ix + items_shown
    row_item = enumerate(it.islice(active, start_ix, stop_ix), start=self.y0)
    [self._display(y, self.x0, item) for y, item in row_item]

    if chosen_ix < len(active):  # make selection
      y = self._guardy(chosen_ix + 2)
      self._display(y, self.x0, active[chosen_ix], curses.A_REVERSE)


class Input(WidthAware):
  def __init__(self, stdscr, bounds):
    super().__init__(stdscr, bounds)
    self.stdscr = stdscr
    self.state = ''

  def __iter__(self):
    while True:
      yield self()

  def _display(self, y, x, s, *a, **kw):
    w = self._guardw(len(s))
    return super()._display(y, x, s[-w:], *a, **kw)

  def __call__(self):
    c = self.stdscr.getch(self.y0, self._guardx(len(self.state) + 1))
    status = None
    if uiutils.is_key(curses.KEY_BACKSPACE, c):
      self.state = self.state[:-1]
      self._display(self.y0, len(self.state) + 1, ' ')
    elif any(uiutils.is_key(k, c) for k in (
        curses.KEY_DOWN, curses.KEY_UP, curses.KEY_ENTER)):
      status = c
    else:
      with utils.noexcept(Exception):
        if (cstr := chr(c)).isprintable():
          self.state += cstr
    self._display(self.y0, self.x0, self.state)
    return self.state, status


def filter_ncurses_app(stdscr, items: list):
  Ym, Xm = map(lambda x: x-1, stdscr.getmaxyx())
  renderer = ListRenderer(items, stdscr, bounds=(yx(2, 1), yx(Ym, Xm)))
  renderer(items, 0)

  items = ListOption(items, [renderer])

  curses.noecho()
  for s, status in Input(stdscr, bounds=(yx(1, 1), yx(1, Xm))):
    items.apply(s)
    if uiutils.is_key(curses.KEY_ENTER, status):
      return items.get()
    elif status is not None:
      items.handle(status)
    stdscr.refresh()


if __name__ == '__main__':
  import sys
  import argparse
  import utils

  parser = argparse.ArgumentParser()
  parser.add_argument('vals', help='Values to fuzzymatch', nargs='*')
  parser.add_argument(
    '-f', '--files', help='valid files only', action='store_true', default=True)
  flags = parser.parse_args()

  args = flags.vals
  if not sys.stdin.isatty():  # has piped data
    args += [x.strip() for x in sys.stdin]

  if not args:  # if no args here, assume we want to walk current directory.
    args = map(os.path.abspath, utils.walk_pruned('.'))

  if flags.files:  # only reatin files
    if all(os.path.isdir(x) for x in args):
      args = utils.fmap(utils.walk_pruned, args)
    args = map(os.path.abspath, args)
    args = filter(os.path.isfile, args)

  args = args if isinstance(args, list) else list(it.islice(args, 0, 500))
  with utils.new_tty():
    result = curses.wrapper(filter_ncurses_app, args)

  print(result)

