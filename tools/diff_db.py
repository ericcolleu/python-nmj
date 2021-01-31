import sqlite3
import sys

from nmj.tables import ALL_TABLES
from sqlite3_diff import diff_table, table_column_diff
from sqlite3_diff.format import format_table_diff


def get_connection_and_cursor(db_file):
	connection = sqlite3.connect(db_file)
	connection.isolation_level = "DEFERRED"
	connection.text_factory = str
	cursor = connection.cursor()
	return connection, cursor


db1, cur1 = get_connection_and_cursor("/home/ecolleu/dev/nmjv2/series.orig/nmj_database/media.db")
db2, cur2 = get_connection_and_cursor("/home/ecolleu/dev/nmjv2/series/nmj_database/media.db")

for table in ALL_TABLES:
	diff = table_column_diff(cur1, cur2)
	print(diff)

