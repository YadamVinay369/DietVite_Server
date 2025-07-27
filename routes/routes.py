from fastapi import APIRouter

router = APIRouter()

@router.post('/missy_monitor')
def check_skips():
    '''
    1. check for skip dates,
    if found then call missymonitor that return yield messages
    2. update the start date in database
    '''
    pass

@router.post('/query')
def query():
    '''
    1. call nutriscanner and returns back response
    2. update the overall_nutrient_intake_sheet
    '''
    pass

@router.get('/diet_suggestions')
def diet_suggestions():
    '''
    1. calls gap detector
    2. calls diet_builder and returns back response
    '''
    pass

@router.get('/review')
def review():
    '''
    1. calls nutriReflector and returns back the response
    '''
    pass

@router.post('/reset')
def reset():
    '''
    can be called right after first signup and login
    1. asks for timeframe
    2. resets the nutrient intake sheet back to zero
    '''
    pass