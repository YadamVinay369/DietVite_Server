from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status
from bson import ObjectId
from utils.db import db
from utils.jwt_create_validate import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Assuming you have this function already
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = verify_access_token(token)  # your JWT verification function
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
