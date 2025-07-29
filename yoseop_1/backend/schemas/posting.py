from pydantic import BaseModel
from typing import Optional

class PostingResponse(BaseModel):
    posting_id: int
    company_id: int
    position_id: int
    content: Optional[str]
