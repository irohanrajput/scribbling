from pydantic import BaseModel
from typing import List

class FunctionSchema(BaseModel):
    function_name: str
    has_entry_log: bool
    has_error_log: bool
    has_try_except: bool
    calls_external_io: bool

class FileSchema(BaseModel):
    file_name:str
    functions: list[FunctionSchema]



