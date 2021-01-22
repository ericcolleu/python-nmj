import logging

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
	TABLE = ""
	FIELDS = OrderedDict()
	DEFAULTS = {}

	@classmethod
	def load(cls, cursor, **kwargs):
		where_clause = ""
		order_by_clause = ""
		limit_clause = ""
		params = []
		where = kwargs.pop("where", None)
		order_by = kwargs.pop("order_by", None)
		limit = kwargs.pop("limit", None)
		if limit:
			limit_clause=" LIMIT %s" % limit
		if order_by:
			order_by_clause=" ORDER BY %s " % order_by
		if where:
			where_clause = " WHERE %s" % where
		elif kwargs:
			where_clauses = []
			for key, value in kwargs.items():
				where_clauses.append("%s=?" % key.upper())
				params.append(value)
			where_clause = " WHERE " + "AND ".join(where_clauses)
		cmd="""SELECT %s from %s%s%s%s;""" % (",".join(cls.FIELDS.keys()), cls.TABLE, where_clause, order_by_clause, limit_clause)
		_LOGGER.debug("get %s items: %s with params %s", cls.__name__, cmd, params)
		db_instances = cursor.execute(cmd, params)
		py_instances = []
		for db_instance in db_instances:
			py_instance = cls()
			for rank, name in enumerate(cls.FIELDS.keys()):
				setattr(py_instance, name.lower(), db_instance[rank])
			py_instances.append(py_instance)
		return py_instances

	@classmethod
	def get_rows_number(cls, cursor):
		return len(cursor.execute("""SELECT * from %s;""" % cls.TABLE).fetchall())

	@classmethod
	def get_id_field(cls):
		return list(cls.FIELDS.items())[0][0]
	@classmethod
	def get_next_id(cls, cursor):
		current_id = cursor.execute("""SELECT MAX(%s) from %s;""" % (cls.get_id_field(), cls.TABLE)).fetchone()[0] or 0
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
			if "id" in kwargs:
				item_id = kwargs["id"]
			param_values = list(params.values())[1:]
			cmd = """INSERT INTO %s VALUES (%d,%s)""" % (cls.TABLE, item_id, ",".join(["?"] * len(param_values)))
			_LOGGER.debug("%s.insert(%s) cmd is:\n%s\n with params : %s", cls, kwargs, cmd, param_values)
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
		cmd = """SELECT * from %s WHERE %s;""" % (cls.TABLE, " AND ".join(params))
		_LOGGER.debug("%s.find(%s) cmd is:\n%s", cls, kwargs, cmd)
		return len(cursor.execute(cmd, kwargs.values()).fetchall())

	@classmethod
	def create(cls, cursor):
		_LOGGER.debug("create table %s", cls.__name__)
		items = "%s %s PRIMARY KEY" % (list(cls.FIELDS.keys())[0], list(cls.FIELDS.items())[0][1])
		for column, column_type in list(cls.FIELDS.items())[1:]:
			items += ", %s %s" % (column, column_type)
			if column in cls.DEFAULTS:
				items += " DEFAULT '%s'" % cls.DEFAULTS[column]
		cmd = """CREATE TABLE %s (%s)""" % (cls.TABLE, items)
		_LOGGER.debug("%s.create() cmd is:\n%s", cls, cmd)
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
			cmd = """UPDATE %s SET %s WHERE %s=%s""" % (
				self.TABLE,
				", ".join(query),
				self.get_id_field(),
				self.get_id_value()
			)
			_LOGGER.debug("%s.update(%s) cmd is:\n%s\n with params : %s", self.__class__.__name__, kwargs, cmd, params)
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
	def __repr__(self):
		attrs = ["%s=%s" % (attr, value) for attr, value in self.__dict__.items() if not attr.startswith("__") and value]
		return "%s(%s)" % (self.__class__.__name__, ",".join(attrs))


