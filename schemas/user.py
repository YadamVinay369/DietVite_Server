from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import date

class UserBase(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: EmailStr = Field(...,description="email is a required.")
    
class UserCreate(UserBase):
    password: str = Field(...,min_length=6)
    start_date: Optional[date] = None
    overall_nutrient_sheet: Optional[Dict[str, Any]] = Field(default=None)
    
class UserInDB(UserBase):
    hashed_password: str
    start_date: Optional[date] = None
    overall_nutrient_sheet: Optional[Dict[str, Any]] = Field(default=None)

    
class UserPublic(UserBase):
    id: str
    start_date: Optional[date] = None
    overall_nutrient_sheet: Optional[Dict[str, Any]] = Field(default=None)
