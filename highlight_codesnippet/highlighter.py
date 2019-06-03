import pathlib

from pygments import highlight
from pygments.lexers import Python3Lexer
from pygments.formatters import HtmlFormatter


parent_path = pathlib.Path(__file__).parent
script_path = parent_path.joinpath('main.py')
str_io = script_path.open(mode='r', encoding='utf-8')

print(highlight(str_io.read(), Python3Lexer(), HtmlFormatter()))
