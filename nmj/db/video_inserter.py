# -*- coding: utf-8 -*-
import datetime
import logging
from nmj.utils import print_details
import string

from nmj.abstract import NMJ_DIRECTOR, NMJ_ACTOR
from nmj.db.constants import MOVIE_TYPE, ALL_KNOWN
from nmj.tables import Videos, ShowsVideos, Shows, VideoGenres, VideoPersons, \
	ShowGroups, ShowsGenres, ShowsPersons, ShowGroupsShows, Synopsises, VideoPosters


_LOGGER = logging.getLogger(__name__)

class ShowFinder(object):
	def __init__(self, db, media_file):
		self.db = db
		self.media_file = media_file
		_LOGGER.debug("Create ShowFinder for media %s", media_file)
		self.video = self.show_video = self.show =None
		self.get_show_from_video()
		_LOGGER.debug("got media infos from DB: video (%s), show_videos (%s), show (%s)", self.video, self.show_video, self.show)

	def get_show_from_video(self):
		try:
			self.video = self.db.get_first(Videos, path=self.media_file.relative_path)
			self.show_video = self.db.get_first(ShowsVideos, videos_id=self.video.id)
			self.show = self.db.get_first(Shows, id=self.show_video.shows_id)
		except AttributeError:
			pass

class VideoDBInserter(ShowFinder):
	person_job_to_type={
		NMJ_DIRECTOR : "DIRECTOR",
		NMJ_ACTOR : "CAST",
	}
	def __init__(self, db, media_file):
		ShowFinder.__init__(self, db, media_file)
		self.video_id = self._insert_video(media_file)
		self.db.commit()

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
				hash="",
				size=0,
				three_d=0,
				resolution="",
				play_count=0,
			)
		else:
			return self.db.get_tables_items(Videos, path=media.relative_path)[0].id

	def need_update(self):
		if not self.show:
			return True
		synopsis = self.db.get_first(Synopsises, id=self.show.id)
		if not synopsis or not synopsis.summary:
			return True
		poster = self.db.get_first(VideoPosters, id=self.show.id)
		if not poster or not poster.poster or not poster.thumbnail or not poster.wallpaper:
			return True
		return False

	def _get_genres_ids(self, media_info):
		genres_ids=[]
		for genre in media_info.genres:
			db_genre = self.db.get_tables_items(VideoGenres, name=genre)
			if not db_genre:
				genres_ids.append(self.db.insert(VideoGenres, name=genre))
			else:
				genres_ids.append(db_genre[0].id)
		return genres_ids

	def _get_persons(self, media_info):
		for person in media_info.persons:
			db_person = self.db.get_tables_items(VideoPersons, name=person.name)
			if not db_person:
				person.set_db_id(self.db.insert(VideoPersons, name=person.name))
			else:
				person.set_db_id(db_person[0].id)
		return media_info.persons

	def _get_group(self, movie_info):
		print_details(movie_info)
		if not movie_info.search_title:
			return self.db.get_tables_items(ShowGroups, name="0-9")[0].id
		first_letter = movie_info.search_title[0]
		if first_letter.upper() in string.ascii_uppercase:
			return self.db.get_tables_items(ShowGroups, name=first_letter.upper())[0].id
		else:
			return self.db.get_tables_items(ShowGroups, name="0-9")[0].id

	def _insert_genres(self, show_id, media_info):
		for genre in self._get_genres_ids(media_info):
			self.db.insert(ShowsGenres, genres_id=genre, shows_id=show_id)

	def _insert_persons(self, show_id, media_info):
		for person in self._get_persons(media_info):
			self.db.insert(ShowsPersons, persons_id=person.db_id, shows_id=show_id, person_type=self.person_job_to_type[person.job])

	def _insert_groups(self, show_id, media_info, title_type=MOVIE_TYPE):
		group_id = self._get_group(media_info)
		if not self.db.contains(ShowGroupsShows, groups_id=group_id, shows_id=show_id):
			self.db.insert(ShowGroupsShows, groups_id=group_id, shows_id=show_id, title_type=title_type)


