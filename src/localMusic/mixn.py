from tqdm import tqdm
from pathlib import Path
from itertools import chain
from send2trash import send2trash
from src.localMusic.api import LocalFile
from src.localMusic.methods import LocalDatabase
import shutil
import os, re

class LocalMAN():
	def __init__(self,db, settings, logger):
		self.settings = settings
		self.logger = logger
		self.db = LocalDatabase(db)
		print('created Local',end='\r')

	def getfiles(self, folders:list):

		generators = []
		ends = (".mp3", '.flac', '.m4a', '.wav')
		generators = [os.walk(folder) for folder in folders]
		songs = []
		exists = [x['path'] for x in self.db.get_Songs({},{'path':1})]
		for cwd, folders, files in tqdm(chain(*generators),desc='Scanning',**self.logger.tqdm):
			for p in files:
				if p.endswith(ends):
					fullpath = cwd.replace('\\','/') + '/' + p
					if fullpath in exists: continue
					lp = LocalFile(fullpath)
					formatedfileinfo = lp.formatfileinfo()
					if formatedfileinfo is not None:
						songs.append(formatedfileinfo)
						tqdm.write(f'QUEUED: {formatedfileinfo["title"]} - {fullpath}')
					if len(songs) == 1000:
						self.db.add_Songs(songs)	
						songs = []

		if len(songs):
			self.db.add_Songs(songs)
			songs = []

	def updatefiles(self,folders:list):
		songs = [self.db.get_Songs({'path':{'$regex':folder}}) for folder in folders]
		for s in tqdm(chain(*songs),'Updating Local Songs',**self.logger.tqdm):
			if not Path(s['path']).exists():
				self.db.delete_Song({'path':s['path']})
				continue
			if 'update_time' not in s or Path(s['path']).stat().st_mtime != s['update_time']:
				formatedinfo = LocalFile(s['path']).formatfileinfo()
				if formatedinfo and formatedinfo['md5'].upper() != s['md5'].upper():	
					self.db.update_Song(formatedinfo['path'],formatedinfo)

	def assignPathToArtist(self):

		artists = self.db.lc_getArtists()
		for artist in tqdm(artists,desc='Artists',**self.logger.tqdm):
			artistpaths = ''
			for song in artist.songs:
				if artist.name in song.path:
					newnam = song.path.split(artist.name)[0] + artist.name
					if artistpaths == '' or len(newnam) < len(artistpaths):
						artistpaths = newnam

			if len(artistpaths):
				artist.path = artistpaths
		self.db.session.commit()
  
	def splitExisting(self,parentFolders:list=None,byChoice=False):
		dld = Path('E:/Deemix/Artists' )
		std = [Path(x) for x in parentFolders]

		for folder in tqdm(dld.iterdir(),desc='Folders',**self.logger.tqdm):
			finpath = False
			for f in std:
				if folder.name == f.name or any(ext for ext in ['various','varios'] if ext in f.name.lower() ):
					break
				if folder.name[0].encode('utf-8').isalpha():
					newf = f / folder.name[0].upper() / folder.name
					newpath = dld / f.name / folder.name[0].upper() / folder.name
				else:
					newf = f / '#' / folder.name
					newpath = dld / f.name / '#' / folder.name
				if newf.exists():
					tqdm.write(f'{folder} -> {newf} -> {newpath}')
					shutil.move(folder,newpath)
					finpath = True
					break
			if not finpath and byChoice:
				tqdm.write(f'{folder.name}')
				for x in folder.rglob('*'): 
					if x.is_file(): 
						tqdm.write(f'\t{x.name}')
				ch = input(f':\t')
				match ch:
					case 'e':
						newpath = dld / std[0].name / folder.name[0].upper() / folder.name
					case 's':
						newpath = dld / std[1].name / folder.name[0].upper() / folder.name
					case _:
						continue
				tqdm.write(f'{folder} -> {newpath}')
				shutil.move(folder,newpath)
		 
	def refreshLoc(self):

		songs = self.db.get_Songs({})
		for song in tqdm(songs,desc='LocalRefresh',**self.logger.tqdm):
			if song['path'] is None or not Path(song['path']).exists():
				tqdm.write(f'DELETED: {song["title"]} - {song["path"]}')
				self.db.delete_Song({'path':song['path']})


	def getDuplicates(self):

		dupes = [x for x in self.db.get_Duplicates()]
		# flacDupes = self.settings.flacDupesFile
		flacDupes = self.settings.flacDupesFile.open('w',encoding='utf-8')
		# mp3Dupes = self.settings.mp3DupesFile
		mp3Dupes = self.settings.mp3DupesFile.open('w',encoding='utf-8')
		flacDupes.write(f'#EXTM3U \n')
		mp3Dupes.write(f'#EXTM3U \n')
  
		for item in tqdm(dupes,"DUPES",**self.logger.tqdm):
			if any([x for x in item['songs'] if x.endswith('flac')]):
				ot = flacDupes
			else:
				ot = mp3Dupes
			for song in item['songs']:
				song = Path(song)
				ot.write(f'#EXTINF:1,{item["isrc"]},{song.name}\n')
				ot.write(f'{song.absolute().as_posix()}\n')
	   
		pass

	def displayPlaylists(self):

		playlists = self.db.sp_getAll('playlists')
		dv = Path('SpotifyPlaylist.txt')
		dvw = dv.open('w', encoding='utf-8')
		for playlist in playlists:
			dvw.write(f'{playlist.spotifyuri} {playlist.name}\n')
		pass

	def copyToDevice(self,devicepath):
		dv = Path('deviceCopy.txt')
		dvw = dv.open('r',encoding='utf-8')
		pls = dvw.readlines()

		filenames = []
		
		# show all playlist and allow to choose
			# after a choice is made add that to the deviceCopy.txt file
		# allow the search of artist by deezerid or spotify id and add that to the text file
		# FORMAT: deviceCopy.txt
			# <deezer|spotify>;<playlist|artist|album>;<id> AKA spotify uri
		self.displayPlaylists()
		localsongs = []
		tot = 0
		for x in tqdm(pls,'Playlist',**self.logger.tqdm):
			
			# read deviceCopy.txt into variables to find in the local database
			try:
				uri = re.fullmatch(r'(deezer|spotify):(album|playlist|artist):([A-Za-z\d]*)',x.split()[0].strip())
				if uri is not None:
					streamtype = uri.group(1).lower()
					streamcat = uri.group(2).lower()
					streamid = uri.group(3)
				# get the list of files that are included in the uri ... Album.songs Artist.songs Playlist.songs
				res = self.db.lc_getstream(streamtype,streamcat,streamid)
				m3u = (devicepath/f'{streamid}.m3u').open('w',encoding='utf-8')
				m3u.write(f'#EXTM3U \n#PLAYLIST: {res.name}\n')
				# get all child playlist songs
				pl = res
				tracks = []
				while 1:
					for song in pl.songs:
						if song.song.isrc not in tracks:
							tracks.append(song.song.isrc)
					if not pl.child:
						break
					pl = pl.child
				locals = self.db.lc_getBy('isrc',tracks)
				siz = 0
				for localsong in locals:
					siz += localsong.file_size
					pt = Path(localsong.path)
					m3u.write(f'{pt.name}\n')
					if pt not in filenames:
						filenames.append(pt)
						tot += localsong.file_size
						localsongs.append(localsong)
				tqdm.write(f"Playlist: {siz/1000000:10.2f}MB {res.name:50} Total: {(tot/1073741824):10.2f}GiB")
				
			except:
				continue
			
		for x in tqdm(filenames,**self.logger.tqdm):
			movto = devicepath / x.name
			if movto.exists():
				continue
			else:
				# tqdm.write(f'{x.as_posix()},{movto.as_posix()}')
				shutil.copy(x,movto)
		pass

	def findFolders(self,folders:list):
		generators = []
		for folder in folders:
			if not os.path.exists(folder):
				continue
			generators.append(os.walk(folder))
		broken = self.settings.brokenFolderStructFile.open('w',encoding='utf-8')
		for cwd, folders, files in tqdm(chain(*generators),desc='Scanning Organization',**self.logger.tqdm):
			cw = Path(cwd)
			nms = [x.lower() for x in folders]
			if cw.name.lower() in nms:
				broken.write(f'{cw.absolute().as_posix()}\n')
	
	
	def deletEmptyDirs(self,path):
		lsd = sorted(os.listdir(path))
		size = len(lsd)
		if size == 0:
			return 0
		for f in lsd:
			fname = os.path.join(path,f)
			if os.path.isdir(fname):
				fsize = self.deletEmptyDirs(fname)
				if fsize == 0:
					os.rmdir(fname)
					tqdm.write(f"DELETED PATH {fsize} {fname}")
					size -= 1
			elif os.path.isfile(fname):
				if f.endswith('.lrc'):
					if not (os.path.exists(fname.replace('.lrc','.mp3')) or os.path.exists(fname.replace('.lrc','.flac'))):
						send2trash(fname)
						tqdm.write(f"DELETED LRC {size} {fname}")
						size -= 1

		return size

	def findNoAlbumArtists(self,folders:list):
		songs = []
		newf = []
		for folder in folders:
			songs += self.db.lc_getAllSongs(Path(folder).absolute().as_posix())
		for song in tqdm(songs,desc='FixAlbumArtists',**self.logger.tqdm):
			if Path(song.path).exists():
				if song.album and len(song.album.artists) == 1: continue
				pt = LocalFile(song.path)
				if pt.metadata is None: 
					continue
				if pt.filetype == 'flac' and (pt.checkfilefor('albumartist', index=-1) is None or len(pt.checkfilefor('albumartist', index=-1)) > 1):
					pt.clearExtraAlbumArtists()
					pt.save()
					tqdm.write(song.path)
					self.db.session.delete(song)
					newf.append(song.path)
					pass
				elif pt.filetype == 'mp3' and (pt.checkfilefor('albumartist', index=-1) is None or len(pt.checkfilefor('albumartist', index=-1)) > 1):
					pt.clearExtraAlbumArtists()
					pt.save()
					tqdm.write(song.path)
					self.db.session.delete(song)
					newf.append(song.path)
					pass
			if len(newf) % 100 == 99:
				self.addNewFiles(newf)
				self.db.session.commit()
				newf = []
	
	def findTracksWithNoPlaylist(self):
		tracks = self.db
		pass


	def clearVariousArtists(self, variousFolder):
		ends = [".mp3", '.flac', '.m4a', '.wav']
		variousFolder = Path(variousFolder)
		generators = [variousFolder.rglob(f'*{ending}') for ending in ends]
		outputFolder = variousFolder.parent / 'output'
		for fl in chain(*generators):
			flinfo = LocalFile(fl.absolute().as_posix())
			if flinfo.makeSingle(): # if the metadata is changed move into new location
				try:
					newname = outputFolder / f"{flinfo.checkfilefor('artist')}/Singles/{flinfo.checkfilefor('date')} - {flinfo.checkfilefor('album')}/{int(flinfo.checkfilefor('tracknumber')):02d} - {flinfo.checkfilefor('title')}.{flinfo.filetype}"
					if newname.exists(): raise
					newname.parent.mkdir(parents=True,exist_ok=True)
					shutil.move(fl,newname)
				except Exception as e:
					print(f"Couldnt move {fl} to {newname}")
		pass