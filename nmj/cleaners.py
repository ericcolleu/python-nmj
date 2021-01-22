import logging
import re

_LOGGER = logging.getLogger(__name__)

clean_re = "[ _\,\.\(\)\[\]\-](\
ac3.*|avc|\
bigf|bluray.*|blueray|bd5|brrip|bdrip|\
cam|custom|\
dts|dc|dl|divx|divx5|dsr|dsrip|dutch|dvdrip|dvdscr|dvdscreener|dvdivx|dvd|dd2\ 0|dxva|\
fragment|frenh|fs|forcebleue|\
german|\
hdtv|hdrip|hdtvrip|hrhd|hrhdtv|hddvd|hd|\
internal|\
klinehd|\
legion|lechti|limited|\
multilang|multisubs|multi|\
nerdhd|nfofix|ntsc|\
ogg|ogm\
|pal|patologik|pdtv|proper\
read\.nfo|repack|remux|rerip|retail|rld|r3|r5|\
screener|seth|slimhd|stv|svcd|swedish|ssl|\
tftd|trsiel|\
unrated|\
vostfr|\
wazatt|ws|\
telesync|ts|telecine|tc|\
4khd|480p|480i|576p|576i|720p.*|720i|1080p.*|1080p\-.*1080i|\
x264.*|h264|h\ 264|h\ 264\ .*|264|web|web\-dl|xvid|xvidvd|xxx|www.*|cd[1-9]|\[.*\])"

class TitleCleaner(object):
	def __init__(self, pattern_cleaners):
		self.__pattern_cleaners = pattern_cleaners

	def clean_title(self, title):
		title = title.lower()
		for pattern, replace in self.__pattern_cleaners:
			# _LOGGER.debug("clean title %s with pattern %s, and replace with |%s|", title, pattern, replace)
			title = re.sub(pattern, replace, title)
		_LOGGER.info("Got clean title: %s", title)
		return title.strip()

class TVShowCleaner(TitleCleaner):
	clean_strings_pattern = [
		("([\.])", " "),
#		("[s]\d\d[e]\d\d([\w\s]+)", ""),
		("([_])", " "),
		(clean_re + "([_\,\.\(\)\[\]\-]|$)", ""),
		(clean_re, ""),
		("(french.*|truefrench.*|www.*|xvid.*|subforced.*|dvdrip.*|brrip.*)", ""),
		("(\[.*\])", ""),
		("( 19[0-9][0-9]|20[0-1][0-9] [\w\s]+)", ""),
	]
	def __init__(self):
		TitleCleaner.__init__(self, self.clean_strings_pattern)

class MovieCleaner(TitleCleaner):
	clean_strings_pattern = [
		("([\.-])", " "),
		("([_])", " "),
		("\s(\d\d\d\d.*)", ""),
		("([\(\)])", " "),
		(clean_re + "([_\,\.\(\)\[\]\-]|$)", ""),
		(clean_re, ""),
		("(french.*|truefrench.*|www.*|xvid.*|subforced.*|dvdrip.*)", ""),
		("(\[.*\])", ""),
		("[. ]+(19[0-9][0-9]|20[0-1][0-9])", ""),
	]
	def __init__(self):
		TitleCleaner.__init__(self, self.clean_strings_pattern)

