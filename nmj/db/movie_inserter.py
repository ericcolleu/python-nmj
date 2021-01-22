# -*- coding: utf-8 -*-
import datetime
import logging

from nmj.db.constants import MOVIE_TYPE, ALL_KNOWN
from nmj.db.video_inserter import VideoDBInserter
from nmj.tables import Videos, Shows, ShowsVideos, Synopsises, VideoProperties, \
	VideoPosters


_LOGGER = logging.getLogger(__name__)

class MovieDBInserter(VideoDBInserter):
	def _insert_video(self, media):
		if not self.db.contains(Videos, path=media.relative_path):
			return self.db.insert(
				Videos,
				path=media.relative_path,
				file_type=MOVIE_TYPE,
				scan_dirs_id=1,
				create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				update_state=ALL_KNOWN,
				file_status="",
				hash="boring info",
				size=0,  # s.path.getsize(filepath),
				three_d=0,
				resolution="",
				play_count=0,
			)
		else:
			return self.db.get_tables_items(Videos, path=media.relative_path)[0].id

	def _insert_show(self, media_info):
		show_id = self.db.insert(
			Shows,
			ttid=media_info.ttid,
			title=media_info.title,
			search_title = media_info.search_title,
			total_item=1,
			year=media_info.year,
			release_date=media_info.release_date,
			rating=media_info.rating,
			runtime=media_info.runtime,
			create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
			update_state="4",
			title_type="1",
			content_ttid=media_info.content_ttid,
			three_d="0",
		)
		_LOGGER.debug("SHOW ID %s(%s)", show_id, type(show_id))
		self.db.insert(ShowsVideos, shows_id=show_id, videos_id=self.video_id)
		self.db.insert(Synopsises, id=show_id, summary=media_info.synopsis)
		self.db.insert(VideoProperties, id=show_id, runtime=media_info.runtime)
		self.db.insert(VideoPosters, id=show_id, type="0", create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		self._insert_genres(show_id, media_info)
		self._insert_persons(show_id, media_info)
		self._insert_groups(show_id, media_info)
		return show_id

	def update_media_info(self, media_info):
		try:
			if not self.show:
				show_id = self._insert_show(media_info)
			else:
				show_id = self.show.id
			db_poster = self.db.get_tables_items(VideoPosters, id=show_id)[0]
			if not db_poster.poster:
				media_info.download_poster()
				self.db.update(VideoPosters, show_id, poster=media_info.poster_path)
			if not db_poster.thumbnail:
				media_info.download_thumbnail()
				self.db.update(VideoPosters, show_id, thumbnail=media_info.thumbnail_path)
			if not db_poster.wallpaper:
				media_info.download_wallpaper()
				self.db.update(VideoPosters, show_id, wallpaper=media_info.wallpaper_path)
			if self.db.contains(Synopsises, id=show_id, summary=""):
				self.db.update(Synopsises, show_id, summary=media_info.synopsis)
			return show_id
		finally:
			self.db.commit()


