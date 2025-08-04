from fastapi import APIRouter, Depends, HTTPException, status
from utils.auth_utils.route_checkup import get_current_user
from utils.db_utils.db import db
from pydantic import BaseModel, Field
from datetime import datetime,timedelta,date
from bson import ObjectId
from dotenv import load_dotenv
load_dotenv()
import os
import json
from utils.llm_utils.agents import nutri_orchestrator,omni_knowledge_bot,nutri_scanner,gap_detector,diet_builder,nutri_reflector,clean_json,missy_monitor

router = APIRouter()

class Query(BaseModel):
    query: str
    
class TimeFrame(BaseModel):
    time_frame: int = Field(...,ge=1)

@router.post('/start')
async def start(payload: TimeFrame,user_id: dict = Depends(get_current_user)):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        user["start_date"] = datetime.utcnow()
        user["time_frame"] = payload.time_frame
        nutrients_list = json.loads(os.getenv("NUTRIENTS_LIST"))
        overall_nutrient_intake_sheet = {nutrient: [0] * payload.time_frame for nutrient in nutrients_list}
        user["overall_nutrient_sheet"] = overall_nutrient_intake_sheet
        user["attendance" ] = [False] * payload.time_frame
        
        await db.users.replace_one(
            {"_id": ObjectId(user_id)},
            user,
            upsert=True
        )
        user["_id"] = str(user["_id"])
        user["start_date"] = user["start_date"].isoformat()
        
        return {"message": "Time frame updated","updated user details":user}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred at start: {str(e)}"
        )

@router.post('/query')
async def query(payload: Query,user_id: dict = Depends(get_current_user)):
    '''
    1. call nutriscanner and returns back response
    2. update the overall_nutrient_intake_sheet
    '''
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")         
        
        initial_response = nutri_orchestrator(user_query=payload.query)

        if isinstance(initial_response,str):
            initial_response = initial_response.strip().lower()
        if initial_response == "yes":
            json_output = nutri_scanner(nutrient_sheet_per_food_item=os.getenv("NUTRIENT_SHEET_PER_FOOD_ITEM"),user_query=payload.query)
            try:
                cleaned_json_output,remarks = clean_json(json_output)
            except Exception as e:
                raise ValueError("Error during cleaning: ",e)
            try:
                for key,val in cleaned_json_output.items():
                    index = (datetime.today()-user["start_date"]).days
                    user["overall_nutrient_sheet"][key][index] += val
                index = (datetime.today()-user["start_date"]).days
                user["attendance"][index] = True
                await db.users.replace_one(
                    {"_id": ObjectId(user_id)},
                    user,
                    upsert=True
                )
                user["_id"] = str(user["_id"])
                user["start_date"] = user["start_date"].isoformat()
            except Exception as e:
                raise ValueError("Error while modifying overall nutrient sheet: ",e)
            return {"nutri_scanner":remarks,"updated_user_details":user}
        else:
            response = omni_knowledge_bot(user_query=payload.query)
            return {"omni_knowledge_bot":response}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.get('/diet_suggestions')
async def diet_suggestions(user_id: dict = Depends(get_current_user)):
    '''
    1. calls gap detector
    2. calls diet_builder and returns back response
    '''
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        try:            
            gap_sheet = gap_detector(overall_nutrient_intake_sheet=user["overall_nutrient_sheet"],balanced_diet_sheet=json.loads(os.getenv("BALANCED_DIET_SHEET")))
        except Exception as e:
            raise ValueError("Error in gap_detector: ",e)
        response = diet_builder(gap_sheet=gap_sheet)
        return {"diet_builder":response}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred in dietbuilder: {str(e)}"
        )    

@router.get('/review')
async def review(user_id: dict = Depends(get_current_user)):
    '''
    1. calls nutriReflector and returns back the response
    '''
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        try:            
            gap_sheet = gap_detector(overall_nutrient_intake_sheet=user["overall_nutrient_sheet"],balanced_diet_sheet=json.loads(os.getenv("BALANCED_DIET_SHEET")))
        except Exception as e:
            raise ValueError("Error in gap_detector: ",e)
        response = nutri_reflector(gap_sheet=gap_sheet)
        return {"nutri_reflector":response}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred review: {str(e)}"
        )

@router.get('/reset')
async def reset(user_id: dict = Depends(get_current_user)):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        user["time_frame"] = None
        user["start_date"] = None
        user["overall_nutrient_sheet"] = None
        
        await db.users.replace_one({"_id": ObjectId(user_id)},user,upsert=True)
        
        user["_id"] = str(user["_id"])
        return {"reset_status":True,"updated_user_details":user}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred at reset: {str(e)}"
        )
        
@router.get('/check_skips')
async def check_skips(user_id: dict = Depends(get_current_user)):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        try:            
            today = date.today()
            start_date = user["start_date"].date()  # convert to date only
            attendance = user["attendance"]
            miss_dates = [
                start_date + timedelta(days=i)
                for i, attended in enumerate(attendance)
                if not attended and (start_date + timedelta(days=i)) <= today
            ]
            if len(miss_dates)>0:
                miss_dates_str = [d.strftime("%d-%m-%Y") for d in miss_dates]
                try:
                    comments = missy_monitor(miss_dates_str)
                    return {"Miss_Flag":True,"missy_monitor":comments}
                except Exception as e:
                    raise ValueError("Error in missy_monitor: ",e) 
            else:
                return {"Miss_Flag":False,"missy_monitor":"Kudos! for your discipline!"}
        except Exception as e:
            raise ValueError("Error in gap_detector: ",e)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred check skips: {str(e)}"
        )
