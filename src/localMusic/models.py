from pydantic import BaseModel, Field
from typing import List, Optional
from src.config.models import DatabaseInfo

class Song(BaseModel):
	path:str
 
	title:str
	isrc:Optional[str] = Field(default=None)
	length:int
	bitrate:int
	md5:str
	file_size:int
	album:Optional[str] = Field(default=None)
	language:Optional[str] = Field(default=None)
	artists:Optional[List[str]]
	albumartists:Optional[List[str]]
	
	