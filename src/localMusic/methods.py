from src.config.utils import handle_exceptions
from src.localMusic.models import Song
import pymongo

class LocalDatabase():
	def __init__(self,db):
		self.songs = db['local_songs']
		self.songs.create_index([("path", pymongo.ASCENDING)], unique=True)
		self.songs.create_index([("isrc", pymongo.ASCENDING)])
  
  
# Validate Models
	@handle_exceptions
	def validate_Song(self,data):
		return Song(**data).model_dump()

	# TODO create Update schemas/models
	@handle_exceptions
	def validate_SongUpdate(self,data):
		return data

	@handle_exceptions
	def update_Song(self,songpath,data):
		data = self.validate_SongUpdate(data)
		if data:
			self.songs.update_one({'path':songpath},{'$set':data})
   
	def update_Songs(self,filter,data):
		data = self.validate_SongUpdate(data)
		self.songs.update_many(filter,data)
  
# Create Document
	@handle_exceptions
	def add_Song(self,data):
		valid = self.validate_Song(data)
		if valid:
			return self.songs.insert_one(valid)

	@handle_exceptions
	def add_Songs(self,songls:list):
		sl = []
		for song in songls:
			valid = self.validate_Song(song)
			if valid:
				sl.append(valid)
		self.songs.insert_many(sl,ordered=False)
# Get
	def get_Song(self,q,params=None):
		if params is None: params = {}
		return self.songs.find_one(q,params)

	def get_Songs(self,q,params=None):
		if params is None: params = {}
		return self.songs.find(q,params,no_cursor_timeout=True)

# Exists
	def exists_Songs(self,songl:list,params:dict):
		if params is None: params = {}
		return self.songs.find({ 'path': { '$in': songl } },params)


	def delete_Song(self,q,params=None):
		if params is None: params = {}
		return self.songs.find_one(q,params)