from datetime import datetime
from time import time
import hashlib

def parse_date(value):
	formats = [
		"%Y-%m-%dT%H:%M:%SZ","%Y-%m-%d %H:%M:%S","%Y-%m-%d","%Y"
	]
	if value is not None:
		for format in formats:
			try:
				return datetime.strptime(value,format)
			except:
				continue
	return datetime.fromtimestamp(0)

def handle_exceptions(f):
	def wrapper(*args, **kw):
		try:
			return f(*args, **kw)
		except Exception as e:
			self = args[0]
			return None
	return wrapper


def timer_func(func): 
    def wrap_func(*args, **kwargs): 
        t1 = time() 
        result = func(*args, **kwargs) 
        t2 = time() 
        print(f'Function {func.__name__!r} executed in {(t2-t1):.4f}s') 
        return result 
    return wrap_func


def md5_string(stringlist):
	hash_md5 = hashlib.md5()
	for chunk in stringlist:
		hash_md5.update(chunk.encode('utf-8'))
	return hash_md5.hexdigest().upper()