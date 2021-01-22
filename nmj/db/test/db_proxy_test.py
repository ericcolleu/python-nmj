import shutil
import tempfile
import unittest

from nmj.abstract import MediaFile
from nmj.db.movie_inserter import MovieDBInserter
from nmj.db.proxy import DBProxy
from nmj.tables import DbVersion, Videos, Shows


class DBProxyTestCase(unittest.TestCase):
	def setUp(self):
		self.root_path = tempfile.mkdtemp()

	def tearDown(self):
		try:
			shutil.rmtree(self.root_path)  # delete directory
		except OSError as exc:
			if exc.errno != 2:  # code 2 - no such file or directory
				raise

	def test_01a(self):
		db = DBProxy(self.root_path)
		version = db.get_tables_items(DbVersion)
		self.assertEqual(1, len(version))
		self.assertEqual("2.0.0", version[0].version)

	def test_02a(self):
		db = DBProxy(self.root_path)
		self.assertTrue(db.contains(DbVersion, version="2.0.0"))
		self.assertFalse(db.contains(DbVersion, version="polop"))

class MovieDBInserterTestCase(unittest.TestCase):
	def setUp(self):
		self.root_path = tempfile.mkdtemp()

	def tearDown(self):
		try:
			shutil.rmtree(self.root_path)  # delete directory
		except OSError as exc:
			if exc.errno != 2:  # code 2 - no such file or directory
				raise

	def insertshows(self, db, number):
		for rank in range(number):
			MovieDBInserter(db, MediaFile("pilip/polop%d.avi" % rank))

	def test_01a(self):
		path = "pilip/polop.avi"
		media_file = MediaFile(path)
		db = DBProxy(self.root_path)
		inserter1 = MovieDBInserter(db, media_file)
		self.assertTrue(db.contains(Videos, path=path))
		inserter2 = MovieDBInserter(db, media_file)
		self.assertEqual(inserter1.video_id, inserter2.video_id)
		self.assertEqual(1, len(db.get_tables_items(Videos)))

	def test_02a(self):
		db = DBProxy(self.root_path)
		self.insertshows(db, 20)
		result = db.get_tables_items(Videos, order_by="PATH", limit=10)
		self.assertEqual(10, len(result))

	def test_03a(self):
		db = DBProxy(self.root_path)
		self.insertshows(db, 20)
		result = db.get_tables_items(Videos, order_by="PATH", limit=10, where="ID > 10")
		self.assertEqual(10, len(result))

if __name__ == "__main__":
	import logging
	logging.basicConfig(level=logging.DEBUG)
	unittest.main()

