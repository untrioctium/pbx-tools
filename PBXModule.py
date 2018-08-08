import re
from ModuleField import *
from PBXUtil import matching_regex, sanitary_format, module, dest
from collections import OrderedDict as ODict

class ModuleMeta(type):
	def __init__(cls, name, bases, dict):
		if not hasattr(module, "registry"): module.registry = ODict()
		if not hasattr(module, "regex_registry"): module.regex_registry = {}

		if name != "Module":
			print("Loading module: %s" % cls.__name__)
			for k,v in cls.fields.items():
				if v.xpath_location is not None:
					cls._has_xpath = True
					break

			module.registry[cls.__name__] = cls
			cls.name = cls.__name__
			if hasattr(cls, 'dest_regex'):
				module.regex_registry[cls.dest_regex] = name

		super(ModuleMeta, cls).__init__(name, bases, dict)

class Module(metaclass=ModuleMeta):

	_has_xpath = False

	def __init__(self, pbx):
		self._instanced_fields = ODict()
		self._pbx = pbx
		self._is_instance = False

	def is_object_instance(self):
		return self._is_instance

	@classmethod
	def from_row(cls, pbx, row):
		obj = cls(pbx)
		obj._is_instance = True

		if row is None: return None

		if cls._has_xpath:
			page = pbx.get_config_from_param(**cls.config_param(row))

		for name, info in cls.fields.items():
			if info.xpath_location is not None:
				try:
					row[name] = page.xpath(info.xpath_location)[0]
				except:
					row[name] = None

			if not name in row and isinstance(info, ManyToManyField):
				row[name] = row[obj.pk_field]
			if not name in row or row[name] == None:
				obj._instanced_fields[name] = info.populate_null()
			else:
				obj._instanced_fields[name] = info.populate(pbx, row[name])
		return obj

	def get(self, pk):
		cur = self._pbx.get_sql_cursor()
		q = sanitary_format("SELECT * FROM {table} WHERE {pk}=%s;",
			table = self.db_table, pk = self.pk_field)

		cur.execute(q, [pk])

		row = cur.fetchone()
		return self.from_row(self._pbx, row)

	def all(self):
		self._pbx.update_status("Processing module: " + self.description)
		cur = self._pbx.get_sql_cursor()

		order = self.pk_field
		if hasattr(self, 'ordering'):
			order = self.ordering

		q = sanitary_format("SELECT * FROM {table} ORDER BY {order};",
			table = self.db_table, order = order)

		cur.execute(q)

		result = []
		for row in cur.fetchall():
			obj = self.from_row(self._pbx, row)
			result.append(obj)
			self._pbx.update_subtask("\tProcessed: " + str(obj))

		return result

	def __len__(self):
		try:
			cur = self._pbx.get_sql_cursor()
			q = sanitary_format("SELECT COUNT(*) as COUNT FROM {table};", table = self.db_table)
			cur.execute(q)
			return cur.fetchone()["COUNT"]
		except:
			return 0

	@staticmethod
	def _construct_ordering(order_str):
		fields = order_str.split(",")
		for i, f in enumerate(fields):
			if f[-1] != "+" and f[-1] != "-":
				fields[i] = sanitary_format("{field} ASC", field = f)
			elif f[-1] == "-":
				fields[i] = sanitary_format("{field} DESC", field = f[:-1])
			elif f[-1] == "+":
				fields[i] = sanitary_format("{field} ASC", field = f[:-1])

		return ", ".join(fields)

	def filter(self, **kwargs):
		cur = self._pbx.get_sql_cursor()
		operands = { "eq": "=", "neq": "<>", "lt": "<", "lte": "<=", "gt": ">", "gte": ">=", "like": "LIKE" }

		order = self.pk_field
		if hasattr(self, 'ordering'):
			order = self.ordering

		clause = ""
		for f,v in kwargs.items():
			f = f.split("__")
			if len(f) == 1: f.append("eq")
			f[1] = operands[f[1]]

			if clause == "":
				clause = sanitary_format("{field} __op__ '{value}'", field = f[0],
					value = str(v))
			else:
				clause = clause + sanitary_format(" AND {field} __op__ '{value}'", field = f[0],
					value = str(v))

			clause = clause.replace("__op__", f[1])

		q = sanitary_format("SELECT * FROM {__table__} WHERE __clause__ ORDER BY {__order__};",
				__table__ = self.db_table, __order__ = order)

		q = q.replace("__clause__", clause)

		cur.execute(q)

		return [self.from_row(self._pbx, row) for row in cur.fetchall()]

	def __getitem__(self, field):
		if self.is_object_instance():
			return self._instanced_fields[field]
		else: return self.get(field)

	def __repr__(self):
		if len(self._instanced_fields) == 0:
			return "Module: " + self.description

		desc_fields = re.findall(r"{([\w-]*)}", self.repr_format)
		format_dict = dict([(f, str(self[f])) for f in desc_fields if f in self._instanced_fields])
		return self.repr_format.format( **format_dict )

	def __iter__(self):
		for k,v in self._instanced_fields.items():
			yield k,v

	def config_url(self):
		if not hasattr(self, "config_param"): return None

		p = self.__class__.config_param(self)
		return self._pbx.make_config_url(p)

	def uid(self):
		return "%s-%s" % (self.__class__.__name__, self[self.pk_field])

