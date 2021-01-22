# -*- coding: utf-8 -*-
import datetime
import logging
import os.path
import re

from nmj.utils import download_image, to_unicode


UNKNOWN_MEDIA_TYPE="Unknown media type"
MOVIE_MEDIA_TYPE="Movie"
MUSIC_MEDIA_TYPE="Music"
TVSHOW_EPISODE_MEDIA_TYPE="TVShow Episode"
NMJ_ACTOR="Actor"
NMJ_DIRECTOR="Director"
DEFAULT_RELEASE_DATE = datetime.datetime(9999, 1, 1)

_LOGGER = logging.getLogger(__name__)
class AbstractNotImplemented(Exception): pass

class Scanner(object):
	accepted_extensions = []
	accepted_regexp = []
	accepted_media = UNKNOWN_MEDIA_TYPE
	ignored_sort_tokens = [
		u"à ",
		u"les ",
		u"le ",
		u"la ",
		u"l'",
		u"l’",
		u"de ",
		u"du ",
		u"d'",
		u"the ",
		u"an ",
		u"a ",
	]

	def __init__(self):
		self.compiled_regexp = [re.compile(regexp, re.I) for regexp in self.accepted_regexp]

	def accept(self, media):
		if os.path.splitext(media.path)[1] not in self.accepted_extensions:
			return False

		title = os.path.basename(os.path.splitext(media.path)[0])
		for regexp in self.compiled_regexp:
			regexp = re.compile(regexp)
			if regexp.match(title):
				media.set_media_type(self.accepted_media)
				return True
		return False

	def search(self, title): # pragma no cover
		raise AbstractNotImplemented("search method MUST be implemented on Scanner objet")

	def get_details(self, search_result): # pragma no cover
		raise AbstractNotImplemented("get_details method MUST be implemented on Scanner objet")

	def clean(self, title):
		return title

	def get_search_title(self, title):
		lower_title = to_unicode(title.lower())
		for prefix in self.ignored_sort_tokens:
			_LOGGER.debug("searching %s in %s", prefix, lower_title)
			if lower_title.startswith(prefix):
				return title[len(prefix):].strip()
		return title.strip()

class MovieScanner(Scanner):
	accepted_extensions = [".avi", ".mpg", ".mpeg", ".mkv", ".iso", ".mp4", ".vob", ".ogm"]
	accepted_regexp = ["^(?P<show_name>.*).*$", ]
	accepted_media = MOVIE_MEDIA_TYPE

class TVShowScanner(Scanner):
	accepted_extensions = [".avi", ".mpg", ".mpeg", ".mkv", ".iso", ".mp4", ".vob", ".ogm"]
	accepted_regexp = [
		"^(?P<show_name>.*)\s-\s(?P<episode>\d+).*$",
		"^(?P<show_name>.*)[S|s](?P<season>\d+)[E|e](?P<episode>\d+).*$",
		"^(?P<show_name>.*)[-|\s|_](?P<season>\d+)[X|x](?P<episode>\d+).*$",
		"^(?P<show_name>.*)[S|s](?P<season>\d+).*$"
	]
	accepted_media = TVSHOW_EPISODE_MEDIA_TYPE

	def get_details_from_media(self, media):
		title = self.clean(media.title)
		for pattern in self.accepted_regexp: #for regexp in self.compiled_regexp:
			_LOGGER.debug("test %s with regexp %s", title, pattern)
			regexp = re.compile(pattern)
			match = regexp.match(title)
			if match:
				_LOGGER.debug("regexp match!!")
				params = match.groupdict()
				for key, value in params.items():
					params[key] = value.strip()
				return params
			else:
				_LOGGER.debug("regexp doesn't match!!")
		return {
			"show_name" : media.title,
			"season" : 1,
			"episode" : 1,
		}


class Printable(object):
	def do_str(self):
		raise AbstractNotImplemented("MUST implement do_str")
	def __str__(self):
		return self.do_str()
	def __repr__(self):
		return self.do_str()

class MediaFile(Printable):
	extension_to_system = {
		".avi" : "AVI",
		".mkv" : "Matroska",
	}
	def __init__(self, path, relative_path=None):
		self.filename = os.path.basename(path)
		self.title, self.extension = os.path.splitext(self.filename)
		self.path = path
		self.relative_path = relative_path or path
		self.location = os.path.dirname(path)
		self.media_type = UNKNOWN_MEDIA_TYPE
		self.system = self.extension_to_system.get(os.path.splitext(self.filename)[1], "")

	def set_media_type(self, media_type):
		self.media_type = media_type

	def export(self):
		return {
			self.title : self.filename,
		}

	def do_str(self):
		return "%s (%s)" % (self.path, self.media_type)

class SearchResult(Printable):
	def __init__(self, search_id, poster_url, title, filepath):
		self.search_id = search_id
		self.poster_url = poster_url or NMJImage()
		self.title = title
		self.filepath = filepath

	def get_poster(self):
		return self.poster_url

	def do_str(self):
		return "SearchResult(%s, %s, %s)" % (self.search_id, self.get_poster(), to_unicode(self.title))

	def export(self):
		return {
			"id" : self.search_id,
			"title" : self.title,
			"poster" : self.poster_url.url,
		}

class TVShowSearchResult(SearchResult):
	def __init__(self, search_id, poster_url, show, filepath, showdata=None, season="", episode="", **kwargs_):
		super(TVShowSearchResult, self).__init__(search_id, poster_url, show, filepath)
		self.season = season
		self.episode = episode
		self.showdata = showdata

	def do_str(self):
		return "TVShowSearchResult(%s, %s, %s)" % (self.title, self.season, self.episode)

