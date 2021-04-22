import itertools as it
import os
import sys
import contextlib


fmap = lambda f, xs: (y for ys in xs for y in f(ys))

noexcept = contextlib.suppress


def walk_pruned(dir_: str):
  '''Prune directory contents using heuristics.'''
  skipwalk = lambda f: any(f.startswith(x) for x in ('__', '.'))
  for root, dirs, files in os.walk(dir_):
    files = [f for f in files if not skipwalk(f)]
    dirs[:] = [d for d in dirs if not skipwalk(d)]
    yield from map(lambda f: f'{root}/{f}', files)


# NOTE(tk) ncurses and piped input. google 'use ncurses with pipe "python"'
# option 1:
  # copy parent's stdin from shell e.g. `$ ls | python fuzzyselect.py 3<&0`
  # then in python call `os.dup2(3, 0)` before opening curses
# cf. https://stackoverflow.com/questions/65978574/how-can-i-use-python-curses-with-stdin
# cf. https://stackoverflow.com/questions/53696818/how-to-i-make-python-curses-application-pipeline-friendly
@contextlib.contextmanager
def new_tty():
  # NOTE(tk) not sure how hacky this is

  oldstdin = os.dup(0)
  oldstdout = os.dup(1)
  terminalr = open('/dev/tty')
  terminalw = open('/dev/tty', 'w')
  os.dup2(terminalr.fileno(), 0)
  os.dup2(terminalw.fileno(), 1)

  yield

  os.dup2(oldstdin, 0)
  os.dup2(oldstdout, 1)

