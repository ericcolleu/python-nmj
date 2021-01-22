import logging
import unittest

from nmj.abstract import MediaFile
from nmj.scanners.tvdb import TTVDBScanner


class TTVDBScannerTestCase(unittest.TestCase):
	def setUp(self):
		super(TTVDBScannerTestCase, self).setUp()
		logging.basicConfig(level=logging.DEBUG)
		self.scanner = TTVDBScanner()

	def test_01a(self):
		self.__test_cleaning("Naruto_-_228_", "naruto", episode="228")

	def test_02a(self):
		self.__test_cleaning("Lost S01E01", "lost", season="01", episode="01")

	def test_03a(self):
		self.__test_cleaning("FlashForward S01E01", "flashforward", season="01", episode="01")

	def test_05a(self):
		self.__test_cleaning("minuscule s04", "minuscule", season="04")

	def test_06a(self):
		self.__test_cleaning("minuscule s01e03", "minuscule", season="01", episode="03")

	def test_11a(self):
		self.__test_cleaning("The.Mentalist.S02E21.FRENCH.LD.HDTV.XviD-JMT", "the mentalist", season="02", episode="21")

	def __test_cleaning(self, basename, show, season="01", episode="01"):
		details = self.scanner.get_details_from_media(MediaFile(basename, basename))
		self.assertEqual(show, details.get("show_name", ""))
		self.assertEqual(season, details.get("season", "01"))
		self.assertEqual(episode, details.get("episode", "01"))