class DbVersion(DatabaseItem):
	TABLE = "DB_VERSION"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("VERSION", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ScanDirs(DatabaseItem):
	TABLE = "SCAN_DIRS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("DIRECTORY", "TEXT"), ("NAME", "TEXT"), ("SCAN_TIME", "TEXT"), ("SIZE", "INTEGER"), ("CATEGORY", "INTEGER"), ("STATUS", "TEXT"), ("SEQUENCE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ScanSystem(DatabaseItem):
	TABLE = "SCAN_SYSTEM"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TYPE", "TEXT"), ("VALUE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ContentProviders(DatabaseItem):
	TABLE = "CONTENT_PROVIDERS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("DESCRIPTION", "TEXT"), ("CREATE_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Photos(DatabaseItem):
	TABLE = "PHOTOS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TITLE", "TEXT"), ("SEARCH_TITLE", "TEXT"), ("PATH", "TEXT"), ("SCAN_DIRS_ID", "INTEGER"), ("THUMBNAIL", "TEXT"), ("PREVIEW", "TEXT"), ("FORMAT", "TEXT"), ("WIDTH", "TEXT"), ("HEIGHT", "TEXT"), ("CAPTURE_TIME", "TEXT"), ("F_NUMBER", "TEXT"), ("SHUTTLE_SPEED", "TEXT"), ("FOCAL_LENGTH", "TEXT"), ("ISO_SPEED", "TEXT"), ("FLASH", "TEXT"), ("MODEL", "TEXT"), ("SIZE", "INTEGER"), ("CREATE_TIME", "TEXT"), ("UPDATE_STATE", "TEXT"), ("FILE_STATUS", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class PhotoAlbums(DatabaseItem):
	TABLE = "PHOTO_ALBUMS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TITLE", "TEXT"), ("SEARCH_TITLE", "TEXT"), ("PATH", "TEXT"), ("TOTAL_ITEM", "INTEGER"), ("CREATE_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class PhotoAlbumsPhotos(DatabaseItem):
	TABLE = "PHOTO_ALBUMS_PHOTOS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PHOTO_ALBUMS_ID", "INTEGER"), ("PHOTOS_ID", "INTEGER"), ("SEQUENCE", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class PhotoDate(DatabaseItem):
	TABLE = "PHOTO_DATE"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("CAPTURE_TIME", "TEXT"), ("TOTAL_ITEM", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class PhotoLastOpen(DatabaseItem):
	TABLE = "PHOTO_LAST_OPEN"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PHOTOS_ID", "INTEGER"), ("CREATE_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Songs(DatabaseItem):
	TABLE = "SONGS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TITLE", "TEXT"), ("SEARCH_TITLE", "TEXT"), ("PATH", "TEXT"), ("SCAN_DIRS_ID", "INTEGER"), ("FOLDERS_ID", "INTEGER"), ("RUNTIME", "TEXT"), ("FORMAT", "TEXT"), ("LYRIC", "TEXT"), ("RATING", "INTEGER"), ("HASH", "TEXT"), ("SIZE", "INTEGER"), ("PLAY_COUNT", "INTEGER"), ("BIT_RATE", "TEXT"), ("TRACK_POSITION", "INTEGER"), ("RELEASE_DATE", "TEXT"), ("CREATE_TIME", "TEXT"), ("UPDATE_STATE", "TEXT"), ("FILE_STATUS", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongAlbums(DatabaseItem):
	TABLE = "SONG_ALBUMS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TITLE", "TEXT"), ("LANGUAGE", "TEXT"), ("SEARCH_TITLE", "TEXT"), ("TOTAL_ITEM", "TEXT"), ("RELEASE_DATE", "TEXT"), ("UPDATE_STATE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongAlbumsSongs(DatabaseItem):
	TABLE = "SONG_ALBUMS_SONGS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("ALBUMS_ID", "INTEGER"), ("SONGS_ID", "INTEGER"), ("SEQUENCE", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongFolders(DatabaseItem):
	TABLE = "SONG_FOLDERS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("FOLDER", "TEXT"), ("TOTAL_ITEM", "TEXT"), ("PATH", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongGenresSongs(DatabaseItem):
	TABLE = "SONG_GENRES_SONGS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("SONGS_ID", "INTEGER"), ("GENRES_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongGenres(DatabaseItem):
	TABLE = "SONG_GENRES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("DESCRIPTION", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongGenresSongAlbums(DatabaseItem):
	TABLE = "SONG_GENRES_SONG_ALBUMS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("ALBUMS_ID", "INTEGER"), ("GENRES_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongGroupsSongAlbums(DatabaseItem):
	TABLE = "SONG_GROUPS_SONG_ALBUMS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("GROUPS_ID", "INTEGER"), ("ALBUMS_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongGroups(DatabaseItem):
	TABLE = "SONG_GROUPS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("LANGUAGE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongPls(DatabaseItem):
	TABLE = "SONG_PLS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("PATH", "TEXT"), ("FORMAT", "TEXT"), ("SCAN_DIRS_ID", "INTEGER"), ("SIZE", "INTEGER"), ("TOTAL_ITEM", "TEXT"), ("CREATE_TIME", "TEXT"), ("UPDATE_STATE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongPlsItem(DatabaseItem):
	TABLE = "SONG_PLS_ITEM"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PLS_ID", "INTEGER"), ("SONGS_ID", "INTEGER"), ("SEQUENCE", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongLastOpen(DatabaseItem):
	TABLE = "SONG_LAST_OPEN"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("SONGS_ID", "INTEGER"), ("CREATE_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongPersonsSongs(DatabaseItem):
	TABLE = "SONG_PERSONS_SONGS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PERSONS_ID", "INTEGER"), ("SONGS_ID", "INTEGER"), ("PERSON_TYPE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongPersonsSongAlbums(DatabaseItem):
	TABLE = "SONG_PERSONS_SONG_ALBUMS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PERSONS_ID", "INTEGER"), ("ALBUMS_ID", "INTEGER"), ("PERSON_TYPE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongPersons(DatabaseItem):
	TABLE = "SONG_PERSONS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("POSTER", "TEXT"), ("THUMBNAIL", "TEXT"), ("BIOGRAPHY", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class SongAlbumPosters(DatabaseItem):
	TABLE = "SONG_ALBUM_POSTERS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("POSTER", "TEXT"), ("POSTER_HASH", "TEXT"), ("THUMBNAIL", "TEXT"), ("THUMBNAIL_HASH", "TEXT"), ("TYPE", "TEXT"), ("CREATE_TIME", "TEXT"), ("MODIFY_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Shows(DatabaseItem):
	TABLE = "SHOWS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TITLE", "TEXT"), ("SEARCH_TITLE", "TEXT"), ("LAST_PLAY_ITEM", "TEXT"), ("TOTAL_ITEM", "INTEGER"), ("YEAR", "TEXT"), ("RELEASE_DATE", "TEXT"), ("POSTERS_ID", "INTEGER"), ("RATING", "INTEGER"), ("RESOLUTION", "TEXT"), ("PARENTAL_CONTROL", "TEXT"), ("RUNTIME", "INTEGER"), ("CREATE_TIME", "TEXT"), ("TTID", "TEXT"), ("UPDATE_STATE", "TEXT"), ("TITLE_TYPE", "TEXT"), ("CONTENT_ID", "INTEGER"), ("CONTENT_TTID", "INTEGER"), ("THREE_D", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ShowsGenres(DatabaseItem):
	TABLE = "SHOWS_GENRES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("GENRES_ID", "INTEGER"), ("SHOWS_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ShowsKeywords(DatabaseItem):
	TABLE = "SHOWS_KEYWORDS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("KEYWORDS_ID", "INTEGER"), ("SHOWS_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ShowsPersons(DatabaseItem):
	TABLE = "SHOWS_PERSONS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PERSONS_ID", "INTEGER"), ("SHOWS_ID", "INTEGER"), ("PERSON_TYPE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ShowsVideos(DatabaseItem):
	TABLE = "SHOWS_VIDEOS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("SHOWS_ID", "INTEGER"), ("VIDEOS_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ShowGroups(DatabaseItem):
	TABLE = "SHOW_GROUPS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("GROUP_TYPE", "TEXT"), ("LANGUAGE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class ShowGroupsShows(DatabaseItem):
	TABLE = "SHOW_GROUPS_SHOWS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("GROUPS_ID", "INTEGER"), ("SHOWS_ID", "INTEGER"), ("TITLE_TYPE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Videos(DatabaseItem):
	TABLE = "VIDEOS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("PATH", "TEXT"), ("FILE_TYPE", "TEXT"), ("SCAN_DIRS_ID", "INTEGER"), ("CREATE_TIME", "TEXT"), ("UPDATE_STATE", "TEXT"), ("FILE_STATUS", "TEXT"), ("HASH", "TEXT"), ("SIZE", "INTEGER"), ("THREE_D", "INTEGER"), ("RESOLUTION", "TEXT"), ("PLAY_COUNT", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class VideoBookmarks(DatabaseItem):
	TABLE = "VIDEO_BOOKMARKS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("VIDEOS_ID", "INTEGER"), ("TITLE", "TEXT"), ("SEARCH_TITLE", "TEXT"), ("BOOKMARK_TIME", "INTEGER"), ("THUMBNAIL", "TEXT"), ("TYPE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class VideoSubtitles(DatabaseItem):
	TABLE = "VIDEO_SUBTITLES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("VIDEOS_ID", "INTEGER"), ("FILE_NAME", "TEXT"), ("LANGUAGE", "TEXT"), ("SIZE", "INTEGER"), ("CREATE_TIME", "TEXT"), ("TYPE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class VideoGenres(DatabaseItem):
	TABLE = "VIDEO_GENRES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("DESCRIPTION", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class VideoPersons(DatabaseItem):
	TABLE = "VIDEO_PERSONS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("NAME", "TEXT"), ("POSTER", "TEXT"), ("THUMBNAIL", "TEXT"), ("BIOGRAPHY", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class VideoPosters(DatabaseItem):
	TABLE = "VIDEO_POSTERS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("POSTER", "TEXT"), ("POSTER_HASH", "TEXT"), ("THUMBNAIL", "TEXT"), ("THUMBNAIL_HASH", "TEXT"), ("WALLPAPER", "TEXT"), ("TYPE", "TEXT"), ("CREATE_TIME", "TEXT"), ("MODIFY_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class VideoProperties(DatabaseItem):
	TABLE = "VIDEO_PROPERTIES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("RUNTIME", "INTEGER"), ("RESOLUTION", "TEXT"), ("WIDTH", "TEXT"), ("HEIGHT", "TEXT"), ("ASPECT_RATIO", "TEXT"), ("SYSTEM", "TEXT"), ("VIDEO_CODEC", "TEXT"), ("FPS", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Episodes(DatabaseItem):
	TABLE = "EPISODES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("EPISODE_ID", "INTEGER"), ("SERIES_ID", "INTEGER"), ("SEASON_ID", "INTEGER"), ("SEASON", "INTEGER"), ("EPISODE", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Synopsises(DatabaseItem):
	TABLE = "SYNOPSISES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("SUMMARY", "TEXT"), ("TAGLINE", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class TvLastOpen(DatabaseItem):
	TABLE = "TV_LAST_OPEN"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("VIDEOS_ID", "INTEGER"), ("CREATE_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class MovieLastOpen(DatabaseItem):
	TABLE = "MOVIE_LAST_OPEN"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("VIDEOS_ID", "INTEGER"), ("CREATE_TIME", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Keywords(DatabaseItem):
	TABLE = "KEYWORDS"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("KEYWORD", "TEXT"), ("DESCRIPTION", "TEXT"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

class Favourites(DatabaseItem):
	TABLE = "FAVOURITES"
	FIELDS = OrderedDict(
		[("ID", "INTEGER"), ("TYPE", "TEXT"), ("MEDIA_ID", "INTEGER"), ("CUSTOM1", "TEXT"), ("CUSTOM2", "TEXT"), ("CUSTOM3", "TEXT"), ("CUSTOM4", "TEXT"), ("CUSTOM5", "TEXT")]
	)
	DEFAULTS = {}

ALL_TABLES = [
	DbVersion,
	ScanDirs,
	ScanSystem,
	ContentProviders,
	Photos,
	PhotoAlbums,
	PhotoAlbumsPhotos,
	PhotoDate,
	PhotoLastOpen,
	Songs,
	SongAlbums,
	SongAlbumsSongs,
	SongFolders,
	SongGenresSongs,
	SongGenres,
	SongGenresSongAlbums,
	SongGroupsSongAlbums,
	SongGroups,
	SongPls,
	SongPlsItem,
	SongLastOpen,
	SongPersonsSongs,
	SongPersonsSongAlbums,
	SongPersons,
	SongAlbumPosters,
	Shows,
	ShowsGenres,
	ShowsKeywords,
	ShowsPersons,
	ShowsVideos,
	ShowGroups,
	ShowGroupsShows,
	Videos,
	VideoBookmarks,
	VideoSubtitles,
	VideoGenres,
	VideoPersons,
	VideoPosters,
	VideoProperties,
	Episodes,
	Synopsises,
	TvLastOpen,
	MovieLastOpen,
	Keywords,
	Favourites
]
