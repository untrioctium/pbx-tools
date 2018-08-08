import requests
import logging
import MySQLdb
import PBXModule

from lxml.html import fromstring
from PBXUtil import module
from sshtunnel import SSHTunnelForwarder

class PBXError(Exception):
	pass

class PBX:
	"""PBX management class
	"""

	def __init__(self, url):
		'''Sets up a new PBX instance

		Sets up a new instance of a PBX class. This constructor
		does not do any actual connecting.

		Args:
			url: The URL or IP to this PBX

		'''

		self._base_url = url
		self._url = "http://" + url + "/"
		self._config_base = "admin/config.php"

		self._web_session = requests.Session()
		self._web_authenticated = False

		self._sql_connected = False
		self._sql_handle = False
		self._sql_tunnel = False

		self._page_cache = {}

		self._update_percent = None
		self._update_status = None
		self._update_subtask = None

	def set_update_targets( self, percent = None, status = None, subtask = None ):
		self._update_status = status
		self._update_percent = percent
		self._update_subtask = subtask

	def update_status( self, text ):
		if self._update_status is not None:
			self._update_status(text)

	def update_subtask( self, text):
		if self._update_subtask is not None:
			self._update_subtask(text)

	def update_percent( self, percent ):
		if self._update_percent is not None:
			self._update_percent(percent)

	def connect_web_config( self, username, password ):
		try:
			r = self._web_session.get(self._url + self._config_base)
		except requests.exceptions.RequestException:
			raise PBXError("Cannot connect to PBX")

		if r.status_code == 404:
			raise PBXError("Configuration page not found")

		self._web_session.auth = ( username, password )
		r = self._web_session.post(self._url + self._config_base, data = {"username": username, "password": password})

		if r.status_code == 401 or b"Invalid Username or Password" in r.content:
			raise PBXError("Invalid username or password")

		self._web_authenticated = True

	def connect_sql( self, username, password ):
		ssh_logger = logging.getLogger("ssh-logger")
		ssh_logger.disabled = True

		self.update_subtask("Opening proxy")
		self._sql_tunnel = SSHTunnelForwarder(
					(self._base_url, 22),
					ssh_username=username,
					ssh_password=password,
					remote_bind_address=('localhost', 3306),
					logger = ssh_logger)

		self._sql_tunnel.start()
		self._sql_handle = None
		#if not self._sql_tunnel.is_active:
		#	raise PBXError("Cannot open SSH tunnel")


		self.update_subtask("Logging in")
		try:
			self._sql_handle = MySQLdb.connect(
				'127.0.0.1',
				'root',
				password,
				'asterisk', self._sql_tunnel.local_bind_port);
		except:
			try:
				self._sql_handle = MySQLdb.connect(
					'127.0.0.1',
					'root',
					'',
					'asterisk', self._sql_tunnel.local_bind_port);
			except:
				raise PBXError("Cannot log in to SQL")
		self.update_subtask("Logged in")

	def get_sql_cursor( self ):
		if not self._sql_handle: raise PBXError()
		return self._sql_handle.cursor(MySQLdb.cursors.DictCursor)

	def make_config_url(self, param):
		get_line = "?"
		for k, v in param.items():
			get_line += "%s=%s&" % (k, v)
		return self._url + self._config_base + get_line

	def get_config_url(self, url):
		if not self._web_authenticated:
			raise PBXError("could not web auth")

		if url in self._page_cache:
			return self._page_cache[url]

		self.update_subtask("\tScraping: " + url.split("?")[1])
		r = self._web_session.get(self._url + url, headers={'referer': self._config_base})

		if r.status_code != 200:
			raise PBXError("Config scrape error: " + str(r.status_code))

		t = r.content

		t = t.replace(b'"CHECKED ', b'" CHECKED ')
		t = t.replace(b' CHECKED ', b' CHECKED="checked" ')
		t = t.replace(b"CHECKED", b"checked")

		t = t.replace(b'"SELECTED', b'" SELECTED')
		t = t.replace(b'SELECTED', b' SELECTED="selected" ')
		t = t.replace(b"SELECTED", b"selected")

		self._page_cache[url] = fromstring(t)

		return self._page_cache[url]

	def get_config_from_param( self, **kwargs ):
		get_line = "?"
		for k, v in kwargs.items():
			get_line += "%s=%s&" % (k, v)
		return self.get_config_url(self._config_base + get_line)

	def __getitem__(self, mod):
		return module(self, name=mod)

	def __iter__(self):
		for m in self.get_module_names():
			yield self[m]

	def __del__(self):
		self._sql_tunnel.stop()

	def close(self):
		self._sql_tunnel.stop()

	@staticmethod
	def get_module_names():
		return module.registry.keys()