class InboundRoute(Module):
	description = "Inbound Routes"
	item_name = "Inbound Route"
	repr_format = "{description} ({extension})"

	db_table = "incoming"
	pk_field = "extension"

	render_template = "table.tpl"

	fields = ODict([
			("extension", StringField("DID number")),
			("description", StringField("description")),
			#("cidnum", StringField("caller id number")),
			#("pricid", BooleanField("CID priority route", ("", "CHECKED"))),
			#("alertinfo", StringField("alert info")),
			#("grppre", StringField("CID name prefix")),
			#("mohclass", StringField("music on hold")),
			#("ringing", BooleanField("signal ringing", ("", "CHECKED"))),
			#("delay_answer", IntField("pause before answer")),
			#("privacyman", BooleanField("privacy manager", (0,1))),
			("destination", DestinationField("destination")),
			("notes", StringField("Notes")),
		])

class CallRecording(Module):
	description = "Call Recordings"
	item_name = "Call Recording"
	repr_format = "{description}"
	dest_regex = "ext-callrecording,([0-9]+)"

	pk_field = "callrecording_id"
	db_table = "callrecording"

	render_template = "list.tpl"

	config_param = staticmethod(lambda s: {"display": "callrecording", "type": "setup", "extdisplay": s["callrecording_id"]})

	fields = ODict([
			("callrecording_id", IntField()),
			("description", StringField("description")),
			("callrecording_mode", EnumField( "call recording mode",
				{"": "Allow", "delayed": "Record on Answer", "force": "Record Immediately", "never": "Never"})),
			("dest", DestinationField("destination")),
		])

class ParkingLot(Module):
	description = "Parking Lots"
	item_name = "Parking Lot"
	repr_format = "{name}"

	pk_field = "id"
	db_table = "parkplus"

	render_template = "list.tpl"

	config_param = staticmethod(lambda s: {"display": "parking", "type": "action", "id": s["id"]})

	fields = ODict([
			("id", IntField()),
			("parkext", IntField("parking lot extension")),
			("name", StringField("parking lot name")),
			("parkpos", IntField("parking lot starting position")),
			("numslots", IntField("number of slots")),
			("parkingtime", IntField("parking timeout")),
			("parkedmusicclass", StringField("parked music class")),
			("generatehints", BooleanField("BLF capabilities", ("no", "yes"))),
			("findslot", StringField("find slot")),
			("parkedplay", StringField("pickup courtesy tone")),
			("parkedcalltransfers", StringField("transfer capability")),
			("parkedcallreparking", StringField("reparking capability")),
			("alertinfo", StringField("parking alert-info")),
			("cidpp", StringField("callerID prepend")),
			("autocidpp", StringField("auto callerID prepend")),
			("announcement_id", ForeignKeyField("announcement", "Recording", {0: "None", None:"None"})),
			("comebacktoorigin", BooleanField("come back to origin", ("no", "yes"))),
			("dest", DestinationField("destination")),
		])


class Directory(Module):
	description  = "Directories"
	item_name = "Directory"
	repr_format = "{dirname}"
	dest_regex = "directory,([0-9]+)"

	pk_field = "id"
	db_table = "directory_details"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "directory", "id": s["id"]})

	fields = ODict([
			("id", IntField()),
			("dirname", StringField("directory name")),
			("description", StringField("directory description")),
			("callid_prefix", StringField("CID prefix")),
			("alert_info", StringField("alert info")),
			("announcement", ForeignKeyField("announcement", "Recording", {0: "None"})),
			("repeat_loops", IntField("invalid retries")),
			("repeat_recording", ForeignKeyField("invalid retry recording", "Recording", {"": "None", 0: "Default"})),
			("invalid_recording", ForeignKeyField("invalid recording", "Recording", {"": "None", 0: "Default"})),
			("invalid_destination", DestinationField("invalid destination")),
			("retivr", BooleanField("return to IVR", ("", "1"))),
			("say_extension", BooleanField("announce extension", ("", "1"))),
			("entries", ManyToManyField("directory entries", "DirectoryEntry", "id")),
		])

