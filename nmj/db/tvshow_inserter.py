# -*- coding: utf-8 -*-
import datetime
import logging

from nmj.db.constants import SHOW_TITLE_TYPE, ALL_KNOWN, SEASON_TITLE_TYPE, \
	MOVIE_TYPE
from nmj.db.video_inserter import VideoDBInserter
from nmj.tables import Shows, VideoProperties, VideoPosters, Synopsises, \
	ShowsVideos, Episodes


_LOGGER = logging.getLogger(__name__)

class TVShowDBInserter(VideoDBInserter):
	def _insert_show(self, media_info):
		shows = self.db.get_tables_items(Shows, ttid=media_info.show.ttid, title_type=SHOW_TITLE_TYPE)
		if not shows:
			release_date = datetime.datetime.strptime(media_info.show.release_date, "%Y-%m-%d")
			show_id = self.db.insert(
				Shows,
				title=media_info.show.title,
				search_title=media_info.show.search_title,
				total_item=0,
				year=release_date.strftime("%Y"),
				release_date=media_info.show.release_date, #.strftime("%Y-%m-%d"),
				rating=media_info.show.rating,
				create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				ttid=media_info.show.ttid,
				update_state=ALL_KNOWN,
				title_type=SHOW_TITLE_TYPE,
				content_ttid=media_info.show.content_id,
				three_d="0",
			)
			self.db.insert(VideoProperties, id=show_id, runtime=0)
			self.db.insert(VideoPosters, id=show_id, type="0", create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			self.db.insert(Synopsises, id=show_id, summary=media_info.show.synopsis)

			self._insert_genres(show_id, media_info.show)
			self._insert_persons(show_id, media_info.show)
			self._insert_groups(show_id, media_info.show, title_type=SHOW_TITLE_TYPE)
			return show_id
		else:
			return shows[0].id

	def _insert_season(self, media_info):
		seasons = self.db.get_tables_items(Shows, title=media_info.season.title, title_type=SEASON_TITLE_TYPE)
		if not seasons:
			release_date = datetime.datetime.strptime(media_info.season.release_date, "%Y-%m-%d")
			season_id = self.db.insert(
				Shows,
				title=media_info.season.title,
				search_title=media_info.season.search_title,
				total_item=0,
				year=release_date.strftime("%Y"),
				release_date=release_date.strftime("%Y-%m-%d"),
				rating=media_info.season.rating,
				create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				ttid=media_info.season.ttid,
				update_state=ALL_KNOWN,
				title_type=SEASON_TITLE_TYPE,
				content_ttid=media_info.season.content_id,
				three_d="0",
			)
			self.db.insert(VideoProperties, id=season_id, runtime=0)
			self.db.insert(VideoPosters, id=season_id, type="0", create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			self.db.insert(Synopsises, id=season_id, summary=media_info.season.synopsis)
			self._insert_genres(season_id, media_info.season)
			self._insert_persons(season_id, media_info.season)
			self._insert_groups(season_id, media_info.season, title_type=SEASON_TITLE_TYPE)
			return season_id
		else:
			return seasons[0].id

	def _insert_episode(self, media_info, show_id, season_id):
		if not self.show:
			release_date = datetime.datetime.strptime(media_info.episode.release_date, "%Y-%m-%d")
			db_episode_id = self.db.insert(
				Shows,
				title=media_info.episode.title,
				search_title=media_info.episode.search_title,
				total_item=1,
				year=release_date.strftime("%Y"),
				release_date=release_date.strftime("%Y-%m-%d"),
				rating=media_info.episode.rating,
				create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				ttid=media_info.episode.ttid,
				update_state=ALL_KNOWN,
				title_type=MOVIE_TYPE,
				content_ttid=media_info.episode.content_id,
				three_d="0",
			)
			show=self.db.get_tables_items(Shows, ttid=media_info.show.ttid, title_type=SHOW_TITLE_TYPE)[0]
			season=self.db.get_tables_items(Shows, title=media_info.season.title, title_type=SEASON_TITLE_TYPE)[0]
			self.db.update(Shows, show_id, total_item=show.total_item+1)
			self.db.update(Shows, season_id, total_item=season.total_item+1)

			self.db.insert(ShowsVideos, shows_id=db_episode_id, videos_id=self.video_id)
			self.db.insert(Synopsises, id=db_episode_id, summary=media_info.episode.synopsis)
			self.db.insert(VideoProperties, id=db_episode_id, runtime=media_info.episode.runtime)
			self.db.insert(VideoPosters, id=db_episode_id, type="0", create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			self.db.insert(Episodes, episode_id=db_episode_id, series_id=show_id, season_id=season_id, season=media_info.season.rank, episode=media_info.episode.rank)
			self._insert_genres(db_episode_id, media_info.episode)
			self._insert_persons(db_episode_id, media_info.episode)
			return db_episode_id
		else:
			return self.show.id

	def _insert_images(self, show_id, media_info):
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
		if self.db.contains(Synopsises, id=show_id, summary="") and hasattr(media_info, "synopsis"):
			self.db.update(Synopsises, show_id, summary=media_info.synopsis)

	def update_media_info(self, media_info):
		try:
			_LOGGER.info("Insert %s in DB", media_info)
			show_id = self._insert_show(media_info)
			self._insert_images(show_id, media_info.show)
			season_id = self._insert_season(media_info)
			self._insert_images(season_id, media_info.season)
			self._insert_episode(media_info, show_id, season_id)
			return show_id
		finally:
			self.db.commit()


