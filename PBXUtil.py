import re
from collections import OrderedDict as ODict

def sanitary_format( fmt, **kwargs ):
	return fmt.format( **dict([(k, re.sub(r"[^\*_\w,]+", "", v)) for k,v in kwargs.items()]) )

def dump_error( gl, loc, tb, exception ):
	import pprint
	import traceback
	pp = pprint.PrettyPrinter()
	out = "EXCEPTION:\n" + "-"*80 + "\n"
	out += traceback.format_exc(exception)
	out += "\nLOCALS:\n" + "-"*80 + "\n"
	out += pp.pformat(loc) + "\nGLOBALS:\n" + "-"*80 + "\n"
	out += pp.pformat(gl)
	return out

def matching_regex( regexes, s ):
	for r, n in regexes.items():
		ret = re.findall(r, s)
		if len(ret): return {"key": n, "match": ret[0]}

	return None

def module(pbx, name):
	if name in module.registry:
		return module.registry[name](pbx)
	return None

def dest(pbx, name):
	match = matching_regex( module.regex_registry, name )
	if match is not None:
		return module.registry[match["key"]](pbx).get(match["match"])
	return name
