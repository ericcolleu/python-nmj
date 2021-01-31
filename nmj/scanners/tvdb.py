# -*- coding: utf-8 -*-
import datetime
import logging
import re
import operator

import tvdb_api

from nmj.abstract import TVShowScanner, NMJTVShow, TVShowSearchResult, \
	NMJTVMediaInfo, NMJTVShowSeason, NMJTVShowEpisode, NMJPerson, NMJ_ACTOR,\
	NMJ_DIRECTOR, NMJImage, AbstractNotImplemented
from nmj.cleaners import TVShowCleaner
from nmj.scanners.tmdb import MediaNotFound
from nmj.utils import to_unicode
import pprint


_LOGGER = logging.getLogger(__name__)

def print_details(object, prefix=""):
    _LOGGER.info("%s details:", object)
    _LOGGER.info("%s:", dir(object))
    for attr in dir(object):
        if not attr.startswith("__"):
            try:
                _LOGGER.info("%s %s = %s", prefix, attr, getattr(object, attr))
            except:
                _LOGGER.info("%s : %s = Unknown value", prefix, attr)
            

class TVDBImage(NMJImage):
	def __init__(self, url, size="w500"):
		super(TVDBImage, self).__init__("http://thetvdb.com/banners/%s" % url)


class TTVDBScanner(TVShowScanner):
    def __init__(self):
        super(TTVDBScanner, self).__init__()
        self.web_api = tvdb_api.Tvdb(apikey="5BA46DFDB0AB740E", actors=True, banners=True, language='fr')

    def search(self, media): # pragma no cover
        title = self.clean(media.title)
        for regexp in self.compiled_regexp:
            match = regexp.match(title)
            if match:
                params = match.groupdict()
                shows = self.web_api.search(to_unicode(params.get("show_name", title)))
                #shows = self.web_api.search(to_unicode(params.get("show_name", title)), language='fr')
                #pprint.pprint(shows)
                #_LOGGER.info("show : %s", show)
                # try:
                #     poster = self.get_posters(show)[0]
                # except IndexError:
                #     poster = ""
                for show in shows:
                    #print_details(show)
                    return [TVShowSearchResult(
                        show["id"],
                        TVDBImage(show["image"]),
                        show["seriesName"],
                        media.path,
                        season=int(params.get("season", "1")),
                        episode=int(params.get("episode", "1")),
                        showdata=show,
                    ),]
        raise MediaNotFound("No information found for %s" % media)

    def get_banners(self, obj, type_="poster"):
        if type_ not in obj:
            type_ = list(obj.keys())[0]
        banners_data = []
        [ banners_data.extend(banner.values()) for resolution, banner in obj[type_].items() if resolution != "raw"]
        return [NMJImage(banner["_bannerpath"]) for banner in banners_data]

    def get_thumbnails(self, obj, type_="poster"):
        if type_ not in obj:
            type_ = list(obj.keys())[0]
        raw_data_list = obj[type_]["raw"]
        return [TVDBImage(banner["thumbnail"]) for banner in raw_data_list]

    def get_details(self, search_result):
        showdata = search_result.showdata
        show = self.web_api[showdata["seriesName"]]
        show.update()
        #print_details(showdata, prefix = "showdata")
        #print_details(show, prefix = "show")
        #season = show[search_result.season]
        # print_details(season, prefix="season")
        # for k,v in season.items():
        #     print("%s : %s" % (k,v))
        episode = show[search_result.season][search_result.episode]
        #print_details(episode, prefix="episode")
        # for k,v in episode.items():
        #     print("%s : %s" % (k,v))
        episode_title = episode["episodeName"]
        #str_actors = [] show.get("actors", "").strip("|")
        main_actors = [NMJPerson(actor["name"], NMJ_ACTOR) for actor in show["_actors"]]
        director = [NMJPerson(director, NMJ_DIRECTOR) for director in episode["directors"]]
        #str_guests = episode.get("gueststars", None) or ""
        guests = [NMJPerson(actor, NMJ_ACTOR) for actor in episode["guestStars"]]
        #str_genres = show.get("genre", "").strip("|")
        genres = show["genre"]
        banners = show["_banners"]
        # pprint.pprint(banners)
        # print(banners.keys())
        #pprint.pprint(show)
        return NMJTVMediaInfo(
                show = NMJTVShow(
                    ttid = show["imdbId"],
                    content_id = show["id"],
                    title=show["seriesName"],
                    search_title=self.get_search_title(show["seriesName"]),
                    release_date=show["firstAired"],
                    rating=show["siteRating"],
                    posters=self.get_banners(banners, type_="season"),
                    thumbnails=self.get_thumbnails(banners, type_="season"),
                    wallpapers=self.get_banners(banners, type_="fanart"),
                    persons=main_actors + director,
                    genres=genres,
                    synopsis=show["overview"],
                ),
                season = NMJTVShowSeason(
                    ttid = show["imdbId"],
                    content_id = show["id"],
                    title = "%s Saison %s" % (show["seriesName"], search_result.season),
                    rank = search_result.season,
                    release_date=show["firstAired"],
                    rating=show["rating"],
                    posters=self.get_banners(banners, type_="season"),
                    thumbnails=self.get_thumbnails(banners, type_="poster"),
                    wallpapers=self.get_banners(banners, type_="fanart"),
                    persons=main_actors + director,
                    genres=genres,
                    synopsis=show["overview"],
                ),
                episode = NMJTVShowEpisode(
                    ttid = show["imdbId"],
                    content_id = show["id"],
                    title = episode_title,
                    rank = search_result.episode,
                    search_title = self.get_search_title(episode_title),
                    release_date=episode["firstAired"],
                    rating=episode["rating"],
                    synopsis=episode["overview"],
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
    scanner = TTVDBScanner()
    search_res = scanner.search(MediaFile(sys.argv[1]))
    result = scanner.get_details(search_res[0])
    # print(result)
    print(type(result.show.release_date))
    # result.show.download_thumbnail()
    #result.show.download_wallpapers()
