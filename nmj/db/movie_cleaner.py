import logging
import os

from nmj.db.video_inserter import ShowFinder
from nmj.tables import VideoPosters, VideoProperties, Synopsises, ShowsVideos, \
	Shows, Videos, ShowsGenres, ShowsPersons, ShowGroupsShows


_LOGGER = logging.getLogger(__name__)
def safely_clean_file(filename):
	try:
		os.remove(filename)
	except:
		_LOGGER.exception("Cannot remove %s", filename)
class MovieDBCleaner(ShowFinder):
	def __init__(self, db, media):
		ShowFinder.__init__(self, db, media)

	def clean(self, base_dir):
		if not self.show:
			return
		[self.db.delete(to_remove) for to_remove in self.get_db_objects_from_show_id()]
		for table in [ShowsGenres, ShowsPersons, ShowGroupsShows]:
			for element in self.db.get_tables_items(table, shows_id=self.show.id):
				self.db.delete(element)
		poster = self.db.get_first(VideoPosters, id=self.show.id)
		if poster.poster:
			safely_clean_file(os.path.join(base_dir, poster.poster))
		if poster.thumbnail:
			safely_clean_file(os.path.join(base_dir, poster.thumbnail))
		if poster.wallpaper:
			safely_clean_file(os.path.join(base_dir, poster.wallpaper))
		self.db.delete(poster)
		self.db.commit()

	def get_db_objects_from_show_id(self):
		result = []
		for table in [VideoProperties, Synopsises, ShowsVideos, Shows, Videos]:
			_LOGGER.debug("get item from %s", table)
			try:
				result.append(self.db.get_first(table, id=self.show.id))
			except:
				_LOGGER.exception("Cannot get first %s with id=%s", table, self.show)
		return result