class NMJImage(Printable):
	def __init__(self, url=""):
		self.filename = os.path.basename(url)
		self.url = url

	def download(self, base_dir, prefix):
		relative_path = "%s%s" % (prefix, self.filename)
		_LOGGER.info("Downloading image in %s from %s", os.path.join(base_dir, relative_path), self.url)
		download_image(self.url, os.path.join(base_dir, relative_path))
		return relative_path

	def do_str(self):
		return "NMJImage(%s)" % self.filename

class NMJImageDownloader(object):
	def __init__(self, posters=None, thumbnails=None, wallpapers=None):
		self.posters=posters or []
		self.thumbnails=thumbnails or []
		self.wallpapers=wallpapers or []
		self.poster_path=""
		self.thumbnail_path=""
		self.wallpaper_path=""
		self.base_dir=""

	def set_base_dir(self, base_dir):
		self.base_dir = base_dir

	def download_poster(self):
		if not self.posters:
			return False
		self.poster_path = self.posters[0].download(self.base_dir, os.path.join("nmj_database", "media", "video", "poster", "poster_"))
		return True

	def download_thumbnail(self):
		if not self.thumbnails:
			return False
		self.thumbnail_path = self.thumbnails[0].download(self.base_dir, os.path.join("nmj_database", "media", "video", "thumbnail", "thumbnail_"))
		return True

	def download_wallpaper(self):
		if not self.wallpapers:
			return False
		self.wallpaper_path = self.wallpapers[0].download(self.base_dir, os.path.join("nmj_database", "media", "video", "poster", "wallpaper_"))
		return True

class NMJMovie(Printable, NMJImageDownloader):
	poster_sizes = ['w92', 'w154', 'w185', 'w342', 'w500', 'original']
	def __init__(self, ttid, tmdbid, title="", search_title="", year=9999, release_date="9999-01-01",
				rating=0, parental_control="", runtime=0, synopsis="", posters=None, thumbnails=None, wallpapers=None,
				persons=None, genres=None):
		NMJImageDownloader.__init__(self, posters=posters, thumbnails=thumbnails, wallpapers=wallpapers)
		self.ttid = ttid
		self.content_ttid = tmdbid
		self.title = title.strip()
		self.search_title = search_title.strip()
		self.year = year
		self.release_date = release_date
		self.rating = rating
		self.parental_control = parental_control
		self.runtime=runtime
		self.synopsis=synopsis
		self.persons = persons or []
		self.genres = genres or []
		self.media_file = None

	def set_media_file(self, media_file):
		self.media_file = media_file

	def get_director(self):
		for person in self.persons:
			if person.job == "Director":
				return person
		return ""

	def get_actors(self):
		return [person for person in self.persons if person.job == "Actor"]

	def do_str(self):
		return "Movie: %s (%s)" % (self.title, self.year)

class NMJTVShow(Printable, NMJImageDownloader):
	def __init__(self, ttid="", content_id="", title="", search_title="", synopsis="", release_date=None, rating="", posters=None, thumbnails=None, wallpapers=None, persons=None, genres=None):
		NMJImageDownloader.__init__(self, posters=posters, thumbnails=thumbnails, wallpapers=wallpapers)
		self.ttid = ttid
		self.content_id = content_id
		self.title = title
		self.search_title = search_title
		self.release_date = release_date or DEFAULT_RELEASE_DATE
		self.rating = rating
		self.synopsis = synopsis
		self.persons = persons or []
		self.genres = genres or []

	def get_poster_url(self, image):
		return image

	def get_thumbnail_url(self, image):
		return image

	def get_fanart_url(self, image):
		return image

	def do_str(self):
		return "TVShow: %s" % self.title

class NMJTVShowSeason(Printable, NMJImageDownloader):
	def __init__(self, ttid="", content_id="", title="", rank=0, synopsis="", release_date=None, rating="", posters=None, thumbnails=None, wallpapers=None, persons=None, genres=None):
		NMJImageDownloader.__init__(self, posters=posters, thumbnails=thumbnails, wallpapers=wallpapers)
		self.ttid = ttid
		self.content_id = content_id
		self.title = title
		self.search_title = title
		self.release_date = release_date or DEFAULT_RELEASE_DATE
		self.rating = rating
		self.synopsis = synopsis
		self.rank = rank
		self.persons = persons or []
		self.genres = genres or []

	def get_poster_url(self, image):
		return image

	def get_thumbnail_url(self, image):
		return image

	def get_fanart_url(self, image):
		return image

	def do_str(self):
		return "TVShowSeason: %s" % self.title

class NMJTVShowEpisode(Printable):
	def __init__(self, ttid="", content_id="", title="", rank=0, search_title="", synopsis="", runtime=0, release_date=None, rating="", persons=None, genres=None):
		self.ttid = ttid
		self.content_id = content_id
		self.title = title
		self.search_title = search_title
		self.synopsis = synopsis
		self.release_date = release_date or DEFAULT_RELEASE_DATE
		self.rating = rating
		self.rank = rank
		self.runtime = runtime
		self.persons = persons or []
		self.genres = genres or []

	def do_str(self):
		return "TVShowEpisode: %s" % self.title

class NMJTVMediaInfo(Printable):
	def __init__(self, show, season, episode):
		self.show = show
		self.season = season
		self.episode = episode
		self.media_file = None

	def set_base_dir(self, base_dir):
		self.show.set_base_dir(base_dir)
		self.season.set_base_dir(base_dir)

	def set_media_file(self, media_file):
		self.media_file = media_file

	def do_str(self):
		return "NMJTVMediaInfo: %s (%s, %s)" % (self.show, self.season, self.episode)

class NMJPerson(Printable):
	def __init__(self, name, job):
		self.name = name
		self.job = job
		self.db_id = None

	def set_db_id(self, db_id):
		self.db_id = db_id

	def do_str(self):
		return "%s" % self.name
