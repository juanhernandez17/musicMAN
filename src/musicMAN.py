import json, hashlib
import atexit
from typing import Any
from src.spotifyMusic.mixn import SpotifyMAN
from src.deezerMusic.mixn import DeezerMAN
from src.monitor.mixn import MonitorMixn
from src.localMusic.mixn import LocalMAN
from src.plex.plex import PlexMAN
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path
from pymongo.mongo_client import MongoClient
from datetime import datetime
import os
import yaml
# from plex.plexserver import plexServ
from time import sleep
# from tqdm import tqdm
from src.config.utils import parse_date
load_dotenv()


class _Config:
	defaults = {
		'logFile':"output/output.log",
		'playlistFolder': 'output/playlists',
		'missingSongsFile': 'output/missingSongs.m3u',
		'failedDLsFile':'output/failedDL.txt',
		'downloadedSongsFile':'output/Downloaded.txt',
		'monitoredFile':'input/Monitor.txt',
		'arlListFile':'input/arl.txt',
		'workingARLsFile':'input/ARLworking.txt',
		'flacDupesFile': 'output/dupesflac.m3u',
		'mp3DupesFile': 'output/dupesmp3.m3u',
		'brokenFolderStructFile': 'output/broken.txt',
		'spotifyplaylistFolder': 'output/spotifyplaylists',
		'spotifyratelimitDate':datetime.utcnow()
	}
	settings = {}
	def __init__(self,configFile:Path):
		self.load_config(configFile)

	def __setattr__(self, name: str, value: Any) -> None:
		try:
			self.settings[name] = value
		except KeyError:
			return getattr(self.args, name)
		pass

	def __getattr__(self, name):
		try:
			return self.settings[name]
		except KeyError:
			return getattr(self.args, name)
	# turn strings to Path types
	def load_config(self,configFile):
		print('Loading config',end='\r')
		if configFile.exists():
			config = yaml.load(configFile.read_text(),yaml.Loader)
		else: 
			config = self.defaults
		self.from_dict(config)

	def from_dict(self,data):
		for x, y in data.items():
			if x.endswith('Folder'):
				self.settings[x] = Path(y)
				self.settings[x].mkdir(parents=True,exist_ok=True)
			elif x.endswith('File'):
				self.settings[x] = Path(y)
			elif x.endswith('Date'):
				self.settings[x] = parse_date(y)
			else:
				self.settings[x] = y
				

	# turns a Path object into a nested dict
	def to_dict(self,data=None):
		if data is None: data=self.settings
		jsondata = {}
		for k,v in data.items():
			if k.endswith('Date'):
				jsondata[k] = v.strftime('%Y-%m-%d %H:%M:%S')
			else:
				jsondata[k] = str(v)
		return jsondata

class Logger():
	def __init__(self,outputfile='output.txt'):
		self.tqdm = {
			'leave':False,
			'ncols':100
		}
		self.tqdmsize = 100
		self.outputfile = Path(outputfile).open('w',encoding='utf-8')
		pass
	def processOutput(self,data):
		pass
	def toCli(self,outputstring):
		tqdm.write(outputstring)
		pass
	def toFile(self,outputstring):
		self.outputfile.write(outputstring)
		pass

class musicMAN(MonitorMixn):
	def __init__(self):

		client = MongoClient(os.getenv('MONGO'))
		db = client.musicMAN_db
		self.settingsFile = Path('config.yaml')
		self.settings = {		}
		self.settings = _Config(self.settingsFile)
		self.logger = Logger(self.settings.logFile)
		atexit.register(self.saveSettings)
		super().__init__(db)

		self.spotify = SpotifyMAN(db,self.settings, self.logger)
		self.deezer = DeezerMAN(db,self.settings, self.logger)
		self.local = LocalMAN(db,self.settings,self.logger)
		self.plex = PlexMAN(self.settings,self.logger)
		pass

	def md5_string(self, stringlist):
		hash_md5 = hashlib.md5()
		for chunk in stringlist:
			hash_md5.update(chunk.encode('utf-8'))
		return hash_md5.hexdigest().upper()

	def saveSettings(self):
		print('Saving config',end='\r')
		self.settings.spotifyratelimitDate = self.spotify.sp.ratelimit
		tmp = self.settings.to_dict()
		yaml.dump(tmp,self.settingsFile.open('w',encoding='utf-8'))