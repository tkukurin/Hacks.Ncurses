import itertools as it
import os
import curses
import utils

def emacs(stdscr):
  editwin = curses.newwin(5, 30, 2, 1)
  box = curses.textpad.Textbox(editwin)
  box.edit()
  stdscr.addstr(2, 1, box.gather())
  stdscr.refresh()

  stdscr.getkey()


def fuzzymatch(search_term_cased):
  search_term = search_term_cased.lower()
  def fuzzy_inner(test_against):
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
    return self.active[self.choice]


class ListRenderer:
  def __init__(self, items, stdscr):
    self.items = items
    self.stdscr = stdscr
    self.longest = max(map(len, items))

  def __call__(self, active, chosen):
    for i in range(2, len(self.items) + 2):
      self.stdscr.addstr(i, 1, ' ' * self.longest)
    for i, item in enumerate(active, start=2):
      attr = curses.A_STANDOUT if i == chosen + 2 else 0
      self.stdscr.addstr(i, 1, item, attr)


class Input:
  def __init__(self, stdscr, pos=1):
    self.stdscr = stdscr
    self.pos = pos
    self.state = ''

  def __call__(self):
    s = self.state
    c = self.stdscr.getch(self.pos, len(s) + 1)
    status = None
    if utils.is_key(curses.KEY_BACKSPACE, c):
      s = s[:-1]
      self.stdscr.addstr(self.pos, len(s) + 1, ' ')
    elif c in (curses.KEY_DOWN, curses.KEY_UP) or utils.is_key(curses.KEY_ENTER, c):
      status = c
    else:
      s += chr(c)
    self.stdscr.addstr(1, 1, s)
    self.state = s
    return self.state, status


def filter_(stdscr):
  items = os.listdir('.')
  renderer = ListRenderer(items, stdscr)
  renderer(items, 0)

  items = ListOption(items, [renderer])
  in_ = Input(stdscr)

  curses.noecho()
  while True:
    s, status = in_()
    items.apply(s)
    if utils.is_key(curses.KEY_ENTER, status):
      return items.get()
    elif status is not None:
      items.handle(status)
    stdscr.refresh()


result = curses.wrapper(filter_)
print(result)

