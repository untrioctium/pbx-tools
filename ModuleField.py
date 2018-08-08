import PBXUtil
from copy import copy

class ModuleField():
	def __init__(self, desc = ""):
		self.description = desc
		self.value = None
		self.xpath_location = None

	def populate(self, pbx, val):
		ret = copy(self)
		ret.value = val
		ret.pbx = pbx
		return ret

	def populate_null(self):
		return copy(self)

	def __repr__(self):
		return str(self.value)

	def xpath(self, path):
		self.xpath_location = path
		return self

class IntField(ModuleField):
	def populate(self, pbx, val):
		if val == "": return ModuleField.populate_null(self)
		if val == "disabled": return ModuleField.populate(self, pbx, -666)
		return ModuleField.populate(self, pbx, int(val))

	def __repr__(self):
		if self.value == -666: return "Disabled"
		else: return str(self.value)

class StringField(ModuleField):
	def populate(self, pbx, val):
		if isinstance(val, (bytes, bytearray)):
			val = str(val, "utf-8")

		return ModuleField.populate(self, pbx, val)
	
	def __repr__(self):
		if self.value == None: return ""
		if len(self.value) == 0: return ""

		return ModuleField.__repr__(self)

class EnumField(ModuleField):
	def __init__(self, desc, enum):
		self.enum = enum
		ModuleField.__init__(self, desc)

	def __repr__(self):
		return self.enum[self.value]

class ListField(ModuleField):
	def __init__(self, sep, desc = ""):
		self.separator = sep
		ModuleField.__init__(self, desc)

	def populate(self, pbx, val):
		if isinstance(val, (bytes, bytearray)):
			val = str(val, "utf-8")
		return ModuleField.populate(self, pbx, val.split(self.separator))

	def __repr__(self):
		if self.value is None: return ""
		return " ".join(self.value)

class BooleanField(ModuleField):
	def __init__(self, desc = "", tpair = ("", "CHECKED")):
		self.tpair = tpair
		ModuleField.__init__(self, desc)

	def populate(self, pbx, val):
		return ModuleField.populate(self, pbx, val == self.tpair[1])

class ForeignKeyField(ModuleField):
	def __init__(self, desc, module, special = {}):
		self.module = module
		self.special = special
		ModuleField.__init__(self, desc)

	def populate(self, pbx, val):

		self.pbx = pbx
		return ModuleField.populate(self, pbx, val)

	def isref(self):
		return not self.value in self.special

	def deref(self):
		return self.pbx[self.module].get(self.value)

	def __repr__(self):
		if self.isref():
			try:
				dr = self.deref()
				return "[[#%s|%s]]" % (dr.uid(), str(dr))
			except: return "None"
		else:
			return self.special[self.value]

	def __getitem__(self, item):
		return self.deref()[item]

class ManyToManyField(ModuleField):
	def __init__(self, desc, module, key):
		self.module = module
		self.key = key
		ModuleField.__init__(self, desc)

	def populate(self, pbx, val):
		children = pbx[self.module].filter(**{self.key: val})
		return ModuleField.populate(self, pbx, children )


class DestinationField(ModuleField):

	def blackhole(self, dest):
		location = {
			"hangup": "Hangup",
			"congestion": "Congestion",
			"busy": "Busy",
			"zapateller": "Play SIT tone (Zapateller)",
			"musiconhold": "Put caller on hold forever",
			"ring": "Play ringtones to caller until they hang up"
		}.get(dest, "")

		if len(location): return "Terminate call: " + location
		return "Terminate call"

	def voicemail(self, dest):
		flag = { "b": "busy", "u": "unavail", "s": "no-msg", "i": "instruction-only" }[dest[0]]
		ext = int(dest[1:])
		return "Voicemail: %s (%s)" % ( str(self.pbx["Extension"].get(ext)), flag )

	def feature_code(self, dest):
		c = self.pbx["FeatureCode"].filter(customcode = dest)
		if len(c) == 0:
			c = self.pbx["FeatureCode"].filter(defaultcode = dest)

		return "Feature code: <%s> %s" % (dest, c[0]["description"])

	special_fields = {
		"app-blackhole,([a-z]+)": blackhole,
		"app-pbdirectory": lambda x: "Phonebook directory",
		"ext-local,vm([busi][0-9]+)": voicemail,
		"ext-featurecodes,(\**[0-9]+)": feature_code,
	}

	def __init__(self, desc = ""):
		ModuleField.__init__(self, desc)

	def populate(self, pbx, val):
		return ModuleField.populate(self, pbx, val)

	def __repr__(self):
		match = PBXUtil.matching_regex( self.special_fields, self.value )
		if match is not None:
			if isinstance(match["key"], str): return match["match"]
			return match["key"](self, match["match"])

		d = PBXUtil.dest(self.pbx, self.value)
		if self.value == None or self.value == "": return ""
		if isinstance(d, str) or d is None: return OutputFormatter.wiki_error("ERROR: Unknown destination '%s'" % self.value)

		link_format = "[[#%s|%s: %s]]"

		return link_format % (d.uid(), d.item_name, str(d))
