
import curses

# cf. https://stackoverflow.com/questions/32252733/interpreting-enter-keypress-in-stdscr-curses-module-in-python
ks_enter = [curses.KEY_ENTER, 10, 13]
ks_backspace = [curses.KEY_BACKSPACE, 127]
ks = {vs[0]:vs for k, vs in locals().items() if k.startswith('ks')}

is_key = lambda k, x: x in ks[k]