class DirectoryEntry(Module):
	description = "Directory Entries"
	item_name = "Directory Entry"
	repr_format = "{name}"
	db_table = "directory_entries"
	pk_field = "id"

	render_template = None

	fields = ODict([
			("id", IntField()),
			("e_id", IntField()),
			("name", StringField()),
			("audio", StringField()),
			("type", StringField()),
			("foreign_id", IntField()),
			("dial", StringField())
		])

	def __repr__(self):
		#for k, v in self.fields.iteritems():
		#print self["audio"].value
		if self["type"].value == "user":
			self["dial"].value = str(self["foreign_id"])
			self["name"].value = self._pbx["Extension"].get(self["foreign_id"].value)["name"].value

		audio = {
			"tts": "Text-to-speech",
			"spell": "Spell name",
			"vm": "Voicemail Greeting",
			None: "Voicemail Greeting"
			}.get(self["audio"].value, "")

		if len(audio) == 0:
			audio = int(self["audio"].value)
			audio = "Recording: %s" % self._pbx["Recording"].get(audio)

		return "%s (%s): %s" % (self["name"], audio, self["dial"])

class Queue(Module):
	description = "Queues"
	item_name = "Queue"
	repr_format = "{extension}: {descr}"
	dest_regex = "ext-queues,([0-9]+)"
	db_table = "queues_config"
	render_template = "list.tpl"
	pk_field = "extension"

	config_param = staticmethod(lambda s: {"display": "queues", "extdisplay": s["extension"]})

	fields = ODict([
			("extension", IntField("queue number")),
			("descr", StringField("queue name")),
			("password", StringField("queue password")),
			("togglehint", BooleanField("generate device hints", (0,1))),
			("callconfirm", BooleanField("call confirm", (0,1))),
			("callconfirm_id", ForeignKeyField("call confirm announce", "Recording", {0: "Default"})),
			("grppre", StringField("CID name prefix")),
			("queuewait", BooleanField("wait time prefix", (0,1))),
			("alertinfo", StringField("alertinfo")),
			("members", ListField("\n", "static agents").xpath('//textarea[@id="members"]//text()')),
			("dynmembers", ListField("\n", "dynamic members").xpath('//textarea[@id="dynmembers"]//text()')),
			("dest", DestinationField("fail over destination")),
		])

class Extension(Module):
	description = "Extensions"
	item_name = "Extension"
	repr_format = "<{extension}> {name}"
	db_table = "users"
	pk_field = "extension"

	fields = ODict([
			("extension", IntField()),
			("name", StringField("name")),
		])

	render_template = None

	dest_regex = "from-did-direct,([0-9]+)"

	#def get(self, pk):
	#	try:
	#		page = self._pbx.get_config_from_param(display="extensions", extdisplay=pk)
	#	except: return None
	#
	#	row = {}
	#	row["ext"] = pk
	#	row["name"] = page.xpath('//input[@name="name"]/@value')[0]
	#
	#	return Extension.from_row(self._pbx, row)

class Blacklist(Module):
	description = "Blacklist"
	item_name = "Blacklist"
	repr_format = "{description}"

	pk_field = "number"

	fields = ODict([
			("description", StringField("description")),
			("number", StringField("Number/CID")),
		])

	render_template = "table.tpl"

	def get(self, pk):

		# hacky and slow, but I doubt I'm ever going to need to call
		# the get method on this module
		for c in self.all():
			if c[self.pk_field].value == pk: return c

		return None

	def __len__(self):
		return len(self.all())

	def all(self):
		page = self._pbx.get_config_from_param(display="blacklist")
		try:
			child = page.xpath('(//h5[text()="Blacklist entries"])/../../..')[0].getchildren()[2:]
		except:
			return []

		ret = []
		for c in child:
			row = {}
			row["description"] = c.xpath("td[2]//text()")[0]
			row["number"] = c.xpath("td[1]//text()")[0]
			ret.append( Blacklist.from_row(self._pbx, row))

		return ret

