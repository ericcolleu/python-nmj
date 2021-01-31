# -*- coding: utf-8 -*-
import logging
import os.path
import sys

from nmj.abstract import MediaFile, MOVIE_MEDIA_TYPE, TVSHOW_EPISODE_MEDIA_TYPE, \
	NMJImageDownloader
from nmj.db.constants import SHOW_TITLE_TYPE, SEASON_TITLE_TYPE
from nmj.db.movie_cleaner import MovieDBCleaner
from nmj.db.movie_inserter import MovieDBInserter
from nmj.db.proxy import DBProxy
from nmj.db.tvshow_inserter import TVShowDBInserter
from nmj.scanner_factory import ScannerFactory, ScannerNotFound, \
	UnknownMediaType
from nmj.scanners.tmdb import MediaNotFound, TMDBScanner
from nmj.scanners.tvdb3 import TTVDB3Scanner
from nmj.scanners.tvdb import TTVDBScanner
from nmj.tables import Videos, ShowsVideos, Shows, Synopsises, VideoPosters, \
	Episodes
from nmj.utils import to_unicode


_LOGGER = logging.getLogger(__name__)

def build_image_from_directory(width=200, height=200, directory="."):
	pass

class NMJMedia(object):
	def __init__(self, title, show_id, synopsis, poster, search_title=None, wallpaper=""):
		self.title = title
		self.search_title = search_title or title
		self.show_id = show_id
		self.synopsis = synopsis
		self.poster = poster
		self.wallpaper = wallpaper
		
	def jsondetails(self):
		return {
				"title" : to_unicode(self.title),
				"search_title" : to_unicode(self.search_title),
				"synopsis" : to_unicode(self.synopsis),
				"poster" : self.poster,
				"wallpaper" : self.wallpaper,
				"id" : self.show_id,
		}

class NMJEpisode(NMJMedia):
	def __init__(self, title, show_id, synopsis, poster, search_title=None, wallpaper=""):
		super(NMJEpisode, self).__init__(title, show_id, synopsis, poster, search_title=search_title, wallpaper=wallpaper)
		
class NMJSeason(NMJMedia):
	def __init__(self, title, show_id, synopsis, poster, search_title=None, wallpaper="", episodes=None):
		super(NMJSeason, self).__init__(title, show_id, synopsis, poster, search_title=search_title, wallpaper=wallpaper)
		self.episodes = episodes or []
		
	def jsondetails(self):
		result = super(NMJSeason, self).jsondetails()
		result.update({
				"episodes" : [episode.jsondetails() for episode in self.episodes]
		})
		return result
		
class NMJShow(NMJMedia):
	def __init__(self, title, show_id, synopsis, poster, search_title=None, wallpaper="", seasons=None):
		super(NMJShow, self).__init__(title, show_id, synopsis, poster, search_title=search_title, wallpaper=wallpaper)
		self.seasons = seasons or []

	def jsondetails(self):
		result = super(NMJShow, self).jsondetails()
		result.update({
				"seasons" : [season.jsondetails() for season in self.seasons]
		})
		return result

class NMJVideo(object):
	def __init__(self, video_id, relative_path, full_path):
		self.video_id = video_id
		self.relative_path = relative_path
		self.full_path = full_path
		self.basename = os.path.basename(relative_path)

