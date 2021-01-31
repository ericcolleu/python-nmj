import logging
import os.path
import shutil
import tempfile
import unittest
import pprint

from nmj.abstract import MediaFile
from nmj.db.constants import SHOW_TITLE_TYPE, SEASON_TITLE_TYPE, MOVIE_TYPE
from nmj.db.proxy import DBProxy
from nmj.tables import Videos, Shows, ShowsVideos, ShowsPersons, VideoPersons, \
	VideoPosters, Synopsises, VideoProperties, ShowGroupsShows, ShowsGenres
from nmj.updater import NMJUpdater

_LOGGER = logging.getLogger("test")

class NMJUpdaterTestCase(unittest.TestCase):
	def setUp(self):
		logging.basicConfig(level=logging.ERROR)
		logging.getLogger("nmj.updater").setLevel(logging.INFO)
		logging.getLogger("nmj.db.video_inserter").setLevel(logging.DEBUG)
		logging.getLogger("nmj.db.movie_cleaner").setLevel(logging.DEBUG)
		self.root_path = tempfile.mkdtemp()
		if not self.root_path.endswith("/"):
			self.root_path+="/"

	def tearDown(self):
		try:
			shutil.rmtree(self.root_path)  # delete directory
		except OSError as exc:
			if exc.errno != 2:  # code 2 - no such file or directory
				raise

	def create_file(self, filename):
		filepath=os.path.join(self.root_path, filename)
		if not os.path.isdir(os.path.dirname(filepath)):
			os.makedirs(os.path.dirname(filepath))
		open(filepath, "w+").close()
		return filepath

	def remove_file(self, filename):
		filepath=os.path.join(self.root_path, filename)
		os.remove(filepath)

	def get_show_from_video(self, db, path):
		try:
			video = db.get_tables_items(Videos, path=path)[0]
			show_video = db.get_tables_items(ShowsVideos, videos_id=video.id)[0]
			return db.get_tables_items(Shows, id=show_video.shows_id)[0]
		except IndexError:
			return None

	def _scan_file(self, filename):
		filepath=os.path.join(self.root_path, filename)
		open(filepath, "w+").close()
		controller = NMJUpdater(self.root_path, "popcorn/path/to/the/library")
		controller.search_media_and_add(MediaFile(filepath, relative_path=filepath[len(self.root_path):]))
		return controller

	def check_movie(self, filename, title):
		self._scan_file(filename)
		db = DBProxy(self.root_path)
		video = db.get_tables_items(Videos, path=filename)[0]
		show = db.get_tables_items(Shows)[0]
		self.assertEqual(show.title, title)
		self.assertTrue(db.contains(ShowsVideos, shows_id=show.id, videos_id=video.id))
		posters = db.get_tables_items(VideoPosters, id=show.id)
		self.assertTrue(posters)
		return db, video, show

	def test_01a(self):
		"New movie, Nominal case"
		db, _, show = self.check_movie("avatar.avi", "Avatar")
		director = db.get_tables_items(ShowsPersons, shows_id=show.id, person_type="DIRECTOR")[0]
		self.assertEqual(db.get_tables_items(VideoPersons, id=director.persons_id)[0].name, "James Cameron")
		actors = db.get_tables_items(ShowsPersons, shows_id=show.id, person_type="CAST")
		self.assertTrue(actors)

	def test_02a(self):
		"New movie, case with no release date"
		self.check_movie("one.day.avi", "Un jour")

	def test_03a(self):
		"New movie, case with movie details not found"
		self.check_movie("polop.pilip.avi", "polop.pilip")

	def test_03b(self):
		self.check_movie("Rendez-Vous En Terre Inconnue - Bruno Solo Chez Les Cavaliers Mongols.avi", "Rendez-Vous En Terre Inconnue - Bruno Solo Chez Les Cavaliers Mongols")

	def test_04a(self):
		"Updater: scan directory"
		library = [
			"some/path/to/avatar.avi",
			"gladiator.iso",
			"a/directory/wich/contains/star wars.mkv",
			"an/ignored/directory/.no_all.nmj",
			"an/ignored/directory/media.avi",
			"an/ignored/videos/directory/.no_video.nmj",
			"an/ignored/videos/directory/movie.mkv",
			"an/unknown/media/polop.pilip",
		]
		for filename in library:
			self.create_file(filename)
		updater = NMJUpdater(self.root_path, "popcorn/path/to/the/library")
		medias = updater.scan_dir()
		self.assertEqual(5, len(medias))
		for media in medias:
			self.assertIsInstance(media, MediaFile)
			updater.search_media_and_add(media)
		db = DBProxy(self.root_path)
		videos = db.get_tables_items(Videos)
		self.assertEqual(3, len(videos))

	def __check_show_attributes(self, show, title, search_title, total_item, year, title_type):
		self.assertEqual(show.title, title)
		self.assertEqual(show.search_title, search_title)
		self.assertEqual(show.total_item, total_item)
		self.assertEqual(show.year, year)
		self.assertEqual(show.title_type, title_type)

	def test_05a(self):
		"Updater : New tvshow episode"
		filename = "The.Mentalist.S01E01.FRENCH.DVDRip.XviD-JMT.avi"
		self._scan_file(filename)
		db = DBProxy(self.root_path)
		videos = db.get_tables_items(Videos, path=filename)
		shows_videos = db.get_tables_items(ShowsVideos)
		self.assertEqual(1, len(videos))
		self.assertEqual(1, len(shows_videos))
		show, season, episode = db.get_tables_items(Shows)

		self.assertEqual(shows_videos[0].shows_id, episode.id)
		self.assertEqual(shows_videos[0].videos_id, videos[0].id)
		self.__check_show_attributes(show, "Mentalist", "Mentalist", 1, "2008", SHOW_TITLE_TYPE)
		self.__check_show_attributes(season, "Mentalist Saison 1", "Mentalist Saison 1", 1, "2008", SEASON_TITLE_TYPE)
		self.__check_show_attributes(episode, "John le Rouge", "John le Rouge", 1, "2008", MOVIE_TYPE)

	def test_06a(self):
		"Updater : Remove movie"
		updater = self._scan_file("avatar.avi")
		self.remove_file("avatar.avi")
		updater.clean()
		db = DBProxy(self.root_path)
		self.assertEqual(0, len(db.get_tables_items(Shows)))
		self.assertEqual(0, len(db.get_tables_items(Videos)))
		self.assertEqual(0, len(db.get_tables_items(Synopsises)))
		self.assertEqual(0, len(db.get_tables_items(VideoPosters)))
		self.assertEqual(0, len(db.get_tables_items(VideoProperties)))
		self.assertEqual(0, len(db.get_tables_items(ShowGroupsShows)))
		self.assertEqual(0, len(db.get_tables_items(ShowsGenres)))
		self.assertEqual(0, len(db.get_tables_items(ShowsPersons)))
		
	def test_07a(self):
		"Updater : multiple tvshows"
		filenames = [
			"The.Mentalist.S01E01.FRENCH.DVDRip.XviD-JMT.avi",
			"Person.of.interest.s01e02.mkv",
#			"Heroes.s01e22.avi",
		]
		[self._scan_file(filename) for filename in filenames]
		db = DBProxy(self.root_path)
		videos = db.get_tables_items(Videos)
		shows_videos = db.get_tables_items(ShowsVideos)

		# self.assertEqual(1, len(videos))
		# self.assertEqual(1, len(shows_videos))
		_LOGGER.info("Shows : %s", pprint.pformat(db.get_tables_items(Shows)))
		_LOGGER.info("videos : %s", videos)
		_LOGGER.info("show_videos : %s", shows_videos)
		# self.assertEqual(shows_videos[0].shows_id, episode.id)
		# self.assertEqual(shows_videos[0].videos_id, videos[0].id)
		# self.__check_show_attributes(show, "Mentalist", "Mentalist", 1, "2008", SHOW_TITLE_TYPE)
		# self.__check_show_attributes(season, "Mentalist Saison 1", "Mentalist Saison 1", 1, "2008", SEASON_TITLE_TYPE)
		# self.__check_show_attributes(episode, "John le Rouge", "John le Rouge", 1, "2008", MOVIE_TYPE)
		


if __name__ == "__main__":
	logging.basicConfig(level=logging.ERROR)
	#logging.getLogger("nmj.updater").setLevel(logging.INFO)
	logging.getLogger("test").setLevel(logging.INFO)
	unittest.main()

