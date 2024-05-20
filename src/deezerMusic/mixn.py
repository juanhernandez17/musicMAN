import os
from deezer import Client
from tqdm import tqdm
from datetime import datetime
from src.deezerMusic.api import DeezerAPI
from src.deezerMusic.methods import DeezerDatabase
from pathlib import Path
from src.config.utils import parse_date
from time import time
class DeezerMixn():
	def __init__(self,db):
		super().__init__(db)
		print('created Deezer',end='\r')
		self.dz = DeezerAPI()
		self.dbdz = DeezerDatabase(db)
  
	def getDeezerPlaylists(self):
		playlists = self.dz.me.get_playlists()
		existing = [x['checksum'] for x in self.dbdz.exists_Playlists([x.checksum for x in playlists],{'checksum':1})]
		missing = [x for x in playlists if x.checksum not in existing]
		for playlist in tqdm(missing,'Deezer Playlists',**self.logger.tqdm):
			self.getDeezerPlaylist(playlist)

	def getDeezerDiscography(self,artist_id):
		artist = self.dz.getArtist(artist_id)
		if artist is None: return None
		albums = self.dz.getDiscography(artist.name) # deezer api only lets us search by artist name not by artist id
		if albums is None: return None
		spotids = [x for x in albums]
		existingalbums = {x['_id']:x for x in self.dbdz.get_Albums(spotids)}
		missing = {}
		for x,y in albums.items():
			if x not in existingalbums or (y.nb_tracks != existingalbums[x]['nb_tracks'] and y.artist.id == artist.id):
				missing[x] = y
		for dzid, album in tqdm(missing.items(), f'Deezer Albums',**self.logger.tqdm):
			tracks = []
			existing = {x['id']:x['_id'] for x in self.dbdz.get_Album(dzid,{'id':1})}
			if album.artist.id == artist.id: # if its an official album
				tracks = [(x).as_dict()['id'] for x in album.get_tracks()]
			else: # if artists is featured or wrong artist[sometimes fakeprofiles are made]
				for track in self.dz.getAlbumTracks(album):
					artists = track.contributors
					if len(artists) > 1:
						for cont in artists:
							if artist.id == cont.id:
								tracks.append(track.as_dict()['id'])
								break
			if len(tracks):
				self.addMissingDeezerSongs(tracks,existing)
				tqdm.write(f'[NEW DEEZER ALBUM] [{album.title}]')

	def getDeezerPlaylist(self,playlist):
		if isinstance(playlist,int):
			playlist = self.dz.getPlaylist(playlist)
			exists = self.dbdz.get_Playlist({'checksum':playlist.checksum},{'id':1})
			if exists is not None:
				return exists
		pl = playlist.as_dict()
		if 'tracks' not in pl or pl['nb_tracks'] != len(pl['tracks']):
			tracks = playlist.get_tracks()
			pl['tracks'] = []
			for track in tracks:
				pl['tracks'].append(track.as_dict())
		tracklist = [x['id'] for x in pl['tracks']]
		self.addMissingDeezerSongs(tracklist)
		pl = self.dbdz.add_Playlist(pl)
		tqdm.write(f'[NEW PLAYLIST] [{playlist.id}:{playlist.title}]')

	def getDeezerLikes(self):
		me = {
			'id': self.dz.me.id,
			'name': self.dz.me.name
		}
		playlist = {
			'id': self.dz.me.id,
			'collaborative': False,
			'description': 'user likes',
			'title': f'Likes: {self.dz.me.id}-{self.dz.me.name}',
			'duration':0,
			'public':False,
			'creator': me,
		}
		tracks = []
		hs = []
		old = parse_date('2000')
		for trk in self.dz.me.get_tracks():
			playlist['duration'] += trk.duration
			newd = datetime.fromtimestamp(trk.time_add)
			if old < newd:
				old = newd
			hs.append(trk.title)
			hs.append(str(trk.time_add))
			tracks.append(trk.as_dict())
			pass
		playlist['creation_date'] = old.strftime("%Y-%m-%d %H:%M:%S")
		playlist['checksum'] = self.md5_string(hs)
		playlist['tracks'] = tracks
		playlist['nb_tracks'] = len(tracks)
		self.addMissingDeezerSongs([x['id'] for x in tracks])
		self.dbdz.add_Playlist(playlist)

	def addMissingDeezerSongs(self,songidlist:list,existing=None):
		if existing is None:
			existing = {x['id']:x['_id'] for x in self.dbdz.exists_Songs(songidlist,{'id':1})}
		missing = [x for x in songidlist if x not in existing]
		creating = []
		for x in tqdm(missing,'Deezer Songs',**self.logger.tqdm):
			song = self.dz.getTrack(x)
			if song:
				creating.append(song.as_dict())
				# res = self.dbdz.add_Song(song.as_dict())
				# if res.inserted_id:
				# 	existing[song.id] = res.inserted_id
		if len(creating):
			self.dbdz.add_Songs(creating)

	def updateDeezerSongs(self):
		allsongs = list(self.dbdz.get_Songs({}))
		for song in tqdm(allsongs,**self.logger.tqdm):
			objid = song['_id']
			track = self.dz.getTrack(song['id'])
			if track:
				song = self.dbdz.validate_Song(track.as_dict())
				if song:
					self.dbdz.update_Song(song['id'],{'$set':song})
			pass
		pass

	def updateDeezerPlaylists(self):
		allplaylist = list(self.dbdz.get_Playlists({}))
		for playlist in tqdm(allplaylist,**self.logger.tqdm):
			checksum = playlist.pop('checksum')
			_id = playlist.pop('_id')
			for song in playlist['tracks']:
				sg = self.dbdz.get_Song({'id':song['id']})
				song['isrc'] = sg['isrc']
				pass
			pass
			self.dbdz.update_Playlist(checksum,{'$set':playlist})
   
	def getMissingDeezerSongs(self):
		songids = []
		artistids = []
		for x in tqdm(self.dbmn.get_Monitors(),'Collections',**self.logger.tqdm):
			if x['monitor_type'] == 'artist':
				artistids.append(x['deezerid'])
			elif x['monitor_type'] == 'playlist':
				songids += [y['id'] for y in x['tracks']]
		
		return

	def updateDeezerSongsisrc(self):
		for track in tqdm(self.dbdz.get_Songs({'isrc':{'$regex':'[a-z\-]'}}), desc='Songs',**self.logger.tqdm):
			if track['isrc']:
				track['isrc'] = track['isrc'].upper().replace('-','').replace('_','')
			self.dbdz.update_Song({'id':track['id']},{'$set':track})