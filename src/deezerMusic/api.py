import os
from deezer import Client
from deezer.resources import Album
from deezerpy.gw import GW
from deezerpy.utils import map_album, map_artist_album, map_playlist, map_track
import requests
from time import sleep

from dotenv import load_dotenv

load_dotenv()

def retry_404(f):
	def wrapper(*args, **kw):
		self = args[0]
		for x in range(self.maxattempts):
			try:
				res = f(*args, **kw)
			except Exception as e:
				# if e.json_data.get('error',{}).get('code') == 800:
				# 	return None
				continue
			return res
	return wrapper


class DeezerAPI():
	def __init__(self):
		session = requests.Session()
		self.api = Client(app_id=os.getenv('DEEZERAPPID'),app_secret=os.getenv('DEEZERSECRET'),access_token=os.getenv('DEEZERTOKEN'))
		self.me = self.api.get_user(os.getenv('DEEZERUSERID'))
		http_headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/118.0",
			"x-deezer-user":str(self.me.id)

		}
		self.gw = GW(session,http_headers)
		self.gw.api_token = os.getenv('DEEZERTOKEN')
		self.maxattempts = 3

	# Necessary because of the 404 bug in the spotify API
	def retry404(self,func,data={},attempt=1,maxattempt=3):
		res = None
		for x in range(attempt,maxattempt):
			try:
				res = func(**data)
			except Exception as e:
				if e.json_data.get('error',{}).get('code') == 800:
					return res
				print(f'DEEZER-API-ERROR: {e}\nRETRYING {x}/{maxattempt}')
				sleep(3)
				continue
			break
		return res

	@retry_404
	def getUserPlaylists(self):
		return self.me.get_playlists()

	@retry_404
	def getPlaylist(self,playlistid):
		return self.api.get_playlist(playlistid)
		
	@retry_404
	def getTrack(self,trackid):
		return self.api.get_track(trackid)

	@retry_404
	def getArtist(self,artistid):
		return self.api.get_artist(artistid)
	@retry_404
	def getAlbum(self,albumid):
		return self.api.get_album(albumid)

	@retry_404
	def getDiscography(self,artistname):
		discos = {}
		index = 0
		tm = self.api.search_albums(f'artist:"{artistname}"')
		srt = {x.id:x for x in tm}
		# while True:
		# 	tmp = self.gw.get_artist_discography(artistid,index,limit=100)
		# 	for x in tmp['data']:
		# 		x = map_album(x)
		# 		x['id'] = int(x['id'])
		# 		x['nb_tracks'] = int(x['nb_tracks'])
		# 		if x['id'] not in discos:
		# 			discos[x['id']] = x
		# 	index += tmp['count']
		# 	if tmp['start']+tmp['count'] >= tmp['total']:
		# 		diff = {x:y for x,y in srt.items() if x not in discos}
				# return discos
		return srt
	@retry_404
	def getAlbumTracks(self,albumid):
		if not isinstance(albumid,Album):
			albumid = self.api.get_album(albumid)
		return [self.getTrack(x.id) for x in albumid.get_tracks()]

	@retry_404
	def search(self,q):
		res = self.api.search(**q)
		return res
  
	@retry_404
	def getFeat(self,artist_id):
		limit = 50
		index = 0
		releases = []
		while True:
			response = self.gw.api_call('album.getDiscography', {
					'ART_ID': artist_id,
					"discography_mode":"featured",
					'nb': limit,
					'nb_songs': 0,
					'start': index,
					"filter_role_id":[5]
				})
			releases += response['data']
			index += limit
			if index > response['total']:
				break
		return {int(x['ALB_ID']):map_artist_album(x) for x in releases}

	def map_song(self,song):
		mapped = map_track(song)
		mapped['id'] = int(mapped['id'])
		mapped['duration'] = int(mapped['duration'])
		mapped['explicit_lyrics'] = bool(mapped['explicit_lyrics'])
		mapped['disk_number'] = int(mapped['disk_number'])
		mapped['track_position'] = int(mapped['track_position'])
		mapped['album']['id'] = int(mapped['album']['id'])
		mapped['artist']['id'] = int(mapped['artist']['id'])
		for artist in mapped['contributors']:
			artist['id'] = int(artist['id'])
		return mapped
	def getISRC(self,info):
		res = self.getTrack(f'isrc:{info.pop("isrc","")}')

		return res

if __name__ == "__main__":
	ls = DeezerAPI()
