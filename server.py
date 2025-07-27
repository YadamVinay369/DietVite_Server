from fastapi import FastAPI
from routes.routes import router

app = FastAPI()

app.include_router(router)

@app.get('/')
def home():
    
    '''
    after logging in , 
    1. we fetch overall_nutrient_intake_sheet
    2. Check missing dates and call missy monitor if required
    '''
    print("Welcome to Home...!")
    return {"message":"Home called!" }

