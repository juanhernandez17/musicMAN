import pymongo
from src.config.utils import handle_exceptions
from src.monitor.models import Monitor

class MonitorDatabase():
	def __init__(self,db):
		self.monitor = db['monitor']
		self.monitor.create_index([("spotifyid", pymongo.ASCENDING),("deezerid", pymongo.ASCENDING)], unique=True)
		# self.monitor.create_index([("deezerid", pymongo.ASCENDING)], unique=True)
  
	@handle_exceptions
	def validate_Monitor(self,data):
		return Monitor(**data)
	@handle_exceptions
	def validate_MonitorUpdate(self,data):
		return data

	@handle_exceptions
	def update_Monitor(self,filter,data):
		data = self.validate_MonitorUpdate(data)
		if data:
			return self.monitor.update_one(filter,data)
		return None
	@handle_exceptions
	def add_Monitor(self,data):
		valid = self.validate_Monitor(data)
		if valid:
			valid.set_next_check()
			return self.monitor.insert_one(valid.model_dump())
		return None
	def get_Monitor(self,q,params=None):
		if params is None: params = {}
		return self.monitor.find_one(q,params)

	def get_Monitors(self,q,params=None):
		if params is None: params = {}
		return self.monitor.find(q,params)

	def exists_Monitors(self,monitorl:list,params=None):
		if params is None: params = {}
		return self.monitor.find({ 'id': { '$in': monitorl } }, params)