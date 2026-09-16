from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    format: Literal["step", "pdf", "dxf", "doc", "xls", "ppt", "md", "txt", "html"]
    codes: List[str]
    folder_path: Optional[str] = None
