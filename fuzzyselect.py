#!/usr/bin/python

'''Emulates fzf-like behavior.
My attempt at learning Python ncurses.
Example:
  $ python fuzzyselect.py -f .
  $ python fuzzyselect.py **/*py
  $ ls | python fuzzyselect.py
  $ vim (python fuzzyselect.py *py)
'''
import os
import curses
import itertools as it

import utils
from utils import uiutils
from utils import yx


L = utils.logcfg(__name__).disable()


def fuzzymatch_score(search_term_cased: str):
  search_term = search_term_cased.lower()
  def fuzzy_inner(test_against: str):
    last_match = -1
    iterm = 0
    score = 1
    for i, letter in enumerate(test_against.lower()):
      if iterm == len(search_term): break
      if letter == search_term[iterm]:
        score += 1.0 / (i - last_match)
        iterm += 1
        last_match = i
    return score * (iterm == len(search_term))
  return fuzzy_inner


class ListOption:
  def __init__(self, items, listeners=None):
    self.items = items
    self.listeners = listeners or []
    self.choice = 0

  def apply(self, filter_str: str):
    scored = zip(map(fuzzymatch_score(filter_str), self.items), self.items,)
    scored = filter(lambda score_item_tpl: score_item_tpl[0], scored)
    self.active = [str_ for _, str_ in sorted(scored, reverse=True)]
    if self.choice >= len(self.active):
      self.choice = 0
    self._notify(self.active, self.choice)
    return self.active

  def handle(self, key):
    if uiutils.is_key(curses.KEY_DOWN, key): self.choice = self.choice + 1
    elif uiutils.is_key(curses.KEY_UP, key): self.choice = self.choice - 1
    self.choice = (self.choice + len(self.active)) % len(self.active)
    self._notify(None, self.choice)
    return self.choice

  def get(self):
    return self.active[self.choice] if self.active else None

  def _notify(self, *a, **kw):
    for l in self.listeners:
      l(*a, **kw)


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

  def _blank(self, rows=None):
    blanking = ' ' * self.width
    for y in (rows or self.rows):
      self._display(y, self.x0, blanking)

  def _display(self, y, x, s, *a, **kw):
    s = str(s)
    y = self._guardy(y)
    x = self._guardx(x)
    w = self._guardw(len(s), x)
    return self.stdscr.addstr(y, x, s[:w], *a, **kw)


class ListRenderer(WidthAware):
  def __init__(self, stdscr, bounds):
    super().__init__(stdscr, bounds)
    self._cache = (None, None, [])

  def __call__(self, active: list, chosen_ix: int):
    old_start_ix, old_chosen_ix, old_active = self._cache
    start_ix = max(0, chosen_ix - self.height + 1)

    redraw_single = active is None and old_start_ix == start_ix
    active = old_active if active is None else active

    if redraw_single:
      y = self._guardy(old_chosen_ix + self.y0)
      self._blank([y]); self._display(y, self.x0, active[old_chosen_ix])
    else:
      self._blank()
      items_shown = it.islice(active, start_ix, start_ix + self.height)
      for y, item in enumerate(items_shown, start=self.y0):
        self._display(y, self.x0, item)

    if chosen_ix < len(active):  # make selection
      y = self._guardy(chosen_ix + self.y0)
      self._display(y, self.x0, active[chosen_ix], curses.A_REVERSE)

    self._cache = (start_ix, chosen_ix, active)


class Input(WidthAware):
  def __init__(self, stdscr, bounds):
    super().__init__(stdscr, bounds)
    self.state = ''

  def __iter__(self):
    while True:
      yield self()

  def _display(self, y, x, s, *a, **kw):
    w = self._guardw(len(s))
    return super()._display(y, x, s[-w:], *a, **kw)

  def _getchar(self):
    return self.stdscr.getch(self.y0, self._guardx(len(self.state) + 1))

  def __call__(self):
    c = self._getchar()
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
  renderer = ListRenderer(stdscr, bounds=(yx(2, 1), yx(Ym, Xm)))
  items = ListOption(items, listeners=[renderer])
  items.apply('')

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

  parser = argparse.ArgumentParser()
  parser.add_argument('vals', help='Values to fuzzymatch', nargs='*')
  parser.add_argument(
    '-f', '--files', help='valid files only', action='store_true', default=True)
  parser.add_argument(
    '-a', '--abs', help='expand paths', action='store_true', default=False)
  parser.add_argument('-l', '--limit', help='limit num entries', default=500)
  flags = parser.parse_args()

  args = flags.vals
  if not sys.stdin.isatty():  # has piped data
    args += [x.strip() for x in sys.stdin]

  if not args:  # if no args here, assume we want to walk current directory.
    args = utils.walk_pruned('.')

  if flags.files:  # only retain files
    if all(os.path.isdir(x) for x in args):
      args = utils.fmap(utils.walk_pruned, args)
    args = filter(os.path.isfile, args)

  if flags.abs:
    args = map(os.path.abspath, args)

  args = args if isinstance(args, list) else list(it.islice(args, flags.limit))
  with utils.new_tty():
    if (result := curses.wrapper(filter_ncurses_app, args)):
      print(result)

