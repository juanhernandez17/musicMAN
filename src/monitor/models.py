from pydantic import BaseModel, Field
from typing import List,Optional
from datetime import datetime, timedelta


class Monitor(BaseModel):

	
	spotifyid: Optional[str] = Field(default=None)
	deezerid: Optional[int] = Field(default=None)
	spotifyuri: Optional[str] = Field(default=None)
 
	name:str
	monitor_type: str
	quality: str
	last_checked:Optional[datetime] = Field(default=None)
	next_check:Optional[datetime] = Field(default=None)
	refresh_interval:int = Field(default=604800) # one week
 
	def set_next_check(self):
		if self.last_checked and self.refresh_interval:
			self.next_check = self.last_checked + timedelta(seconds=self.refresh_interval)