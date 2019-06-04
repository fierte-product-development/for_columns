import markdown
import pathlib


parentpath = pathlib.Path(__file__).parent
mdpath = parentpath.joinpath('column.md')

str_io = mdpath.open(mode='r', encoding='utf-8')

md = markdown.Markdown()
html = md.convert(str_io.read())

htmlpath = parentpath.joinpath('new.html')
str_io = htmlpath.open(mode='w', encoding='utf-8_sig')
str_io.write(html)
