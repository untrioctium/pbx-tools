#!/usr/bin/python
import logging
import sys
from PBX import PBX, PBXError
from getpass import getpass
from jinja2 import Environment, FileSystemLoader
from PBXUtil import dump_error

username = input("Enter PBX username:")
password = getpass("Enter PBX password:")

try:
	pbx = PBX(sys.argv[1])

	def echo(str): print(str)
	pbx.set_update_targets(echo, echo, echo)

	pbx.connect_web_config(username, password)
	pbx.connect_sql(username, password)

	j2_env = Environment(loader=FileSystemLoader("./templates"), trim_blocks=True)
	j2_env.filters["capfirst"] = lambda s: s[0].upper() + s[1:]

	def j2_debug(s): print(s)
	j2_env.filters["debug"] = j2_debug

	to_render = []
	for m in pbx:
		if m.render_template is not None and len(m) > 0: to_render.append(m)

	f = open("wiki.txt", "w")
	out = ""
	for m in to_render:
		out += j2_env.get_template("wiki.tpl").render(m=m, nl="\n").replace("\t", "")

	pbx.update_status("Writing output")
	f.write(out)

finally:
	pbx.close()
