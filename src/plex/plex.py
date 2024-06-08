import json, os
import requests
from pathlib import Path
from plexapi.server import PlexServer
import urllib.parse as qt
from time import sleep
from tqdm import tqdm
from dotenv import load_dotenv
load_dotenv()

class PlexMAN():
    
	def __init__(self, settings, logger):
		self.settings = settings
		self.logger = logger
		BASE_URL = os.getenv('PLEX')
		PLEX_TOKEN = os.getenv('PLEX_TOKEN')
		self.baseurl = BASE_URL
		self.token = PLEX_TOKEN
		self.api = PlexServer(self.baseurl, self.token)
		self.users = self.getServerUsers()

	def uploadPlaylists(self, m3uPath:Path, libraryName, api=None):
		if api is None: # incase you want to upload to a different user than default:admin
			api = self.api
		section = api.library.section(libraryName)
		if section is None: return
		if m3uPath.is_dir(): # if folder of playlists
			for fl in m3uPath.rglob('*.m3u'):
				if fl.stat().st_size < 30: # make sure the playlist is not an empty file
					continue
				plf = fl.read_text(encoding='utf-8').split('\n')[1].replace('#PLAYLIST: ','')
				try:
					p = section.createPlaylist(title=plf,m3ufilepath=fl.absolute().as_posix())
					print(f"Successfully uploaded: {fl}",end='\r')
				except:
					print(f"Error uploading: {fl}")
		elif m3uPath.is_file(): # if single playlist
			if m3uPath.stat().st_size < 30: # make sure the playlist is not an empty file
				return
			plf = m3uPath.read_text(encoding='utf-8').split('\n')[1].replace('#PLAYLIST: ','')
			try:
				p = section.createPlaylist(title=plf,m3ufilepath=m3uPath.absolute().as_posix())
				print(f"Successfully uploaded: {m3uPath}",end='\r')
			except:
				print(f"Error uploading: {m3uPath}")

	def deletePlaylists(self, userids=[], typeofPL=[]):
		if typeofPL == ['']:
			typeofPL = [
				'show',
				'artist',
				'photo',
				'movie'
			]
		if userids == []:
			userids = self.users
		elif userids == 'me':
			for section in self.api.library.sections():
				if section.type in typeofPL:
					for playlist in section.playlists():
						print(f"DELETING: {playlist.title} from ME",end='\r')
						playlist.delete()
			return

		for user, name in userids.items():
			try:
				plx = self.switchUser(user)
				if plx == None:
					continue
			except:
				continue
			for section in plx.library.sections():
				if section.type in typeofPL:
					for playlist in section.playlists():
						print(f"DELETING: {playlist.title} from {name}",end='\r')
						playlist.delete()

	# typeofPL must be "show" "artist" "photo" "movie"
	# toids must be key:value pairs of userid:username
	def copyPlaylistToUsers(self, typeofPL=None, fromid=None, toids=None):
		try:
			if fromid == None:
				fromid = self.api.myPlexAccount().id
				plx = self.api
			if fromid != self.api.myPlexAccount().id:
				acc = self.api.systemAccount(fromid)
				if acc == None:
					return
				else:
					plx = self.switchUser(str(fromid))
					if plx == None:
						return
			if toids is None:
				toids = self.users
			if typeofPL is None:
				typeofPL = ["show","artist","photo","movie"]
		except:
			return
		for d, name in toids.items():
			print(f"{d} \\ {name}")
			for section in plx.library.sections():
				if section.type in typeofPL:
					for playlist in section.playlists():
						try:
							playlist.copyToUser(name)
						except:
							print("ERR Copying")
							sleep(1)
						print(f"COPYING {playlist.title} from {self.api.myPlexUsername} to {name}".ljust(100, ' '), end='\r')

	def getServerUsers(self):
		users = {}
		for user in self.api.systemAccounts():
			if user.id != 0 and user.id != 1:
				try:
					self.api.myPlexAccount().user(user.name)
					users[str(user.id)] = user.name
				except:
					continue
		return users


	def joinDups(self):
		tmp = ''
		lst = []
		er = open("artistdup.txt", 'w', encoding='utf-8')
		dct = {}
		for section in self.api.library.sections():
			if section.type == "artist":
				tmp = section
				print(section, "yy", tmp.type)
				lst = tmp.all()
		for i in lst:
			if i.title not in dct:
				dct[i.title] = [i.ratingKey]
			else:
				dct[i.title].append(i.ratingKey)
		for i, k in dct.items():
			k = sorted(k)
			if len(k) > 1:
				print(i, k)
				for x in lst:
					if x.ratingKey == k[0]:
						k.pop(0)
						x.merge(k)
						break
				er.write(f"{i},{k}\n")

	def getDuos(self):
		tmp = ''
		lst = []
		dct = {}
		for section in self.api.library.sections():
			if section.type == "artist":
				tmp = section
				print(section, "yy", tmp.type)
				lst = tmp.all()
				break
		for i in tqdm(lst,ncols=100):
			if i.title not in dct:
				if any(x in i.title for x in ['\\', '/', ':', ';', '&', '+']):
					# print(i.title,i.fields)
					trks = i.tracks()
					tkl = []
					for t in trks:
						# print(t.title,t.fields)
						tkl += t.locations
					dct[i.title] = {
						"artist": i.locations,
						"tracks": tkl
					}
					# i.refresh()

		er = open("artister.m3u", 'w', encoding='utf-8')
		er.write(f"#EXTM3U\n")
		for i, k in dct.items():
			# print(i)
			er.write(f'#EXTINF:,{i}\n')
			tp = "\n".join(k["tracks"])
			er.write(f'{tp}\n')
		return dct

	def updateBlankObj(self):
		op = []
		libs = ['artist']
		for section in self.api.library.sections():
			if section.type in libs:
				# print(section)
				for artist in section.all():
					print(f"working on artist {artist.title}")
					for song in artist.tracks():
						if song.title == "":
							print(f"{song.title}{song.parentTitle}")
							op.append(song.title)
							song.refresh()
							song.analyze()
		op = sorted(op)
		writelist(op, 'names.json')

def writelist(var, filename='playlists.json'):
	with open(filename, 'w', encoding="utf-8") as pl:
		json.dump(var, pl)

if __name__ == "__main__":
	plex = PlexMAN()
