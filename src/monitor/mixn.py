import re, json, os
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
from threading import Thread
from send2trash import send2trash
from src.monitor.methods import MonitorDatabase
from itertools import chain
from collections import defaultdict
try:
    from src.monitor.dmx import DLR
except ImportError:
    DLR = None

class MonitorMixn():

	def __init__(self,db):
		super().__init__(db)
		print('created Monitor',end='\r')
		self.settings |= {  # default settings
			'playlistFolder': 'output/playlists',
			'missingSongsFile': 'output/missingSongs.m3u',
			'failedDLsFile':'output/failedDL.txt',
			'downloadedSongsFile':'output/Downloaded.txt'
		}
		self.settings |= {
			'monitoredFile':'input/Monitor.txt',
			'arlListFile':'input/arl.txt',
			'workingARLsFile':'input/ARLworking.txt'
		}
		self.dbmn = MonitorDatabase(db)
		if DLR:
			self.dmx = DLR(arl=os.getenv('DEEZERARLDL'),failedFile=self.settings.failedDLsFile,successFile=self.settings.downloadedSongsFile,workingarls=self.settings.workingARLsFile)
   
	def urlToCollection(self, url):
		info = {}
		spotifyuri = re.fullmatch(
			r'([A-Za-z\d]*);spotify:(playlist|artist|user):([A-Za-z\d]*)', url)
		spotifylink = re.fullmatch(
			r'([A-Za-z\d]*);https?:\/\/(?:open)?\.spotify\.com\/(playlist|artist|user)\/([A-Za-z\d]*)\??.*', url)
		deezerlink = re.fullmatch(
			r'([A-Za-z\d]*);https?:\/\/(?:www\.)?deezer\.com\/(?:[a-z]{2,2}\/)?(playlist|artist)\/(\d*)\??.*', url)
		if spotifyuri is not None:
			info['quality'] = spotifyuri.group(1).lower()
			info['spotifyuri'] = url
			info['monitor_type'] = spotifyuri.group(2).lower()
			info['spotifyid'] = spotifyuri.group(3)
		elif spotifylink:
			info['quality'] = spotifylink.group(1).lower()
			info['spotifyuri'] = f'spotify:{spotifylink.group(2).lower()}:{spotifylink.group(3)}'
			info['monitor_type'] = spotifylink.group(2).lower()
			info['spotifyid'] = spotifylink.group(3)
		elif deezerlink:
			info['quality'] = deezerlink.group(1).lower()
			info['monitor_type'] = deezerlink.group(2).lower()
			info['deezerid'] = int(deezerlink.group(3))
		return info

	def findSpotifyArtistInDeezer(self, name):
		dzid, th = 0, None
		dzinfo = self.dz.api.search_artists(name)[0]
		if dzinfo and dzinfo.name.lower() == name.lower():
			dzid = dzinfo.id
			th = Thread(target=self.getDeezerDiscography, args=(dzinfo.id,))
		return th, dzid

	def findDeezerArtistInSpotify(self, name):
		info, th = {}, None
		spinfo = self.sp.findArtistByName(name)
		if spinfo and spinfo.get('name').lower() == name.lower():
			info['spotifyid'] = spinfo.get('id')
			info['spotifyuri'] = spinfo.get('uri')
			th = Thread(target=self.getSpotifyDiscography,
						args=(spinfo.get('id'),))
		return th, info

	def addCollection(self, url=None, info: dict = None):
		threads = []
		info = {}
		if url is not None:
			info = self.urlToCollection(url.strip())
		filter = {'spotifyid':info['spotifyid']} if 'spotifyid' in info else {'deezerid':info['deezerid']}
		if self.dbmn.get_Monitor(filter):
			return
		match info:
			case {'spotifyid': spotifyid, 'monitor_type': tp} if tp == 'artist':
				information = self.sp.getArtist(spotifyid)
				if information:
					info['name'] = information.get('name')
					tqdm.write(f'Getting {information.get("name")} Songs')
					threads.append(
						Thread(target=self.getSpotifyDiscography, args=(spotifyid,)))
					th, dzid = self.findSpotifyArtistInDeezer(
						information.get('name'))
					if th:
						threads.append(th)
						info['deezerid'] = dzid
			case {'spotifyid': spotifyid, 'monitor_type': tp} if tp == 'user':
				info['type'] = 'playlist'
				info['spotifyuri'] = info['spotifyuri'].replace(
					':user:', ':playlist:')
				info['name'] = f"{info['spotifyid']} Likes"

			case {'spotifyid': spotifyid, 'monitor_type': tp} if tp == 'playlist':
				information = self.sp.getPlaylist(spotifyid)
				if information:
					info['name'] = information.get('name')
					tqdm.write(f'Getting {information.get("name")} Songs')
					threads.append(
						Thread(target=self.getSpotifyPlaylist, args=(spotifyid,)))
			case {'deezerid': deezerid, 'monitor_type': tp} if tp == 'artist':
				information = self.dz.api.get_artist(deezerid)
				if information:
					info['name'] = information.name
					tqdm.write(f'Getting {information.name} Songs')
					threads.append(
						Thread(target=self.getDeezerDiscography, args=(deezerid,)))
					th, spinfo = self.findDeezerArtistInSpotify(
						information.name)
					if th:
						threads.append(th)
						info.update(spinfo)
			case {'deezerid': deezerid, 'monitor_type': tp} if tp == 'playlist':
				information = self.dz.api.get_playlist(deezerid)
				if information:
					info['name'] = information.title
					tqdm.write(f'Getting {information.title} Songs')
					threads.append(
						Thread(target=self.getDeezerPlaylist, args=(deezerid,)))
		for t in threads:
			t.start()
		for t in threads:
			t.join()
		info['last_checked'] = datetime.utcnow()
		if info.get('name'):
			self.dbmn.add_Monitor(info)
		pass

	def refreshCollect(self, force=False, spotify=True, deezer=True):

		if force:
			collections = list(self.dbmn.get_Monitors({}))
		else:
			collections = list(self.dbmn.get_Monitors({'next_check':{'$lt':datetime.utcnow()}}))
		for coll in tqdm(collections, desc='Collection',**self.logger.tqdm):
			coll = self.dbmn.validate_Monitor(coll)
			threads = []
			tqdm.write(f'Getting {coll.name} Songs')
			if coll.monitor_type == 'artist':
				if coll.deezerid and deezer:
					threads.append(
						Thread(target=self.getDeezerDiscography, args=(coll.deezerid,)))
				if coll.spotifyid and spotify:
					threads.append(
						Thread(target=self.getSpotifyDiscography, args=(coll.spotifyid,)))
			elif coll.monitor_type == 'playlist':
				if coll.deezerid and deezer:
					threads.append(
						Thread(target=self.getDeezerPlaylist, args=(coll.deezerid,)))
				if coll.spotifyid and spotify:
					threads.append(
						Thread(target=self.getSpotifyPlaylist, args=(coll.spotifyid,)))
			for t in threads:
				t.start()
			for t in threads:  # commented out because running two threads can lead to database being locked by one and not allowing the other to continue
				t.join()
			coll.last_checked = datetime.utcnow()
			coll.set_next_check()
			if coll.deezerid and coll.spotifyid:
				self.dbmn.update_Monitor({'deezerid':coll.deezerid,'spotifyid':coll.spotifyid},{'$set':coll.model_dump()})
			elif coll.deezerid:
				self.dbmn.update_Monitor({'deezerid':coll.deezerid},{'$set':coll.model_dump()})
			elif coll.spotifyid:
				self.dbmn.update_Monitor({'spotifyid':coll.spotifyid},{'$set':coll.model_dump()})

