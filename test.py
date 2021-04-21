import itertools as it
import os
import curses

from curses import wrapper
from curses import textpad


def emacs(stdscr):
  editwin = curses.newwin(5, 30, 2, 1)
  box = textpad.Textbox(editwin)
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


def filter_(stdscr):
  # TODO change active
  items = os.listdir('.')
  chosen = 0
  maxl = 0
  for i, item in enumerate(items, start=2):
    attr = curses.A_STANDOUT if i == chosen + 2 else 0
    stdscr.addstr(i, 1, item)
    maxl = max(maxl, len(item))

  curses.noecho()
  s = ''
  while True:
    c = stdscr.getch(1, len(s) + 1)
    if c == 127: # backspace
      s = s[:-1]
      stdscr.addstr(1, len(s) + 1, ' ')
    elif c == 10:  # enter
      if s == 'q': break
      return next(filter(fuzzymatch(s), items), None)
    else:
      s += chr(c)
    stdscr.addstr(1, 1, s)
    for i in range(2, len(items) + 2):
      stdscr.addstr(i, 1, ' ' * maxl)
    for i, item in enumerate(filter(fuzzymatch(s), items), start=2):
      attr = curses.A_STANDOUT if i == chosen + 2 else 0
      stdscr.addstr(i, 1, item, attr)
    stdscr.refresh()


def filter_str(stdscr):
  items = os.listdir('.')
  maxl = 0
  for i, item in enumerate(items, start=2):
    stdscr.addstr(i, 1, item)
    maxl = max(maxl, len(item))

  curses.echo()
  s = ''
  while True:
    stdscr.addstr(1, 1, ' ' * len(s))
    s = stdscr.getstr(1, 1).decode()
    if s == 'q':
      break
    for i in range(2, len(items) + 2):
      stdscr.addstr(i, 1, ' ' * maxl)
    for i, item in enumerate(filter(fuzzymatch(s), items), start=2):
      stdscr.addstr(i, 1, item)
    stdscr.refresh()


def main(stdscr):
  # This raises ZeroDivisionError when i == 10.
  for i in range(5):
    stdscr.clear()
    c = stdscr.getch()
    v = i - 10
    if c == ord('a'):
      stdscr.addstr(0, 0, 'a')
    else:
      stdscr.addstr(0, 0, '10 divided by {} is {}'.format(v, 10/v))

    stdscr.refresh()
    stdscr.getkey()


result = wrapper(filter_)
print(result)

