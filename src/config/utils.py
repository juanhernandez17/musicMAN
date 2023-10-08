from datetime import datetime


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