# lists the songs from the colections that are missing in a file
	def getCollectionISRCList(self, _ids: list = None):
		filter = {}
		missingbuff = []
		for x in tqdm(self.dbmn.get_Monitors(filter),'Collections',**self.logger.tqdm):
			qualitybit = 315 if x['quality'] == '320' else 321
			songs = []
			if x['deezerid']:
				if x['monitor_type'] == 'artist':
					songs += list(self.dbdz.get_ArtistLocalSongs(x['deezerid'],qualitybit))
				elif x['monitor_type'] == 'playlist':
					songs += list(self.dbdz.get_PlaylistLocalSongs({'id':x['deezerid']},qualitybit))
			if x['spotifyid']:
				if x['monitor_type'] == 'artist':
					songs += list(self.dbsp.get_ArtistLocalSongs(x['spotifyid'],qualitybit))
				elif x['monitor_type'] == 'playlist':
					songs += list(self.dbsp.get_PlaylistLocalSongs({'uri':x['spotifyuri']},qualitybit))

			missing = [f'# {x["name"]}']
			for song in tqdm(songs,**self.logger.tqdm):
				st = f'\t{song["isrc"]} - {x["quality"]} - {song["title"]}'
				if len(song['local']) == 0 and st not in missing:
					missing.append(st)

			if len(missing) > 1:
				missingbuff += missing
    
		if len(missingbuff):
			self.settings.missingSongsFile.write_text(
				'\n'.join(missingbuff), encoding='utf-8')
				
		pass

	def readCollectionTxt(self):
		for x in tqdm(self.settings.monitoredFile.open('r').readlines(), desc='Monitor.txt',**self.logger.tqdm):
			if x[0] == '#':
				continue
			self.addCollection(x)

	def dl_missing_tracks(self, gets=True, delfile=False):
		missinglist = self.settings.missingSongsFile.read_text('utf-8').splitlines()
		missing = {}
		for x in missinglist:
			if x[0] == '#':
				continue
			isrc, quality, name = x.strip().split(' - ')[:3]
			if isrc not in missing:
				missing[isrc] = self.getQuality(quality)
			elif missing[isrc] < self.getQuality(quality):
				missing[isrc] = self.getQuality(quality)

		reversed_dict = defaultdict(list)
		for key, value in missing.items():
			reversed_dict[value].append(key)

		for quality,isrcs in tqdm(reversed_dict.items(), 'Loading Songs',**self.logger.tqdm):
			self.dmx.loadLinks(
				[f'deezer.com/track/isrc:{isrc}' for isrc in isrcs], bitrate=quality)
		if gets:
			self.dmx.getsongs()

	@staticmethod
	def getQuality(txt):
		txt = str(txt).lower()
		if txt in ['flac', 'lossless', '9']:
			return 9
		if txt in ['mp3', '320', '3']:
			return 3
		if txt in ['128', '1']:
			return 1
		if txt in ['360', '360_hq', '15']:
			return 15
		if txt in ['360_mq', '14']:
			return 14
		if txt in ['360_lq', '13']:
			return 13
		return 0
