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
from nmj.utils import to_unicode, print_details
import pprint


_LOGGER = logging.getLogger(__name__)

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
                shows = self.web_api.search(to_unicode(params.get("show_name", title)), language='fr', cache=True)
                #pprint.pprint(shows)
                #_LOGGER.info("show : %s", show)
                # try:
                #     poster = self.get_posters(show)[0]
                # except IndexError:
                #     poster = ""
                # print_details(shows[0])
                for show in shows:
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

    def get_season_posters(self, obj, season):
        return [TVDBImage(banner.ThumbnailPath) for banner in sorted(obj.banner_objects, key=operator.attrgetter("Rating"), reverse=True) if banner.BannerType == "season" and banner.Season == season]
    def get_season_thumbnails(self, obj, season):
        return [NMJImage(banner.banner_url) for banner in sorted(obj.banner_objects, key=operator.attrgetter("Rating"), reverse=True) if banner.BannerType == "season" and banner.Season == season]
    def get_banners(self, obj, type="poster"):
        return [NMJImage(banner.banner_url) for banner in sorted(obj.banner_objects, key=operator.attrgetter("Rating"), reverse=True) if banner.BannerType == type]

    def get_thumbnails(self, obj, type="poster"):
        return [TVDBImage(banner.ThumbnailPath) for banner in sorted(obj.banner_objects, key=operator.attrgetter("Rating"), reverse=True) if banner.BannerType == type]

    def get_details(self, search_result):
        show = search_result.showdata
        show.update()
        #season = show[search_result.season]
        #ep = season[search_result.episode]
        #print_details(show.banner_objects[0], prefix="show")
        print_details(show, prefix="show")
        # print_details(season, prefix="season")
        # print_details(ep, prefix="episode")
        episode = search_result.showdata[search_result.season][search_result.episode]
        #print_details(episode)
        episode_title = episode.EpisodeName
        #str_actors = [] show.get("actors", "").strip("|")
        print_details(show.actor_objects[0])
        main_actors = [NMJPerson(actor.Name, NMJ_ACTOR, images=[TVDBImage(actor.Image)]) for actor in show.actor_objects]
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
                    release_date="%s" % show.FirstAired,
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
                    release_date="%s" % show.FirstAired,
                    rating=show.Rating,
                    posters=self.get_season_posters(show, season=search_result.season),
                    thumbnails=self.get_season_thumbnails(show, season=search_result.season),
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
                    release_date="%s" % episode.FirstAired,
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
    import sys
    from nmj.abstract import MediaFile

    logging.basicConfig(level=logging.INFO)
    scanner = TTVDB3Scanner()
    for video in sys.argv[1:]:
        search_result=scanner.search(MediaFile(video))
        result = scanner.get_details(search_result[0])
        # print_details(result)
        # print_details(result.show)
        result.season.posters[0].download(".", video)
        result.season.thumbnails[0].download(".", video)
        # print_details(result.episode)
