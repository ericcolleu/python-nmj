import unittest

from nmj.cleaners import MovieCleaner, TVShowCleaner


class MovieCleanerTestCase(unittest.TestCase):
	def setUp(self):
		super(MovieCleanerTestCase, self).setUp()
		self.cleaner = MovieCleaner()

	def test_01a(self):
		self.__test_cleaning("The A Team", "the a team")

	def test_02a(self):
		self.__test_cleaning("Horrible.Bosses.MULTi.1080p.BluRay.x264-4kHD", "horrible bosses")

	def test_03a(self):
		self.__test_cleaning("Ice.Age.A.Mammoth.Christmas.FRENCH.720p.WEB-DL.DD2.0.H.264-NeXu14", "ice age a mammoth christmas")

	def test_04a(self):
		self.__test_cleaning("LA FEE CLOCHETTE L'EXPEDITION FEERIQUE.LiMiTED.French.BRRip.XviD.AC3-TFTD", "la fee clochette l'expedition feerique")

	def test_05a(self):
		self.__test_cleaning("Les.Aristochats.1970.TRUEFRENCH.1080p.HDTV.x264-BigF", "les aristochats")

	def test_06a(self):
		self.__test_cleaning("2012", "2012")

	def test_07a(self):
		self.__test_cleaning("LOL truefrench", "lol")

	def test_08a(self):
		self.__test_cleaning("Avatar.2011", "avatar")

	def test_09a(self):
		self.__test_cleaning("Avatar (2011)", "avatar")

	def test_10a(self):
		self.__test_cleaning("[RipperTeam]_Avatar_2011_DVDRip_TRUEFRENCH", "avatar")

	def test_11a(self):
		self.__test_cleaning("Thats.My.Boy.2012.FRENCH.BRRiP.XviD.AC3-AUTOPSiE", "thats my boy")

	def test_12a(self):
		self.__test_cleaning("Quantum.Of.Solace.TRUEFRENCH.SUBFORCED.DVDRip.XviD.AC3-PoneyClub", "quantum of solace")

	def __test_cleaning(self, basename, expected_clean_title):
		self.assertEqual(expected_clean_title, self.cleaner.clean_title(basename))

if __name__ == "__main__":
	unittest.main()
