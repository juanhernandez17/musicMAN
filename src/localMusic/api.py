import sys, hashlib
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen import File
from pathlib import Path
from mutagen.id3 import TPE2
class LocalFile():
	def __init__(self,filename=None):
		super(LocalFile,self).__init__()
		self.metadata = None
		self.nametoMP3 = {
			"album": 'TALB',
			"artist": 'TPE1',
			"albumartist": 'TPE2',
			"bpm": 'TBPM',
			"copyright": 'TCOP',
			"discnumber": 'TPOS',
			"genre": 'TCON',
			"isrc": 'TSRC',
			"length": 'TLEN',
			"publisher": 'TPUB',
			"title": 'TIT2',
			"tracknumber": 'TRCK',
			"lyrics": 'USLT::XXX',
			"source": 'TXXX:SOURCE',
			"sourceid": 'TXXX:SOURCEID',
			"itunesadvisory": 'TXXX:ITUNESADVISORY',
			"barcode": 'TXXX:BARCODE',
			"replaygain_track_gain": 'TXXX:replaygain_track_gain',
			"syncedlyrics": 'SYLT::XXX',
			"date": 'TDRC',
			"size":"size"
		}
		self.nametoM4A = {
			"title": '\xa9nam',
			"album": '\xa9alb',
			"artist": '\xa9ART',
			"albumartist": 'aART',
			"date": '\xa9day',
			"genre": '\xa9gen',
			"lyrics": '\xa9lyr'
		}
		if filename:
			self.fileobj = Path(filename)
			if not self.fileobj.exists():
				return None
			self.filetype = self.fileobj.suffixes[-1][1:]
			self.openMutagen(filename)
			
  
	def clearExtraAlbumArtists(self):
     
		albatagname = 'albumartist'
		arttagname = 'artist'
		ts = None
		if self.filetype == 'flac':
			if albatagname in self.metadata:
				ts = self.metadata.pop(albatagname)
			elif self.metadata.get(arttagname):
				ts = self.metadata.get(arttagname)
			if ts:
				self.metadata[albatagname] = ts[0]
		elif self.filetype == 'mp3':
			albatagname = self.nametoMP3[albatagname]
			arttagname = self.nametoMP3[arttagname]
			if albatagname in self.metadata:
				ts = self.metadata.pop(albatagname)
			elif self.metadata.get(arttagname):
				ts = self.metadata.get(arttagname)
			if ts:
				self.metadata.tags.add(TPE2(text=ts[0]))
		return
   
	def save(self):
		if self.metadata:
			self.metadata.save()
  
	def md5_file(self,filename=None):
		hash_md5 = hashlib.md5()
		if filename:
			f = Path(filename).open('rb')
		else:
			f = self.fileobj.open("rb")
		for chunk in iter(lambda: f.read(1024*hash_md5.block_size), b""):
			hash_md5.update(chunk)
		f.close()
		return hash_md5.hexdigest().upper()

	def openMutagen(self,filepath):
		try:
			if '.flac' in filepath:
				self.metadata = FLAC(filepath)
			elif '.mp3' in filepath:
				self.metadata = MP3(filepath)
			else:
				self.metadata = File(filepath)
		except Exception as err:
			print(err)
			print(f"ERROR: Can't open the file {filepath}")
			print("ERROR", sys.exc_info()[0], "occurred.")
			self.metadata = None

	def checkfilefor(self, attr, upper=False, integer=False, index=0):

		try:
			if self.filetype == 'mp3' or self.filetype == 'wav':
				if attr not in self.nametoMP3:
					return None
				attr = self.nametoMP3[attr]
				if index == -1:
					return [c for x in self.metadata.tags.getall(attr) for c in x]
			elif self.filetype == 'm4a':
				if attr not in self.nametoM4A:
					return None
				attr = self.nametoM4A[attr]
			if attr in self.metadata:
				if index == -1:
					return self.metadata[attr]
				if upper:
					return self.metadata[attr][index].upper()
				if integer:
					return int(self.metadata[attr][index])
				if self.metadata[attr] != '':
					return self.metadata[attr][index]
			else:
				return None

		except Exception as err:
			print(err)
			print(f'ERROR getting {attr}')
			print("ERROR", sys.exc_info()[0], "occurred.")
			return None

	def formatfileinfo(self):

		if self.metadata == None:
			print('error')
			return None

		try:
			sz = self.fileobj.stat().st_size
			bitrate = int(self.metadata.info.bitrate / 1000)
			length = int(self.metadata.info.length)
			hashnum = self.md5_file()
			title = self.checkfilefor('title')
			album = self.checkfilefor('album')
			artist = self.checkfilefor('artist', index=-1)
			isrc = self.checkfilefor('isrc', upper=True)
			albart = self.checkfilefor('albumartist', index=-1)
		except Exception as err:
			print(err)
			print('ERROR getting attributes')
			print("ERROR", sys.exc_info()[0], "occurred.")
			return None
		return {
			"path": self.fileobj.absolute().as_posix(),
			"bitrate": bitrate,
			"artists": list(set(artist)) if artist else None,
			"album": album,
			"albumartists": list(set(albart)) if albart else None,
			"length": length,
			"title": title,
			"isrc": isrc,
			"md5": hashnum,
			"file_size":sz
		}
  
	def newcheckfilefor(self, attr, upper=False, integer=False, index=0):

		try:
			if self.filetype == 'mp3' or self.filetype == 'wav':
				if attr not in self.nametoMP3:
					return None
				attr = self.nametoMP3[attr]
				if index == -1:
					return [c for x in self.metadata.tags.getall(attr) for c in x]
			elif self.filetype == 'm4a':
				if attr not in self.nametoM4A:
					return None
				attr = self.nametoM4A[attr]
			if attr in self.metadata:
				if index == -1:
					return self.metadata[attr]
				if upper:
					return self.metadata[attr][index].upper()
				if integer:
					return int(self.metadata[attr][index])
				if self.metadata[attr] != '':
					return self.metadata[attr][index]
			else:
				return None

		except Exception as err:
			print(err)
			print(f'ERROR getting {attr}')
			print("ERROR", sys.exc_info()[0], "occurred.")
			return None