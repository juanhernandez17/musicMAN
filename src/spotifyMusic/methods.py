from src.spotifyMusic.models import Song, Playlist
from src.config.utils import handle_exceptions
import pymongo


class SpotifyDatabase():
	def __init__(self, db):
		self.songs = db['spotify_songs']
		self.songs.create_index([("uri", pymongo.ASCENDING)], unique=True)
		self.songs.create_index([("isrc", pymongo.ASCENDING)])
		self.songs.create_index([("album.id", pymongo.ASCENDING)])
		self.songs.create_index([("artists.id", pymongo.ASCENDING)])
		self.playlists = db['spotify_playlists']
		self.playlists.create_index(
			[("snapshot_id", pymongo.ASCENDING)], unique=True)
		self.playlists.create_index([("uri", pymongo.ASCENDING)])

# Validate Models
	@handle_exceptions
	def validate_Song(self, data):
		return Song(**data).model_dump()

	@handle_exceptions
	def validate_Playlist(self, data):
		return Playlist(**data).model_dump()
	# TODO create Update schemas/models

	@handle_exceptions
	def validate_SongUpdate(self, data):
		return data

	@handle_exceptions
	def validate_PlaylistUpdate(self, data):
		return data
# Get Or Create Documents

	def getOrCreate_Songs(self, data):
		instance = self.get_Song({'id': data['id']})
		if instance is None:
			instance = self.add_Song(data)
		return instance

	def getOrCreate_Playlist(self, data):
		instance = self.get_playlist({'snapshot_id': data['snapshot_id']})
		if instance is None:
			instance = self.add_Playlist(data)
		return instance

	@handle_exceptions
	def update_Song(self, filter, data):
		data = self.validate_SongUpdate(data)
		if data:
			return self.songs.update_one(filter, data)
		return None

	@handle_exceptions
	def update_Playlist(self, filter, data):
		data = self.validate_PlaylistUpdate(data)
		if data:
			return self.playlists.update_one(filter, data)
		return None

	def update_Songs(self, filter, data):
		data = self.validate_SongUpdate(data)
		self.songs.update_many(filter, data)

	def update_Playlists(self, filter, data):
		data = self.validate_PlaylistUpdate(data)
		self.playlists.update_many(filter, data)

# Create Document
	@handle_exceptions
	def add_Song(self, data):
		valid = self.validate_Song(data)
		if valid:
			return self.songs.insert_one(valid)
		return None

	@handle_exceptions
	def add_Playlist(self, data):
		valid = self.validate_Playlist(data)
		if valid:
			return self.playlists.insert_one(valid)
		return None

	@handle_exceptions
	def add_Songs(self, songls: list):
		sl = []
		for song in songls:
			valid = self.validate_Song(song)
			if valid:
				sl.append(valid)
		return self.songs.insert_many(sl, ordered=False)

	@handle_exceptions
	def add_Playlists(self, playl: list):
		sl = []
		for playlist in playl:
			valid = self.validate_Playlist(playlist)
			if valid:
				sl.append(valid)
		self.playlists.insert_many(sl, ordered=False)
# Get

	def get_Song(self, q, params=None):
		if params is None:
			params = {}
		return self.songs.find_one(q, params)

	def get_Songs(self, q, params=None):
		if params is None:
			params = {}
		return self.songs.find(q, params)

	def get_Album(self, albumid, params=None):
		if params is None:
			params = {}
		return self.songs.find({'album.id': albumid}, params)

	def get_Albums(self, albumid, params=None):
		if params is None:
			params = {}
		return self.songs.aggregate([
			{
				"$match": {
					"album.id":
					{
						'$in': albumid
					}
				}
			},
			{
				"$group": {
					"_id": {
						"id": "$album.id",
						"name": "$album.name",
					},
					"count": {"$count": {}}
				}}, {
				"$project": {
					"_id": "$_id.id",
					"name": "$_id.name",
					"total_tracks": "$count"
				}
			}
		])

	def get_Playlist(self, q, params=None):
		if params is None:
			params = {}
		return self.playlists.find_one(q, params)

	def get_Playlists(self, q, params=None):
		if params is None:
			params = {}
		return self.playlists.find(q, params)
# Exists

	def exists_Songs(self, songl: list, params=None):
		if params is None:
			params = {}
		return self.songs.find({'id': {'$in': songl}}, params)

	def exists_Playlists(self, playl: list, params=None):
		if params is None:
			params = {}
		return self.playlists.find({'snapshot_id': {'$in': playl}}, params)

	def get_LocalSongs(self,ids):
		return self.songs.aggregate([
			{
				"$match": {
					"id":
					{
						'$in': ids
					}
				}
			},
			{
				'$lookup': {
					'from':'local_songs',
					'localField':'isrc',
					'foreignField':'isrc',
					"as":'local'
				}
			},
       ])
  
	def get_PlaylistLocalSongs(self,filter,minbitrate:int=0):
		return self.playlists.aggregate(
			[
				{
					"$match":filter,
				},
				{
					"$unwind":
					{
						"path": "$tracks",
						"includeArrayIndex": "index",
					},
				},
				{
					"$project":
					{
						"id": "$tracks.id",
						"isrc": "$tracks.isrc",
						"title": "$tracks.name",
						"added_at":"$tracks.added_at"
					},
				},
				{
					"$sort":{"added_at":1}
				},
				{
					"$lookup":
					{
						"from": "local_songs",
						"localField": "isrc",
						"foreignField": "isrc",
						"pipeline": [
						{
							"$match": {
							"bitrate": {
								"$gte": minbitrate,
							},
							},
						},
						],
						"as": "local",
					},
				}
			]
		)

	def get_ArtistLocalSongs(self,artistsid,minbitrate:int):
		return self.songs.aggregate(
			[
				{
					"$match":
					{
						"artists.id": artistsid,
					},
				},
				{
					"$lookup":
					{
						"from": "local_songs",
						"localField": "isrc",
						"foreignField": "isrc",
						"pipeline": [
							{
								"$match": {
									"bitrate": {
										"$gte": minbitrate,
									},
								},
							},
						],
						"as": "local",
					},
				},
			]
		)