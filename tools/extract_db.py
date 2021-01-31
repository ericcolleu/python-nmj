import sqlite3
import sys

def toCamelCase(word):
	return ''.join(x.capitalize() or '_' for x in word.split('_'))

result = [
"""import logging
import re

_LOGGER = logging.getLogger(__name__)
try:
	from collections import OrderedDict
except:
	print("DeprecationWarning: you should use python 2.7")
	from UserDict import DictMixin
	class OrderedDict(DictMixin):
		def __init__(self, items=None):
			items = items or ()
			self._keys = [key for key, _ in items]
			self._values = [value for _, value in items]
			self.data = dict(items)
			self._items = list(items)

		def __getitem__(self, key): return self.data[key]
		def __setitem__(self, key, value):
			if key not in self.data:
				self._keys.append(key)
				self._values.append(value)
				self._items.append((key, value))
			else:
				self._values[self._keys.index(key)] = value
			self.data[key] = value

		def keys(self): return tuple(self._keys)
		def values(self): return tuple(self._values)
		def items(self): return tuple(self._items)


class DatabaseItem(object):
	@classmethod
	def load(cls, cursor, **kwargs):
		where_clause = ""
		params = []
		if kwargs:
			where_clauses = []
			for key, value in kwargs.items():
				where_clauses.append("%s=?" % key.upper())
				params.append(value)
			where_clause = " WHERE " + ", ".join(where_clauses)
		db_instances = cursor.execute(\"""SELECT %s from %s%s;\""" % (
			",".join(cls.FIELDS.keys()),
			cls.TABLE,
			where_clause
		), params)
		py_instances = []
		for db_instance in db_instances:
			py_instance = cls()
			for rank, name in enumerate(cls.FIELDS.keys()):
				setattr(py_instance, name.lower(), db_instance[rank])
			py_instances.append(py_instance)
		return py_instances

	@classmethod
	def get_rows_number(cls, cursor):
		return len(cursor.execute(\"""SELECT * from %s;\""" % cls.TABLE).fetchall())

	@classmethod
	def get_id_field(cls):
		return cls.FIELDS.items()[0][0]
	@classmethod
	def get_next_id(cls, cursor):
		current_id = cursor.execute(\"""SELECT MAX(%s) from %s;\""" % (cls.get_id_field(), cls.TABLE)).fetchone()[0] or 0
		return current_id + 1

	@classmethod
	def purge(cls, cursor):
		cursor.execute("DELETE FROM %s;" % cls.TABLE).fetchone()

	@classmethod
	def insert(cls, cursor, **kwargs):
		_LOGGER.debug("insert %s in %s", kwargs, cls.__name__)
		params = OrderedDict()
		for key in cls.FIELDS.keys():
			if key in cls.DEFAULTS:
				params[key] = cls.DEFAULTS[key]
			elif cls.FIELDS[key] == "INTEGER":
				params[key] = 0
			else:
				params[key] = ""
		for key, value in kwargs.items():
			params[key.upper()] = value
		try:
			item_id = cls.get_next_id(cursor)
			param_values = params.values()[1:]
			cmd = \"""INSERT INTO %s VALUES (%d,%s)\""" % (cls.TABLE, item_id, ",".join(["?"]*len(param_values)))
			_LOGGER.debug("%s.insert(%s) cmd is:\\n%s\\n with params : %s", cls, kwargs, cmd, param_values)
			cursor.execute(cmd, param_values)
			return item_id
		except :
			_LOGGER.exception("Cannot insert %s in %s", kwargs, cls.__name__)
			raise

	@classmethod
	def count(cls, cursor, **kwargs):
		params = []
		for key in kwargs.keys():
			params.append("%s=?" % key)
		cmd = \"""SELECT * from %s WHERE %s;\""" % (cls.TABLE, " AND ".join(params))
		_LOGGER.debug("%s.find(%s) cmd is:\\n%s", cls, kwargs, cmd)
		return len(cursor.execute(cmd, kwargs.values()).fetchall())

	@classmethod
	def create(cls, cursor):
		_LOGGER.debug("create table %s", cls.__name__)
		items = "%s %s PRIMARY KEY" % (cls.FIELDS.keys()[0], cls.FIELDS.items()[0][1])
		for column, column_type in cls.FIELDS.items()[1:]:
			items += ", %s %s" % (column, column_type)
			if column in cls.DEFAULTS:
				items += " DEFAULT '%s'" % cls.DEFAULTS[column]
		cmd = \"""CREATE TABLE %s (%s)\""" % (cls.TABLE, items)
		_LOGGER.debug("%s.create() cmd is:\\n%s", cls, cmd)
		cursor.execute(cmd)

	def get_id_value(self):
		return int(getattr(self, self.get_id_field().lower()))

	def update(self, cursor, **kwargs):
		_LOGGER.debug("update %s in %s", kwargs, self)
		query = []
		params = []
		for key, value in kwargs.items():
			setattr(self, key, value)
			query.append("%s=?" % key.upper())
			params.append(value)
		try:
			cmd = \"""UPDATE %s SET %s WHERE %s=%s\""" % (
				self.TABLE,
				", ".join(query),
				self.get_id_field(),
				self.get_id_value()
			)
			_LOGGER.debug("%s.update(%s) cmd is:\\n%s\n with params : %s", self.__class__.__name__, kwargs, cmd, params)
			cursor.execute(cmd, params)
		except :
			_LOGGER.exception("Cannot update %s in %s", kwargs, self)
			raise

	def delete(self, cursor):
		cursor.execute("DELETE FROM %s WHERE %s=%s" % (
			self.TABLE,
			self.get_id_field(),
			self.get_id_value())
		)

	def __str__(self):
		attrs = ["%s=%s" % (attr, value) for attr, value in self.__dict__.items() if not attr.startswith("__") and value]
		return "%s(%s)" % (self.__class__.__name__, ",".join(attrs))

""",
]

con = sqlite3.connect(sys.argv[1], detect_types=True)
con.row_factory = sqlite3.Row
con.iterdump
cursor = con.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

tables=cursor.fetchall()
for table in tables:
	table = table[0]
	cursor.execute("PRAGMA table_info(%s)" % table)
	data = cursor.fetchall()
	to_format={
		"table_name" : table,
		"class_name" : toCamelCase(table),
		"fields" : ", ".join(["""("%s", "%s")""" % (infos[1], infos[2]) for infos in data]),
	}
	result.append("""class %(class_name)s(DatabaseItem):
	TABLE="%(table_name)s"
	FIELDS=OrderedDict(
		[%(fields)s]
	)
	DEFAULTS = {}
""" % to_format)

result.append(
"""ALL_TABLES = [
%s
]""" % ",\n".join(["\t%s" % toCamelCase(table[0]) for table in tables])
)
print("\n".join(result))

