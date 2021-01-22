# -*- coding: utf-8 -*-
import datetime
import logging
import re
import operator

from pytvdbapi import api

from nmj.abstract import TVShowScanner, NMJTVShow, TVShowSearchResult, \
	NMJTVMediaInfo, NMJTVShowSeason, NMJTVShowEpisode, NMJPerson, NMJ_ACTOR,\
	NMJ_DIRECTOR, NMJImage, AbstractNotImplemented
from nmj.cleaners import TVShowCleaner
from nmj.scanners.tmdb import MediaNotFound
from nmj.utils import to_unicode
import pprint


_LOGGER = logging.getLogger(__name__)

def print_details(object):
    _LOGGER.info("%s details:", object)
    _LOGGER.info("%s:", dir(object))
    for attr in dir(object):
        if not attr.startswith("__"):
            try:
                _LOGGER.info("%s = %s", attr, getattr(object, attr))
            except:
                _LOGGER.info("%s = Unknown value", attr)
            

class TVDBImage(NMJImage):
	def __init__(self, url, size="w500"):
		super(TVDBImage, self).__init__("http://thetvdb.com/banners/%s" % url)


class TTVDB3Scanner(TVShowScanner):
    def __init__(self):
        super(TTVDB3Scanner, self).__init__()
        self.web_api = api.TVDB("5BA46DFDB0AB740E", actors=True, banners=True)

    def search(self, media): # pragma no cover
        title = self.clean(media.title)
        for regexp in self.compiled_regexp:
            match = regexp.match(title)
            if match:
                params = match.groupdict()
                shows = self.web_api.search(to_unicode(params.get("show_name", title)), language='fr')
                #pprint.pprint(shows)
                #_LOGGER.info("show : %s", show)
                # try:
                #     poster = self.get_posters(show)[0]
                # except IndexError:
                #     poster = ""
                for show in shows:
                    #print_details(show)
                    return [TVShowSearchResult(
                        show.id,
                        TVDBImage(show.banner),
                        show.SeriesName,
                        media.path,
                        season=int(params.get("season", "1")),
                        episode=int(params.get("episode", "1")),
                        showdata=show,
                    ),]
        raise MediaNotFound("No information found for %s" % media)

    def get_banners(self, obj, type="poster"):
        return [NMJImage(banner.banner_url) for banner in sorted(obj.banner_objects, key=operator.attrgetter("Rating"), reverse=True) if banner.BannerType == type]

    def get_thumbnails(self, obj, type="poster"):
        return [TVDBImage(banner.ThumbnailPath) for banner in sorted(obj.banner_objects, key=operator.attrgetter("Rating"), reverse=True) if banner.BannerType == type]

    def get_details(self, search_result):
        show = search_result.showdata
        show.update()
        #print_details(show)
        episode = search_result.showdata[search_result.season][search_result.episode]
        #print_details(episode)
        episode_title = episode.EpisodeName
        #str_actors = [] show.get("actors", "").strip("|")
        main_actors = [NMJPerson(actor, NMJ_ACTOR) for actor in show.Actors]
        director = [NMJPerson(director, NMJ_DIRECTOR) for director in episode.Director]
        #str_guests = episode.get("gueststars", None) or ""
        guests = [NMJPerson(actor, NMJ_ACTOR) for actor in episode.GuestStars]
        #str_genres = show.get("genre", "").strip("|")
        genres = show.Genre
        #pprint.pprint(show)
        return NMJTVMediaInfo(
                show = NMJTVShow(
                    ttid = show.IMDB_ID,
                    content_id = show.id,
                    title=show.SeriesName,
                    search_title=self.get_search_title(show.SeriesName),
                    release_date=show.FirstAired,
                    rating=show.Rating,
                    posters=self.get_banners(show, type="poster"),
                    thumbnails=self.get_thumbnails(show, type="poster"),
                    wallpapers=self.get_banners(show, type="fanart"),
                    persons=main_actors + director,
                    genres=genres,
                    synopsis=show.Overview,
                ),
                season = NMJTVShowSeason(
                    ttid = show.IMDB_ID,
                    content_id = show.id,
                    title = "%s Saison %s" % (show.SeriesName, search_result.season),
                    rank = search_result.season,
                    release_date=show.FirstAired,
                    rating=show.Rating,
                    posters=self.get_banners(show, type="season"),
                    thumbnails=self.get_thumbnails(show, type="poster"),
                    wallpapers=self.get_banners(show, type="fanart"),
                    persons=main_actors + director,
                    genres=genres,
                    synopsis=show.Overview,
                ),
                episode = NMJTVShowEpisode(
                    ttid=episode.IMDB_ID,
                    content_id=episode.id,
                    title = episode_title,
                    rank = search_result.episode,
                    search_title = self.get_search_title(episode_title),
                    release_date=episode.FirstAired,
                    rating=episode.Rating,
                    synopsis=episode.Overview,
                    persons=main_actors + guests + director,
                    genres=genres,
                    runtime=0,
                ),
        )

    def clean(self, title):
        return TVShowCleaner().clean_title(title)


if __name__ == "__main__": # pragma: no cover
    from nmj.abstract import MediaFile

    logging.basicConfig(level=logging.DEBUG)
    scanner = TTVDB3Scanner()
    result = scanner.get_details(scanner.search(MediaFile("person.of.interest.s01e01.avi"))[0])
    print(result)