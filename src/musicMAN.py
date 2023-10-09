import json, hashlib
import atexit
from src.spotifyMusic.mixn import SpotifyMixn
from src.deezerMusic.mixn import DeezerMixn
from src.monitor.mixn import MonitorMixn
from src.localMusic.mixn import LocalMixn
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path
from pymongo.mongo_client import MongoClient
import os
import yaml
# from plex.plexserver import plexServ
from time import sleep
# from tqdm import tqdm
load_dotenv()




class _Config:
	def __init__(self,defaults:dict,configFile:Path):
		self.load_config(defaults,configFile)

	def __getattr__(self, name):
		try:
			return self.settings[name]
		except KeyError:
			return getattr(self.args, name)
	# turn strings to Path types
	def load_config(self,config,configFile):
		print('Loading config',end='\r')
		self.settings = {}
		if configFile.exists():
			tmp = yaml.load(configFile.read_text(),yaml.Loader)
			config['input'] |= tmp['input']
			config['output'] |= tmp['output']
		self.from_dict(config)

	def from_dict(self,data):
		for x, y in data.items():
			if x.endswith('Folder'):
				self.settings[x] = Path(y)
				self.settings[x].mkdir(parents=True,exist_ok=True)
			elif x.endswith('File'):
				self.settings[x] = Path(y)
			else:
				self.settings[x] = y
				

	# turns a Path object into a nested dict
	def to_dict(self,data=None):
		if data is None: data=self.settings
		jsondata = {}
		for k,v in data.items():
			parts= [x for x in v.parts if x != '']
			for part in parts: 
				if part == parts[0]:
					if part not in jsondata:
						jsondata[part] = {}
					tmp = jsondata[part]
				elif part == parts[-1]:
					tmp[k] = part
					pass
				else:
					tmp[part] = {}
					tmp = tmp[part]
					pass
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

class musicMAN(SpotifyMixn,DeezerMixn,MonitorMixn,LocalMixn):
	def __init__(self):

		client = MongoClient(os.getenv('MONGO'))
		db = client.musicMAN_db
		self.settingsFile = Path('config.yaml')
		self.settings = {
			'logFile':"output/output.log"
		}
		super().__init__(db)
		self.settings = _Config(self.settings,self.settingsFile)
		self.logger = Logger(self.settings.logFile)
		atexit.register(self.saveSettings)
		pass

	def md5_string(self, stringlist):
		hash_md5 = hashlib.md5()
		for chunk in stringlist:
			hash_md5.update(chunk.encode('utf-8'))
		return hash_md5.hexdigest().upper()

	def saveSettings(self):
		print('Saving config',end='\r')
		tmp = self.settings.to_dict()
		yaml.dump(tmp,self.settingsFile.open('w',encoding='utf-8'))