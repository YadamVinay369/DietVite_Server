from schemas.user import UserCreate, UserPublic
from utils.db import db
from passlib.context import CryptContext
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from utils.jwt_create_validate import create_access_token

router = APIRouter()
pwd_context = CryptContext(schemes=['bcrypt'],deprecated='auto')

@router.post("/signup",response_model=UserPublic)
async def signup(user: UserCreate):
    if await db.users.find_one({"username":user.username}):
        raise HTTPException(status_code=400,detail="User already exists with such username.")
    if await db.users.find_one({"email":user.email}):
        raise HTTPException(status_code=400,detail="User already exists with such email.")
    
    hashed_pw = pwd_context.hash(user.password)
    
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_pw
    del user_dict["password"]
    
    result = await db.users.insert_one(user_dict)
    
    return UserPublic(
        id=str(result.inserted_id),
        username=user.username,
        email=user.email
    )
    
@router.post("/login")
async def login(user: UserCreate):
    db_user = await db.users.find_one({"username":user.username})
    if not db_user:
        db_user = await db.users.find_one({"email":user.email})
        
    if not db_user:
        raise HTTPException(status_code=404,detail="User not found!")
    
    if not pwd_context.verify(user.password,db_user["hashed_password"]):
        raise HTTPException(status_code=401,detail="Invalid Credentials") 
    
    access_token = create_access_token(data={"sub":str(db_user["_id"])})
    
    response = JSONResponse(
        content={
            "message": "login successful!",
            "user":{
                "id": str(db_user["_id"]),
                "username": db_user["username"],
                "email": db_user["email"]
            }
        }
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600,
    )
    
    return response