# -*- coding: utf-8 -*-
import datetime
import logging
import os.path
import sqlite3
import string

from nmj.tables import ALL_TABLES, DbVersion, ScanDirs, ScanSystem, ShowGroups


_LOGGER = logging.getLogger(__name__)

INDEXES = [
	"CREATE INDEX IDX_PHOTOS_TITLE ON PHOTOS(TITLE ASC);",
	"CREATE INDEX IDX_PHOTOS_SEARCH_TITLE ON PHOTOS(SEARCH_TITLE ASC);",
	"CREATE INDEX IDX_PHOTO_ALBUMS_PHOTOS_PHOTO_ALBUMS_ID ON PHOTO_ALBUMS_PHOTOS(PHOTO_ALBUMS_ID ASC);",
	"CREATE INDEX IDX_PHOTO_ALBUMS_PHOTOS_PHOTOS_ID ON PHOTO_ALBUMS_PHOTOS(PHOTOS_ID ASC);",
	"CREATE INDEX IDX_PHOTO_DATE_CAPTURE_TIME ON PHOTO_DATE(CAPTURE_TIME ASC);",
	"CREATE INDEX IDX_SHOWS_CONTENT_TTID ON SHOWS(CONTENT_TTID ASC);",
	"CREATE INDEX IDX_SHOWS_TITLE ON SHOWS(TITLE ASC);",
	"CREATE INDEX IDX_SHOWS_SEARCH_TITLE ON SHOWS(SEARCH_TITLE ASC);",
	"CREATE INDEX IDX_SHOWS_YEAR ON SHOWS(YEAR ASC);",
	"CREATE INDEX IDX_SHOWS_RATING ON SHOWS(RATING ASC);",
	"CREATE INDEX IDX_SHOWS_PARENTAL_CONTROL ON SHOWS(PARENTAL_CONTROL ASC);",
	"CREATE INDEX IDX_SONGS_TITLE ON SONGS(TITLE ASC);",
	"CREATE INDEX IDX_SONGS_SEARCH_TITLE ON SONGS(SEARCH_TITLE ASC);",
	"CREATE INDEX IDX_SONGS_RATING ON SONGS(RATING ASC);",
	"CREATE INDEX IDX_SONGS_RELEASE_DATE ON SONGS(RELEASE_DATE ASC);",
	"CREATE INDEX IDX_SONG_ALBUMS_TITLE ON SONG_ALBUMS(TITLE ASC);",
	"CREATE INDEX IDX_SONG_ALBUMS_SEARCH_TITLE ON SONG_ALBUMS(SEARCH_TITLE ASC);",
	"CREATE INDEX IDX_SONG_ALBUMS_RELEASE_DATE ON SONG_ALBUMS(RELEASE_DATE ASC);",
	"CREATE INDEX IDX_SONG_ALBUM_SONGS_ALBUMS_ID ON SONG_ALBUMS_SONGS(ALBUMS_ID ASC);",
	"CREATE INDEX IDX_SONG_ALBUM_SONGS_SONGS_ID ON SONG_ALBUMS_SONGS(SONGS_ID ASC);",
	"CREATE INDEX IDX_SONG_GENRES_SONGS_GENRES_ID ON SONG_GENRES_SONGS(GENRES_ID ASC);",
	"CREATE INDEX IDX_SONG_GENRES_SONGS_SONGS_ID ON SONG_GENRES_SONGS(SONGS_ID ASC);",
	"CREATE INDEX IDX_SONG_GENRES_SONG_ALBUMS_ALBUMS_ID ON SONG_GENRES_SONG_ALBUMS(ALBUMS_ID ASC);",
	"CREATE INDEX IDX_SONG_GENRES_SONG_ALBUMS_GENRES_ID ON SONG_GENRES_SONG_ALBUMS(GENRES_ID ASC);",
	"CREATE INDEX IDX_SONG_GROUPS_SONG_ALBUMS_GROUPS_ID ON SONG_GROUPS_SONG_ALBUMS(GROUPS_ID ASC);",
	"CREATE INDEX IDX_SONG_GROUPS_SONG_ALBUMS_ALBUMS_ID ON SONG_GROUPS_SONG_ALBUMS(ALBUMS_ID ASC);",
	"CREATE INDEX IDX_SONG_PERSONS_SONGS_PERSONS_ID ON SONG_PERSONS_SONGS(PERSONS_ID ASC);",
	"CREATE INDEX IDX_SONG_PERSONS_SONGS_SONGS_ID ON SONG_PERSONS_SONGS(SONGS_ID ASC);",
	"CREATE INDEX IDX_SONG_PERSONS_SONG_ALBUMS_PERSONS_ID ON SONG_PERSONS_SONG_ALBUMS(PERSONS_ID ASC);",
	"CREATE INDEX IDX_SONG_PERSONS_SONG_ALBUMS_ALBUMS_ID ON SONG_PERSONS_SONG_ALBUMS(ALBUMS_ID ASC);",
	"CREATE INDEX IDX_VIDEO_SUBTITLES_VIDEOS_ID ON VIDEO_SUBTITLES(VIDEOS_ID ASC);",
]
class DBProxy(object):
	isolation_level = "DEFERRED"

	def __init__(self, root_path, popcorn_path=""):
		self.root_path = root_path
		self.popcorn_path = popcorn_path
		self.media_db_path = os.path.join(root_path, "nmj_database", "media.db")
		if not os.path.isfile(self.media_db_path):
			self.create()
		self.connection, self.cursor = self.get_connection_and_cursor()

	def get_connection_and_cursor(self):
		if not os.path.isdir(os.path.join(self.root_path, "nmj_database")):
			os.makedirs(os.path.dirname(self.media_db_path))
		connection = sqlite3.connect(self.media_db_path)
		connection.isolation_level = self.isolation_level
		connection.text_factory = str
		cursor = connection.cursor()
		return connection, cursor

	def create(self):
		_LOGGER.info("Creating database...")
		connection, cursor = self.get_connection_and_cursor()
		for table in ALL_TABLES:
			_LOGGER.debug("create table %s", table)
			table().create(cursor)
		DbVersion.insert(cursor, version="2.0.0")
		ScanDirs.insert(cursor, directory="", name=self.popcorn_path, scan_time="", size=1807172, category=3, status=3)
		ScanSystem.insert(cursor, type="RUNNING_STATUS", value="0")
		ScanSystem.insert(cursor, type="HISTORY_SCAN_VIDEOS", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), custom1="1", custom2="89", custom3="0")
		for group in ["0-9",] + [letter for letter in string.ascii_uppercase]:
			ShowGroups.insert(cursor, name=group, language="FR")
		for request in INDEXES:
			cursor.execute(request)
		connection.commit()
		cursor.close()
		connection.close()
		_LOGGER.info("Database creation done")

	def contains(self, table, **kwargs):
		items = self.get_tables_items(table, **kwargs)
		return bool(items)

	def get_first(self, table, **kwargs):
		try:
			return self.get_tables_items(table, **kwargs)[0]
		except IndexError:
			return None

	def get_tables_items(self, *tables, **kwargs):
		result = []
		for table in tables:
			try:
				result += table.load(self.cursor, **kwargs)
			except:
				_LOGGER.exception("Getting items in table %s", table)
		return result

	def insert(self, table, **kwargs):
		return table.insert(self.cursor, **kwargs)

	def commit(self):
		self.connection.commit()

	def delete(self, to_remove):
		to_remove.delete(self.cursor)

	def update(self, table, item_id, **kwargs):
		item = self.get_tables_items(table, id=item_id)[0]
		item.update(self.cursor, **kwargs)
		self.commit()