class NMJUpdater(object):
	INDEX = """<html><head><meta name="Author" content="NMJ"></meta><meta HTTP-EQUIV="Content-Type" content="text/html; charset=UTF-8"></meta>
<script type="text/javascript">
<!--
fixedPath=location.href.replace("index.htm","?filter=7&page=1");
document.write('<meta HTTP-EQUIV="REFRESH" content="0; url='+fixedPath.replace("file:///opt/sybhttpd/localhost.drives","http://localhost.drives:8883")+'"></meta>');
-->
</script>
</head></html>"""
	inserters={
		MOVIE_MEDIA_TYPE : MovieDBInserter,
		TVSHOW_EPISODE_MEDIA_TYPE : TVShowDBInserter,
	}
	cleaners={
		MOVIE_MEDIA_TYPE : MovieDBCleaner,
	}
	def __init__(self, root_path, popcorn_path=""):
		self.scanner_factory = ScannerFactory()
		self.db = DBProxy(root_path, popcorn_path)
		self.base_dir = root_path
		index = os.path.join(self.base_dir, "index.htm")
		if not os.path.isfile(index):
			with open(index, "w+") as f:
				f.write(self.INDEX)
		if not self.base_dir.endswith("/"):
			self.base_dir+="/"
		self.scanner_factory.register_scanner(
			#TTVDBScanner(), 
			TTVDB3Scanner(), 
			TMDBScanner(),
		)

	def get_image(self):
		image_path=os.path.join(self.base_dir, "%s.jpg" % os.path.basename(self.base_dir[:-1]))
		_LOGGER.info("Checking if library image exists: %s", image_path)
		if os.path.isfile(image_path):
			return image_path
		else:
			return build_image_from_directory(width=200, height=200, directory=os.path.join(self.base_dir, "nmj_database", "media", "video", "thumbnail"))

	def scan_dir(self):
		result = []
		for root, dirs, files in os.walk(self.base_dir, followlinks=True):
			if self._ignore_dir(root, files):
				_LOGGER.debug("Ignoring directory %s", root)
				del files[:]
				del dirs[:]
				continue
			for filedir in dirs[:]:
				if filedir.startswith("."):
					dirs.remove(filedir)
			for video in files:
				result.append(self.create_media_file(os.path.join(root, video)))
			if "BDMV" in dirs:
				result.append(self.create_media_file(root))
		return result

	def _ignore_dir(self, root, files):
		return ".no_all.nmj" in files or ".no_video.nmj" in files or "nmj_database" in root

	def create_media_file(self, file_path):
		return MediaFile(file_path, relative_path=file_path[len(self.base_dir):])

	def get_scanner(self, media):
		try:
			return self.scanner_factory.get_scanner(media)
		except ScannerNotFound:
			_LOGGER.warning("No Scanner found for %s", media)
			return None

	def get_scanner_and_inserter(self, media):
		try:
			scanner = self.scanner_factory.get_scanner(media)
		except ScannerNotFound:
			_LOGGER.warning("No Scanner found for %s", media)
			return None, None
		db_inserter_class = self.inserters.get(media.media_type, None)
		if not db_inserter_class:
			_LOGGER.error("Don't known how to insert %s in database", media.media_type)
			return scanner, None
		return scanner, db_inserter_class(self.db, media)

	def need_update(self, media):
		scanner, db_inserter = self.get_scanner_and_inserter(media)
		if not scanner or not db_inserter:
			return True
		return db_inserter.need_update()

	def add_media(self, mediafile, media_id):
		scanner, db_inserter = self.get_scanner_and_inserter(mediafile)
		media_info = scanner.get_details_from_id(media_id)
		_LOGGER.info("Found informations: %s", media_info)
		media_info.set_base_dir(self.base_dir)
		media_info.set_media_file(mediafile)
		show_id = db_inserter.update_media_info(media_info)
		self.db.commit()
		return show_id

	def search_media_and_add(self, media):
		scanner, db_inserter = self.get_scanner_and_inserter(media)
		if not scanner or not db_inserter or not db_inserter.need_update():
			return
		try:
			results = scanner.search(media)
		except MediaNotFound:
			_LOGGER.exception("No information found on %s", media)
			media_info = scanner.get_default_details(media)
		else:
			media_info = scanner.get_details(results[0])
			_LOGGER.info("Found informations: %s", media_info)
		media_info.set_base_dir(self.base_dir)
		media_info.set_media_file(media)
		db_inserter.update_media_info(media_info)
		self.db.commit()

	def search(self, file_path):
		media = self.create_media_file(file_path)
		try:
			scanner = self.scanner_factory.get_scanner(media)
		except ScannerNotFound:
			_LOGGER.warning("No Scanner found for %s", media)
			return []
		try:
			return scanner.search(media)
		except MediaNotFound:
			_LOGGER.exception("No information found on %s", media)
			return []

	def clean_media(self, media):
		try:
			self.scanner_factory.update_media_type(media)
		except UnknownMediaType:
			_LOGGER.warning("Unknown media type %s", media)
			return
		_LOGGER.info("%s is a %s", media.path, media.media_type)
		db_cleaner_class = self.cleaners.get(media.media_type, None)
		if not db_cleaner_class:
			_LOGGER.error("Don't known how to clean %s in database", media.media_type)
			return
		db_cleaner = db_cleaner_class(self.db, media)
		db_cleaner.clean(self.base_dir)

	def clean(self):
		videos = self.db.get_tables_items(Videos)
		for video in videos:
			filepath = os.path.join(self.base_dir, video.path)
			if os.path.isfile(filepath):
				continue
			_LOGGER.info("%s should be clean", filepath)
			self.clean_media(MediaFile(filepath, relative_path=filepath[len(self.base_dir):]))

	def clean_names(self):
		medias = self.scan_dir()
		for media in medias:
			scanner = self.get_scanner(media)
			if scanner:
				title = scanner.clean(os.path.basename(os.path.splitext(media.path)[0]))
				new_path = os.path.join(media.location, "%s%s" % (title, media.extension))
				if new_path != media.path:
					#_LOGGER.info("Will rename %s into %s", media.path, new_path)
					os.rename(media.path, new_path)

	def get_episodes(self, tvshow, season):
		episodes_ids = []
		result = []
		for episode in self.db.get_tables_items(Episodes, series_id=tvshow.id, season_id=season.id):
			show = self.db.get_first(Shows, id=episode.episode_id)
			result.append(NMJEpisode(
				title=show.title,
				show_id=show.id,
				synopsis=self.db.get_first(Synopsises, id=show.id).summary,
				poster=self.db.get_first(VideoPosters, id=show.id).poster,
				search_title=show.search_title,
				wallpaper=self.db.get_first(VideoPosters, id=show.id).wallpaper,
			))
			episodes_ids.append(episode.episode_id)
		return result, episodes_ids
	
	def get_seasons(self, tvshow):
		seasons = []
		shows = []
		_LOGGER.debug("Retrieving seasons of %s", tvshow)
		table_seasons = self.db.get_tables_items(Shows, ttid=tvshow.ttid, title_type=SEASON_TITLE_TYPE)
		_LOGGER.debug("Seasons are %s", table_seasons)
		for show in table_seasons:
			_LOGGER.debug("Is %s a season of %s?", show, tvshow)
			if show.id != tvshow.id:
				_LOGGER.debug("YES, retreiving episodes now")
				episodes, to_skip = self.get_episodes(tvshow, show)
				seasons.append(NMJSeason(
					title=show.title,
					show_id=show.id,
					synopsis=self.db.get_first(Synopsises, id=show.id).summary,
					poster=self.db.get_first(VideoPosters, id=show.id).poster,
					search_title=show.search_title,
					wallpaper=self.db.get_first(VideoPosters, id=show.id).wallpaper,
					episodes=episodes
				))
				shows.append(show.id)
				shows.extend(to_skip)
				
		return seasons, shows
	
	def is_serie(self, show_id):
		show = self.db.get_first(Shows, id=show_id)
		return show.total_item > 1 and show.title_type == SHOW_TITLE_TYPE
	
	def get_shows(self):
		result = []
		to_skip = []
		for show in self.db.get_tables_items(Shows):
			try:
				if show.id in to_skip:
					_LOGGER.info("Skipping episode %s", show)
					continue
				seasons = []
				if show.total_item > 1:
					seasons, show_ids = self.get_seasons(show)
					to_skip.extend(show_ids)
				result.append(NMJShow(
					title=show.title,
					show_id=show.id,
					synopsis=self.db.get_first(Synopsises, id=show.id).summary,
					poster=self.db.get_first(VideoPosters, id=show.id).poster,
					search_title=show.search_title,
					wallpaper=self.db.get_first(VideoPosters, id=show.id).wallpaper,
					seasons=seasons,
				))
			except:
				_LOGGER.exception("Cannot get show infos (%s)", show)
		return result
	
	def get_show_id_from_title(self, title):
		return self.db.get_first(Shows, title=title).id
	
	def get_show(self, show_id):
		show = self.db.get_first(Shows, id=show_id)
		seasons = []
		if show.total_item > 1:
			seasons, _ = self.get_seasons(show)
		return NMJShow(
			title=show.title,
			show_id=show.id,
			synopsis=self.db.get_first(Synopsises, id=show.id).summary,
			poster=self.db.get_first(VideoPosters, id=show.id).poster,
			search_title=show.search_title,
			wallpaper=self.db.get_first(VideoPosters, id=show.id).wallpaper,
			seasons=seasons,
		)

	def get_video(self, show_id):
		showvideos = self.db.get_first(ShowsVideos, shows_id=show_id)
		video = self.db.get_first(Videos, id=showvideos.videos_id)
		return NMJVideo(
			video_id=video.id,
			relative_path=video.path,
			full_path=os.path.join(self.base_dir, video.path)
		)

	def get_details(self, show_id):
		show = self.db.get_first(Shows, id=show_id)
		showvideos = self.db.get_first(ShowsVideos, shows_id=show_id)
		video = self.db.get_first(Videos, id=showvideos.videos_id)
		scanner = self.get_scanner(MediaFile(video.path))
		return scanner.get_details_from_id(show.ttid)
			
	def change_poster(self, show_id, poster):
		downloader = NMJImageDownloader(posters=[poster,])
		downloader.set_base_dir(self.base_dir)
		downloader.download_poster()
		_LOGGER.debug("new poster is %s", downloader.poster_path)
		self.db.update(VideoPosters, show_id, poster=downloader.poster_path)
		
	def change_wallpaper(self, show_id, wallpaper):
		downloader = NMJImageDownloader(wallpapers=(wallpaper,))
		downloader.set_base_dir(self.base_dir)
		downloader.download_wallpaper()
		self.db.update(VideoPosters, show_id, wallpaper=downloader.wallpaper_path)
		
	
if __name__ == "__main__": # pragma: no cover
	logging.basicConfig(level=logging.ERROR)
	logging.getLogger(__name__).setLevel(logging.INFO)
	controller = NMJUpdater(sys.argv[1], sys.argv[2])
	medias = controller.scan_dir()
	_LOGGER.info("Found %s medias", len(medias))
	for rank, media in enumerate(medias):
		pass
