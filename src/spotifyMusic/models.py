from pydantic import  Field, AliasPath, validator, BaseModel
from typing import List, Optional
from datetime import datetime
from src.config.models import DatabaseInfo
from src.config.utils import parse_date
# Use PYDANTIC to validate and serialize

class SpotifyInfo(BaseModel):
	id:str
	uri: str

class User(SpotifyInfo):
	name: Optional[str] = Field(default=None,alias=AliasPath('display_name'))

class Artist(SpotifyInfo):
	name: str = Field(default=None)

class Album(SpotifyInfo):
	artists: List[Artist] = Field(default=None)
	title: str = Field(default=None)
	total_tracks:int = Field(default=None)
	release_date:datetime

	@validator("release_date", pre=True)
	def parse_release_date(cls, value):
		return parse_date(value)
class Song(SpotifyInfo,DatabaseInfo):
	album: Album = Field(default=None)
	artists: List[Artist] = Field(default=None)
	available_markets: List[str] = Field(default=None)
	disc_number: int = Field(default=None)
	duration_ms: int = Field(default=None)
	explicit: bool
	isrc: Optional[str] = Field(default=None,alias=AliasPath('external_ids', 'isrc'))
	title: str = Field(default=None,alias='name')
	track_number: int = Field(default=None)
	@validator("isrc", pre=True)
	def parse_isrc(cls, value:str):
		if value is None: return None
		return value.upper().replace('-','').replace('_','')
   
	class Config:
		populate_by_name = True
		arbitrary_types_allowed = True
  
class Track(BaseModel):
	added_at:datetime
	added_by:User
	id:Optional[str] = Field(default=None,alias=AliasPath('track','id'))
	isrc: Optional[str] = Field(default=None,alias=AliasPath('track','external_ids', 'isrc'))
	name: Optional[str] = Field(default=None,alias=AliasPath('track','name'))
	@validator("added_at", pre=True)
	def parse_added_at(cls, value):
		return parse_date(value)
	@validator("isrc", pre=True)
	def parse_isrc(cls, value:str):
		if value is None: return None
		return value.upper().replace('-','').replace('_','')

class Playlist(SpotifyInfo,DatabaseInfo):
	title:str= Field(alias=AliasPath('name'))
	collaborative: bool = Field(default=None)
	description: str = Field(default=None)
	owner: User
	public: bool = Field(default=None)
	snapshot_id: str = Field(default=None)
	tracks: List[Track] = Field(alias=AliasPath('tracks','items'))
	total_tracks: int = Field(alias=AliasPath('tracks','total'))
	daddy:Optional[str] = Field(default=None)
	child:Optional[str] = Field(default=None)
   
	class Config:
		populate_by_name = True
		arbitrary_types_allowed = True