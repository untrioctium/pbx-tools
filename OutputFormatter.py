def wiki_error(s):
	return '<span style="color:red;background:yellow"><b>%s</b></span>' % s

def nice_cap(s):
	 return s[0].upper() + s[1:]

def wiki_format( module ):
	print ("Processing %s" % module.description)

	children = module.all()
	if len(children) == 0:
		return ""

	output = "== %s ==\n" % module.description

	line_format = "* {description}: '''{value}'''\n"

	for i in children:
		title = "%s: %s" % (i.item_name, i)
		print("--Processing %s" % title)
		url = i.config_url()
		if url is not None: title = "[%s %s]" % (url, title)

		anchor = "<div id='%s'>%s</div>" % (i.uid(), title)
		output += "=== %s ===\n" % anchor
		for k, v in i:
			print("---Processing %s" % k)
			if isinstance(v.value, list) and len(v.value) > 0 and not isinstance(v.value[0], str ):
				output += "* " + nice_cap(v.description) + ":\n"
				for c in v.value:
					output += "** " + str(c) + "\n"
			elif isinstance(v.value, list) and len(v.value) == 0:
				output += "* " + nice_cap(v.description) + ": <span style='color:#AAAAAA'>(none)</span>\n"
			elif len(v.description):
				o = str(v)
				if len(o) == 0: o = "<span style='color:#AAAAAA'>(empty)</span>"
				output += line_format.format(description = nice_cap(v.description), value = o)

	return output.rstrip()

def table_format( module ):
	children = module.all()
	if len(children) == 0:
		return ""

	output = "== %s ==\n" % module.description
	output += '{| border="1" cellspacing="0" cellpadding="2"\n'

	for k, f in module.fields.iteritems():
		if len(f.description):
			output += "!%s\n" % nice_cap(f.description)

	output += "|----\n"

	for c in children:
		for k, f in c:
			if len(f.description):
				output += "|%s\n" % f
		output += "|----\n"

	output += "|}"
	return output
