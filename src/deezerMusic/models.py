from pydantic import  Field, AliasPath, validator, BaseModel,AliasChoices
from typing import List,Optional
from datetime import datetime
from src.config.models import DatabaseInfo
from src.config.utils import parse_date

# Use PYDANTIC to validate and serialize
class DeezerMixn(BaseModel):
	id:int

class User(DeezerMixn):
	name:str

class Artist(DeezerMixn):
	name:str
	main:bool = Field(alias=AliasPath('role'))
	@validator("main", pre=True)
	def parse_main(cls, value):
		return value == "Main"

	class Config:
		populate_by_name = True
		arbitrary_types_allowed = True
class Album(DeezerMixn):
	title:str

class Track(BaseModel):
	added_at:datetime = Field(alias=AliasPath('time_add'))
	id: int = Field(alias=AliasPath('id'))
	isrc: str = Field(default=None)
	title: str
	@validator("added_at", pre=True)
	def parse_added_at(cls, value):
		if isinstance(value,int):
			return datetime.fromtimestamp(value)
		return value
	@validator("isrc", pre=True)
	def parse_isrc(cls, value:str):
		if value is None: return None
		return value.upper().replace('-','').replace('_','')
	class Config:
		populate_by_name = True
		arbitrary_types_allowed = True

class Song(DeezerMixn,DatabaseInfo): # Detailed Track
	
	readable: bool
	title: str
	isrc: str = Field(default=None)
	duration: int
	track_position: int = Field(default=None)
	disk_number: int = Field(default=None)
	explicit_lyrics: bool
	available_countries: List[str] = Field(default=None)
	artists: List[Artist] = Field(default=None,alias=AliasPath('contributors'))
	album: Album
	release_date:datetime = Field(default=None)

	@validator("release_date", pre=True)
	def parse_release_date(cls, value):
		return parse_date(value)
	@validator("isrc", pre=True)
	def parse_isrc(cls, value:str):
		if value is None: return None
		return value.upper().replace('-','').replace('_','')
   
	class Config:
		populate_by_name = True
		arbitrary_types_allowed = True
class Playlist(DeezerMixn,DatabaseInfo):
	title:str
	description:Optional[str] = Field(default='')
	duration:int
	public:bool
	collaborative:bool
	nb_tracks:int
	checksum:str
	creation_date:datetime = Field(default=datetime.fromtimestamp(0),alias=AliasPath('time_add'))
	creator:User
	update_date:datetime = Field(default=datetime.fromtimestamp(0),alias=AliasPath('time_mod'))

	tracks:List[Track] = Field([])
	@validator("creation_date","update_date", pre=True)
	def parse_date(cls, value):
		if isinstance(value,int):
			return datetime.fromtimestamp(value)
		return value
	class Config:
		populate_by_name = True
		arbitrary_types_allowed = True