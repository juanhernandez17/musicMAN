import os
from tqdm import tqdm
from src.spotifyMusic.api import SpotifyAPI
from dotenv import load_dotenv
from pathlib import Path
from time import time
from datetime import datetime
import json
from itertools import chain
from src.spotifyMusic.methods import SpotifyDatabase, Song
from src.config.utils import parse_date, md5_string
load_dotenv()


class SpotifyMAN():
    
	def __init__(self,db, settings, logger):
		self.settings = settings
		self.logger = logger
		SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
		SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
		self.sp = SpotifyAPI(clientid=SPOTIFY_CLIENT_ID, secret=SPOTIFY_CLIENT_SECRET,ratelimit=self.settings.spotifyratelimitDate)
		self.db = SpotifyDatabase(db)
		print('created Spotify',end='\r')

	def getPlaylists(self, plids: list = None, likes: bool = True, usercreated=False):
		me = self.sp.spotify.me()
		if plids:
			playlists = [x for x in [self.sp.getPlaylist(x) for x in plids] if x]
		else:
			playlists = self.sp.getUserPlaylists()
		existinpl = [x['snapshot_id'] for x in self.db.exists_Playlists([x['snapshot_id'] for x in playlists],{'snapshot_id':1})]
		missing = [x for x in playlists if x['snapshot_id'] not in existinpl]
		for x in tqdm(missing, 'Spotify Playlists',**self.logger.tqdm):
			if usercreated and x['owner']['id'] != me.get('id'):
				continue
			self.getPlaylist(x)
 
		if likes:
			self.getLiked()

	def getLiked(self):

		me = self.sp.spotify.me()
		playlist = {
			'id': me.get('id'),
			'uri': me.get('uri').replace(':user:', ':playlist:'),
			'collaborative': False,
			'description': 'user likes',
			'name': f'{me.get("display_name")} Likes',
			'public':False,
			'owner':me
		}
		tracks = self.sp.getLiked()
		hs = []
		old = parse_date('2000')
		for tr in tracks:
			hs.append(tr['added_at'])
			hs.append(tr['track']['name'])
			tr['added_by'] = me
			newd = parse_date(tr['added_at'])
			if old < newd:
				old = newd
		playlist['tracks'] = {'items': tracks}
		playlist['snapshot_id'] = md5_string(hs)
		playlist['tracks']['total'] = len(tracks)
		exist = self.db.get_Playlist({'snapshot_id':playlist['snapshot_id']},{'id':1})
		if exist is None:
			self.getPlaylist(playlist)

	def getPlaylist(self, playlist):
		if not isinstance(playlist,dict):
			playlist = self.sp.getPlaylist(playlist)
			if playlist and self.db.get_Playlist({'snapshot_id':playlist['snapshot_id']}) is not None:
				return
		today = datetime.utcnow().date()
		if playlist:
			# get Daddy
			daddy = self.db.get_Playlist({'id':playlist['id'],'child':None},{'id':1,'snapshot_id':1,'last_update':1})
			# some playlists are generated every time they are called, this prevents the database from being flooded with them
			if daddy and daddy['last_update'].date() == today:
				return
			if 'items' not in playlist['tracks'] or len(playlist['tracks']['items']) != playlist['tracks']['total']:
				tracks = self.sp.getPlaylistTracks(playlist['id'])
				playlist['tracks']['items'] = tracks
			if playlist['tracks']['items']:
				self.addMissingSongs([x['track'] for x in playlist['tracks']['items'] if x['track']])
			res = self.db.add_Playlist(playlist)
			if daddy and res is not None:
				self.db.update_Playlist({'snapshot_id':daddy['snapshot_id']},{'$set':{'child':playlist['snapshot_id']}})
				self.db.update_Playlist({'snapshot_id':playlist['snapshot_id']},{'$set':{'daddy':daddy['snapshot_id']}})
			tqdm.write(f'[NEW VERSION] [{playlist["id"]}] {playlist["name"]}')
		pass

	def getDiscography(self, artistid):
		spotalbums = self.sp.getArtistAlbums(artistid)
		if spotalbums is None:
			return None
		spotids = [x['id'] for x in spotalbums]
		existingalbums = {x['_id']:x for x in self.db.get_Albums(spotids)}
		missing = []
		for x in spotalbums:
			if x['id'] not in existingalbums or x['total_tracks'] != existingalbums[x['id']]['total_tracks']:
				missing.append(x)
		# missing = [x for x in spotalbums if x['id'] not in existingalbums or x['total_tracks'] != ]
		for alb in tqdm(missing, desc=f'Spotify Albums',**self.logger.tqdm):
			dbalbum = {x['id']:x['_id'] for x in self.db.get_Album(alb['id'],{'id':1})}
			if len(dbalbum) != alb['total_tracks']:
				tracks = self.sp.getAlbumTracks(alb['id'])
				self.addMissingSongs(tracks,dbalbum)
				tqdm.write(f'[NEW SPOTIFY ALBUM] [{alb["id"]}] {alb["name"]}')
		pass

	def addMissingSongs(self,songidlist:list,existing=None):
		if existing is None:
			existing = {x['id']:x['_id'] for x in self.db.exists_Songs([x['id'] for x in songidlist],{'id':1})}
		missing = [x['id'] for x in songidlist if x['id'] not in existing]
		if len(missing):
			songs = self.sp.getTracks(missing)
			self.db.add_Songs(songs.values())
   
   
	def getMissingSongs(self):
		songids = []
		artistids = []
		for x in tqdm(self.dbmn.get_Monitors(),'Collections',**self.logger.tqdm):
			if x['monitor_type'] == 'artist':
				artistids.append(x['deezerid'])
			elif x['monitor_type'] == 'playlist':
				songids += [y['id'] for y in x['tracks']]

	def playlistToM3U(self,recent=False, archive=False):
		if recent:
			filter = {'child':None}
		else:
			filter = {'daddy':None}

		for playlist in tqdm(self.db.get_Playlists(filter), desc='Playlists',**self.logger.tqdm):
			songs = []
			if archive:
				while True:
					songs.append(self.db.get_PlaylistLocalSongs({'snapshot_id':playlist["snapshot_id"]}))
					if playlist['child'] is None:
						break
					playlist = self.db.get_Playlist({'snapshot_id':playlist['child']})
			else:
				songs.append(self.db.get_PlaylistLocalSongs({'snapshot_id':playlist["snapshot_id"]}))
			buff = [f"#EXTM3U \n#PLAYLIST: {playlist['title']}"]
			self.settings.spotifyplaylistFolder
			# newlist = sorted(chain(*songs), key=lambda d: d['added_at'])
			for song in chain(*songs):
				if song['isrc'] is None: continue
				buff.append(f'#EXTINF:{song["id"]},isrc="{song["isrc"]}" added="{song["added_at"]}",{song["title"]}')
				buff.append('\n'.join([x['path'] for x in song["local"]]))
				pass
			(self.settings.spotifyplaylistFolder / f"{playlist['id']}.m3u").write_text('\n'.join(buff),encoding='utf-8')
			pass

	def updatePlaylists(self):
		for playlist in tqdm(self.db.get_Playlists({"tracks.isrc":{'$regex':'[a-z\-]'}}), desc='Playlists',**self.logger.tqdm):
			for track in playlist['tracks']:
				if track['isrc']:
					track['isrc'] = track['isrc'].upper().replace('-','').replace('_','')
			self.db.update_Playlist({'snapshot_id':playlist['snapshot_id']},{'$set':playlist})
   
	def updateSongs(self):
		for track in tqdm(self.db.get_Songs({'isrc':{'$regex':'[a-z\-]'}}), desc='Songs',**self.logger.tqdm):
			if track['isrc']:
				track['isrc'] = track['isrc'].upper().replace('-','').replace('_','')
			self.db.update_Song({'id':track['id']},{'$set':track})
   
   
	def update(self):
		tracks = [x['id'] for x in self.db.get_Songs({'title':None})]
		tracks = self.sp.getTracks(tracks)
		for track in tqdm(self.db.get_Songs({'title':None}), desc='Songs',**self.logger.tqdm):
			song = tracks[track['id']]
			valid = Song(**song).model_dump()
			self.db.update_Song({'id':track['id']},{'$set':valid})