class IVR(Module):
	description = "IVRs"
	item_name = "IVR"
	repr_format = "{name}"
	dest_regex = "ivr-([0-9]+)"

	db_table = "ivr_details"
	pk_field = "id"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "ivr", "action": "edit", "id": s["id"]})

	fields = ODict([
			("id", IntField()),
			("name", StringField("IVR name")),
			("description", StringField("IVR description")),
			("announcement", ForeignKeyField("announcement", "Recording", {0: "None"})),
			("directdial", ForeignKeyField("direct dial", "Directory", {"": "Disabled", "ext-local": "Extensions"})),
			("timeout_time", IntField("timeout")),
			("invalid_loops", IntField("invalid loops")),
			("invalid_retry_recording", ForeignKeyField("invalid retry recording", "Recording", {"": "None", "default": "Default"})),
			("invalid_append_announce", BooleanField("append announcement on invalid", (0,1))),
			("invalid_recording", ForeignKeyField("invalid recording", "Recording", {"": "None", "default": "Default"})),
			("invalid_destination", DestinationField("invalid destination")),
			("timeout_loops", IntField("timeout retries")),
			("timeout_retry_recording", ForeignKeyField("timeout retry recording", "Recording", {"": "None", "default": "Default"})),
			("timeout_append_announce", BooleanField("append announcement on timeout", (0,1))),
			("timeout_recording", ForeignKeyField("timeout recording", "Recording", {"": "None", "default": "Default"})),
			("timeout_destination", DestinationField("timeout destination")),
			("retvm", BooleanField("return to IVR after VM", ("", "on"))),
			("entries", ManyToManyField( "IVR entries", "IVREntry", "ivr_id")),
		])

class IVREntry(Module):
	description = "IVR entries"
	item_name = "IVR entry"
	repr_format = "{selection}: {dest}"

	render_template = None
	db_table = "ivr_entries"
	pk_field = "ivr_id"

	fields = ODict([
			("ivr_id", IntField()),
			("selection", StringField("selection")),
			("dest", DestinationField("destination")),
		])

class RingGroup(Module):
	description = "Ring Groups"
	item_name = "Ring Group"
	repr_format = "{description} ({grpnum})"
	dest_regex = "ext-group,([0-9]+)"

	db_table = "ringgroups"
	pk_field = "grpnum"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display":"ringgroups", "extdisplay": "GRP-%s" % s["grpnum"]})

	fields = ODict([
			("grpnum", IntField("group number")),
			("description", StringField("group description")),
			("strategy", StringField("ring strategy")),
			("grptime", IntField("ring time")),
			("grplist", ListField("-", "extension list")),
			("annmsg_id", ForeignKeyField("announcement", "Recording", {0: "None"})),
			("ringing", StringField("play music on hold")),
			("grppre", StringField("CID name prefix")),
			("alertinfo", StringField("alert info")),
			("cfignore", BooleanField("ignore CF settings", ("", "CHECKED"))),
			("cwignore", BooleanField("skip busy agent", ("", "CHECKED"))),
			("cpickup", BooleanField("enable call pickup", ("", "CHECKED"))),
			("needsconf", BooleanField("confirm calls", ("", "CHECKED"))),
			("remotealert_id", ForeignKeyField("remote announce", "Recording", {0: "Default"})),
			("toolate_id", ForeignKeyField("too-late announce", "Recording", {0: "Default"})),
			("postdest", DestinationField("destination if no answer")),
		])

class Administrator(Module):
	description = "Administrators"
	item_name = "Administrator"
	repr_format = "{username}"

	db_table = "ampusers"
	pk_field = "username"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "ampusers", "userdisplay": s["username"]})

	fields = ODict([
			("username", StringField("username")),
			("password_sha1", StringField("password hash")),
			("deptname", StringField("department name")),
			("extension_low", IntField("extension low")),
			("extension_high", IntField("extension high")),
			("sections", ListField(";", "permissions")),
		])



class TimeCondition(Module):
	description = "Time Conditions"
	item_name = "Time Condition"
	repr_format = "{displayname}"
	dest_regex = "timeconditions,([0-9]+)"

	db_table = "timeconditions"
	pk_field = "timeconditions_id"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "timeconditions", "itemid": s["timeconditions_id"]})

	fields = ODict([
			("timeconditions_id", IntField()),
			("displayname", StringField("time condition name")),
			("time", ForeignKeyField( "time group", "TimeGroup", {0: "Default"})),
			("truegoto", DestinationField("destination if time matches")),
			("falsegoto", DestinationField("destination if time does not match")),
		])

