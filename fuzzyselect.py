import itertools as it
import os
import curses
import uiutils


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


class ListRenderer:
  def __init__(self, items, stdscr):
    self.items = items
    self.stdscr = stdscr
    self.longest = max(map(len, items))

  def __call__(self, active, chosen):
    H, W = self.stdscr.getmaxyx()

    H = min(H, len(self.items) + 2)
    W = min(W, self.longest)

    items_shown = H - 2
    start_ix = max(0, chosen - items_shown + 1)
    stop_ix = start_ix + items_shown

    for i in range(2, H):
      self.stdscr.addstr(i, 1, ' ' * W)

    items_shown = it.islice(active, start_ix, stop_ix)
    for i, item in enumerate(items_shown, start=2):
      self.stdscr.addstr(i, 1, item)

    if chosen < len(active):
      self.stdscr.addstr(min(H - 1, chosen + 2), 1, active[chosen], curses.A_REVERSE)


class Input:
  def __init__(self, stdscr, pos=1):
    self.stdscr = stdscr
    self.pos = pos
    self.state = ''

  def __call__(self):
    s = self.state
    c = self.stdscr.getch(self.pos, len(s) + 1)
    status = None
    if uiutils.is_key(curses.KEY_BACKSPACE, c):
      s = s[:-1]
      self.stdscr.addstr(self.pos, len(s) + 1, ' ')
    elif any(uiutils.is_key(k, c) for k in (
        curses.KEY_DOWN, curses.KEY_UP, curses.KEY_ENTER)):
      status = c
    else:
      s += chr(c)
    self.stdscr.addstr(1, 1, s)
    self.state = s
    return self.state, status


def filter_term(stdscr, items: list):
  renderer = ListRenderer(items, stdscr)
  renderer(items, 0)

  items = ListOption(items, [renderer])
  in_ = Input(stdscr)

  curses.noecho()
  while True:
    s, status = in_()
    items.apply(s)
    if uiutils.is_key(curses.KEY_ENTER, status):
      return items.get()
    elif status is not None:
      items.handle(status)
    stdscr.refresh()


if __name__ == '__main__':
  import sys
  dir_ = sys.argv[1] if len(sys.argv) > 1 else '.'
  args = os.listdir(os.path.expanduser(dir_))
  result = curses.wrapper(filter_term, args)
  print(result)

