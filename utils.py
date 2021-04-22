import os
import sys
from contextlib import contextmanager


# NOTE(tk) ncurses and piped input. google 'use ncurses with pipe "python"'
# option 1:
  # copy parent's stdin from shell e.g. `$ ls | python fuzzyselect.py 3<&0`
  # then in python call `os.dup2(3, 0)` before opening curses
# cf. https://stackoverflow.com/questions/65978574/how-can-i-use-python-curses-with-stdin
# cf. https://stackoverflow.com/questions/53696818/how-to-i-make-python-curses-application-pipeline-friendly


@contextmanager
def new_tty():
  # NOTE(tk) not sure how hacky this is

  oldstdin = os.dup(0)
  oldstdout = os.dup(1)
  terminalr = open('/dev/tty')
  terminalw = open('/dev/tty', 'w')
  os.dup2(terminalr.fileno(), 0)
  os.dup2(terminalw.fileno(), 1)

  yield os.fdopen(oldstdin), os.fdopen(oldstdout)

  os.dup2(oldstdin, 0)
  os.dup2(oldstdout, 1)

