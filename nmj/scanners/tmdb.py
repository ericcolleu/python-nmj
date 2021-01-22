# -*- coding: utf-8 -*-
import logging
import os.path
from pprint import pprint
#from tmdb3 import set_key, set_locale, searchMovie, Movie
#from tmdbv3api import TMDb
import tmdbsimple as tmdb
tmdb.API_KEY = '104e67f6ef05585ed35eec68f5cae0bf'

from nmj.abstract import MovieScanner, SearchResult, NMJMovie, NMJPerson, \
	NMJ_ACTOR, NMJ_DIRECTOR, NMJImage
from nmj.cleaners import MovieCleaner
from nmj.utils import to_unicode


_LOGGER = logging.getLogger(__name__)

class MediaNotFound(Exception): pass
def date2string(toconvert):
	try:
		if isinstance(toconvert, str):
			return toconvert
		return toconvert.isoformat()
	except:
		_LOGGER.exception("Cannot convert '%s' of type %s in string", toconvert, type(toconvert))
		return ""
def date2yearstring(toconvert):
	try:
		if isinstance(toconvert, str):
			return toconvert[:4]
		return toconvert.strftime("%Y")
	except:
		_LOGGER.exception("Cannot convert '%s' of type %s in year string", toconvert, type(toconvert))
		return ""

class TMDBPoster(NMJImage):
	def __init__(self, url, size="w500"):
		super(TMDBPoster, self).__init__("https://image.tmdb.org/t/p/%s/%s" % (size, url))

class TMDBFanart(NMJImage):
	def __init__(self, url, size="original"):
		super(TMDBFanart, self).__init__("https://image.tmdb.org/t/p/%s/%s" % (size, url))

class TMDBScanner(MovieScanner):
	def __init__(self):
		super(TMDBScanner, self).__init__()
		#set_key("104e67f6ef05585ed35eec68f5cae0bf")
		#set_locale("fr", "fr")
		self.tmdb_config = tmdb.Configuration()

	def search(self, media):
		result = []
		title = self.clean(os.path.basename(os.path.splitext(media.path)[0]))
		try:
			searcher = tmdb.Search()
			searcher.movie(query=to_unicode(title), language='fr')
			for movie in searcher.results:
				try:
					_LOGGER.debug("Search result : %s", movie)
					result.append(SearchResult(movie["id"], TMDBPoster(movie["poster_path"]), movie["title"], media.path))
				except (AttributeError, KeyError):
					result.append(SearchResult(movie.id, None, movie.title, media.path))
		except TypeError:
			_LOGGER.exception("cannot search movie %s", title)
		except IndexError:
			_LOGGER.exception("cannot search movie %s", title)
		if not result:
			raise MediaNotFound("No information found for %s" % media)

		return result

	def print_details(self, object):
		_LOGGER.info("%s details:", object)
		_LOGGER.info("%s:", dir(object))
		for attr in dir(object):
			if not attr.startswith("__"):
				try:
					_LOGGER.info("%s = %s", attr, getattr(object, attr))
				except:
					_LOGGER.info("%s = Unknown value", attr)
				
	def get_details_from_id(self, media_id):
		_LOGGER.info("Retreiving details on movie %s", media_id)
		movie = tmdb.Movies(media_id)
		movie_info = movie.info(language='fr')
		images = movie.images(language='fr,en,null')
		credits = movie.credits()
		#pprint(movie_info)
		#self.print_details(movie_info)
		#self.print_details(movie_info.backdrop)
		#for size in movie_info.backdrop.sizes():
		#	_LOGGER.info("%s : %s", size, movie_info.backdrop.geturl(size))
		#[NMJImage(poster.geturl()) for poster in movie_info.backdrops or [movie_info.backdrop,] if poster]
		return NMJMovie(
			ttid=movie_info["imdb_id"],
			tmdbid=movie_info["id"],
			title=movie_info["title"],
			search_title=self.get_search_title(movie_info["title"]),
			year=date2yearstring(movie_info["release_date"]),
			release_date=date2string(movie_info["release_date"]),
			rating=movie_info["vote_average"],
			parental_control="",
			runtime=movie_info["runtime"]*60,
			synopsis=movie_info["overview"],
			posters=[TMDBPoster(poster["file_path"]) for poster in images["posters"]],
			thumbnails=[TMDBPoster(poster["file_path"], size="w154") for poster in images["posters"]],
			wallpapers=[TMDBFanart(poster["file_path"]) for poster in images["backdrops"]],
			persons=self._get_persons(credits),
			genres=[genre["name"] for genre in movie_info["genres"]]
		)

	def _get_crew(self, credits):
		return [NMJPerson(person["name"], person["job"]) for person in credits["crew"] if person["job"] == NMJ_DIRECTOR]

	def _get_persons(self, credits):
		return self._get_crew(credits) + [NMJPerson(actor["name"], NMJ_ACTOR) for actor in credits["cast"]]

	def get_default_details(self, media):
		return NMJMovie(
			ttid="",
			tmdbid="",
			title=media.title,
			search_title=self.get_search_title(media.title),
			year="9999",
			release_date="9999-01-01",
			rating="",
			parental_control="",
			runtime=0,
			synopsis="",
			posters=[],
			wallpapers=[],
			persons=[],
			genres=[]
		)

	def get_details(self, search_result):
		return self.get_details_from_id(search_result.search_id)

	def clean(self, title):
		return MovieCleaner().clean_title(title)

if __name__ == "__main__": # pragma: no cover
	from nmj.abstract import MediaFile

	logging.basicConfig(level=logging.DEBUG)
	scanner = TMDBScanner()
	#scanner.get_details(MovieSearchResult(160320, "http://d3gtl9l2a4fn1j.cloudfront.net/t/p/original/ejre3MX3Yf8vfjxjkhMV96nBJdp.jpg", "One Day...", "path"))
	result = scanner.get_details(scanner.search(MediaFile("Avatar.avi"))[0])
	pprint(result.wallpapers)
# 	for attr in dir(result):
# 		if not attr.startswith("_"):
# 			print("%s : %s" % (attr, getattr(result, attr)))