class TimeGroupDetails(Module):
	description = "Time Group Details"
	item_name = "Time Group Detail"
	repr_format = "{time}"

	db_table = "timegroups_details"
	pk_field = "id"

	render_template = None

	fields = ODict([
			("id", IntField()),
			("timegroupid", IntField()),
			("time", StringField("time")),
		])

class TimeGroup(Module):
	description = "Time Groups"
	item_name = "Time Group"
	repr_format = "{description}"

	db_table = "timegroups_groups"
	pk_field = "id"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "timegroups", "extdisplay": s["id"]})

	fields = ODict([
			("id", IntField()),
			("description", StringField("description")),
			("times", ManyToManyField("times", "TimeGroupDetails", "timegroupid")),
		])

class Announcement(Module):
	description = "Announcements"
	item_name = "Announcement"
	repr_format = "{description}"
	dest_regex = "app-announcement-([0-9]+)"

	db_table = "announcement"
	pk_field = "announcement_id"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "announcement", "type":"setup", "extdisplay": s["announcement_id"]})

	fields = ODict([
			("announcement_id", IntField()),
			("description", StringField("description")),
			("recording_id", ForeignKeyField("recording", "Recording", {0: "None"})),
			("allow_skip", BooleanField("allow skip", (0,1))),
			("return_ivr", BooleanField("return to IVR", (0,1))),
			("noanswer", BooleanField("don't answer channel", (0,1))),
			("repeat_msg", StringField("repeat")),
			("post_dest", DestinationField("destination after playback")),
		])

class MiscApplication(Module):
	description = "Misc. Applications"
	item_name = "Misc Application"
	repr_format = "{description}"

	db_table = "miscapps"
	pk_field = "miscapps_id"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "miscapps", "type":"setup", "extdisplay": s["miscapps_id"]})

	fields = ODict([
			("miscapps_id", IntField()),
			("ext", StringField("feature code")),
			("description", StringField("description")),
			("dest", DestinationField("destination")),
		])

class CustomDestination(Module):
	description = "Custom Destinations"
	item_name = "Custom Destination"
	repr_format = "{description}"

	db_table = "custom_destinations"
	pk_field = "custom_dest"
	render_template = "list.tpl"
	config_param = staticmethod(lambda s: {"display": "customdests", "type":"tool", "extdisplay": s["custom_dest"]})

	fields = ODict([
			("custom_dest", StringField("custom destination")),
			("description", StringField("description")),
			("notes", StringField("notes")),
		])



class MiscDestination(Module):

	description = "Misc. Destinations"
	item_name = "Misc Destination"
	repr_format = "{description}"
	dest_regex = "ext-miscdests,([0-9]+)"
	render_template = "list.tpl"
	db_table = "miscdests"
	pk_field = "id"

	config_param = staticmethod(lambda s: {"display": "miscdests", "id": s["id"]})

	fields = ODict([
			("id", IntField()),
			("description", StringField("description")),
			("destdial", IntField("destination number")),
		])

class Recording(Module):
	description = "Recordings"
	item_name = "Recording"
	repr_format = "{displayname}"
	render_template = "list.tpl"
	db_table = "recordings"
	pk_field = "id"

	config_param = staticmethod(lambda s: {"display": "recordings", "action":"edit",
		"usersnum": "", "id": s["id"]})

	fields = ODict([
			("id", IntField()),
			("displayname", StringField("name")),
			("filename", StringField("file path")),
			("fcode", BooleanField("link to feature code", (0, 1))),
			("fcode_pass", IntField("feature code password")),
		])

	def __len__(self):
		return Module.__len__(self)

class CustomExtension(Module):
	description = "Custom Extensions"
	item_name = "Custom Extension"
	repr_format = "{custom_exten}"
	render_template = "list.tpl"
	db_table = "custom_extensions"
	pk_field = "custom_exten"

	config_param = staticmethod(lambda s: {"display": "customextens", "type":"tool", "extdisplay": s["custom_exten"]})

	fields = ODict([
			("custom_exten", StringField("custom extension")),
			("description", StringField("description")),
			("notes", StringField("notes")),
		])

class FeatureCode(Module):
	description = "Feature Codes"
	item_name = "Feature Code"
	repr_format = "{description}"

	pk_field = "featurename"
	db_table = "featurecodes"

	ordering = "modulename,description"
	render_template = "table.tpl"

	fields = ODict([
			("modulename", StringField("module")),
			("featurename", StringField()),
			("defaultcode", StringField("default")),
			("customcode", StringField("custom")),
			("description", StringField("description")),
			("enabled", BooleanField("enabled", (0,1))),
		])
