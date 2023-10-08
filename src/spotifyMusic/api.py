import spotipy
import os
import json
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import time
import requests
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()



# attempt to fix call hangging on 429 request with high retry-after Value
class Spot(spotipy.Spotify):
	def _build_session(self):
		self._session = requests.Session()
		# retry = urllib3.Retry(
		#     total=self.retries,
		#     connect=None,
		#     read=False,
		#     allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE']),
		#     status=self.status_retries,
		#     backoff_factor=self.backoff_factor,
		#     status_forcelist=self.status_forcelist)

		# adapter = requests.adapters.HTTPAdapter(max_retries=retry)
		adapter = requests.adapters.HTTPAdapter()
		self._session.mount('http://', adapter)
		self._session.mount('https://', adapter)


class SpotifyAPI():
	def __init__(self, clientid, secret,
				 scope='user-library-read playlist-read-private playlist-modify-public playlist-modify-private ',reqpsec=5):
		scope = scope
		self.spotify = Spot(auth_manager=SpotifyOAuth(client_id=clientid, client_secret=secret,
							redirect_uri="http://localhost:8942/callback/", scope=scope), status_forcelist=(500, 502, 503, 504))
		self.username = self.spotify.me().get('id')
		self.ratelimit = datetime.datetime.utcnow()  # when can i make my next request // updates after 429 error
		self.lastrequest = time.time()
		self.SPR = 1 / reqpsec
		self.getArtist('4jogXSSvlyMkODGSZ2wc2P') # test if still ratelimited

	# Necessary because of the 404 bug in the spotify API
	def trywTimeout(self, result, func, data: dict, attempt=1, maxattempt=3):
		for x in range(attempt, maxattempt):
			try:
				result.put(func(**data))
			except Exception as e:
				print(f'SPOTIFY-API-ERROR: {e}\nRETRYING {x}/{maxattempt}')
				time.sleep(3)
				continue
			break

	def canIrun(self):
		dif = time.time() - self.lastrequest
		if datetime.datetime.utcnow() > self.ratelimit:
			if  dif < self.SPR and dif >= 0: # limit the amount of requests per second
				time.sleep(self.SPR-dif)
				return True
			else:
				return True
		return False
	
	def retry404(self, func, data: dict):
		if not self.canIrun(): return None
		try:
			self.lastrequest = time.time()
			return func(**data)
		except Exception as e:
			print(f'SPOTIFY-API-ERROR: {e.args}')

			if 429 in e.args and 'retry-after' in e.headers: # handle the 429:too many request error 
				self.ratelimit = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(e.headers['retry-after']))
				Path('spotifyratelimit.txt').open('w').write(self.ratelimit.strftime("%Y-%m-%dT%H:%M:%SZ"))
			time.sleep(3)
			return None
		
	# goes thru all the paginated results
	def getALL(self, data, tlist):
		while data['next']:
			data = self.retry404(self.spotify.next, {'result': data})
			if data == None:
				break
			tlist += data['items']
		return tlist

	def getUserPlaylists(self):
		playlists = self.retry404(self.spotify.current_user_playlists,{'limit':50})
		if playlists == None:
			return None
		tlist = playlists['items']
		if 'next' in playlists:
			tlist = self.getALL(playlists, tlist)
		return tlist

	# returns list of tracks from playlist id pid
	def getPlaylistTracks(self, pid):
		tracks = self.retry404(self.spotify.playlist_tracks, {
							   'playlist_id': pid})
		if tracks == None:
			return None
		tlist = tracks['items']
		if 'next' in tracks:
			tlist = self.getALL(tracks, tlist)
		return tlist

	def getLiked(self):
		tracks = self.retry404(self.spotify.current_user_saved_tracks,{'limit':50})
		if tracks == None:
			return None
		tlist = tracks['items']
		if 'next' in tracks:
			tlist = self.getALL(tracks, tlist)
		return tlist

	def getPlaylist(self, pid):
		return self.retry404(self.spotify.user_playlist, {'user': self.username, 'playlist_id': pid})

	def getTrack(self, tid):
		return self.retry404(self.spotify.track, {'track_id': tid})

	def getTracks(self, tids):
		tracks = {}
		limit = 50
		for x in range(0,len(tids),limit):
			res = self.retry404(self.spotify.tracks, {'tracks': tids[x:x+limit]})
			if res:
				for track in res['tracks']:
					if track and 'id' in track:
						tracks[track['id']] = track
		return tracks

	def getAlbum(self, tid):
		return self.retry404(self.spotify.album, {'album_id': tid})

	def getAlbums(self, tids):
		albums = {}
		res = self.retry404(self.spotify.albums, {'albums': tids})
		if res:
			for album in res['albums']:
				albums[album['id']] = album
		return albums

	def getArtist(self, aid):
		artist = self.retry404(self.spotify.artist,{
							   'artist_id': aid})
		return artist

	def getArtistAlbums(self, aid):
		albums = self.retry404(self.spotify.artist_albums, {
							   'artist_id': aid, 'album_type': 'album,single,appears_on,compilation', 'limit': 50})
		if albums == None:
			return None
		tlist = albums['items']
		if 'next' in albums:
			tlist = self.getALL(albums, tlist)
		return tlist

	def getAlbumTracks(self, aid):
		album = self.retry404(self.spotify.album_tracks, {'album_id': aid})
		if album == None:
			return None
		tlist = album['items']
		if 'next' in album:
			tlist = self.getALL(album, tlist)
		return tlist

	def findArtistByName(self, name):
		data = self.retry404(self.spotify.search,{'q':f'artist:{name}','type':'artist'})
		if data:
			if len(data.get('artists', {}).get('items', [])):
				return data.get('artists').get('items')[0]


def writelist(var, filename='playlists.json'):
	with open(filename, 'w', encoding="utf-8") as pl:
		json.dump(var, pl)


if __name__ == "__main__":
	SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
	SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
	spoty = SpotifyAPI(clientid=SPOTIFY_CLIENT_ID,
					   secret=SPOTIFY_CLIENT_SECRET)

