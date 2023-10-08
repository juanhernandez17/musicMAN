from datetime import datetime
from pydantic import Field,BaseModel

class DatabaseInfo(BaseModel):
	last_update:datetime = Field(default=datetime.utcnow())

