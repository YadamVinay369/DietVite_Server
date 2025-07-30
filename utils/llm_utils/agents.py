import json
from dotenv import load_dotenv
import os
load_dotenv()
from groq import Groq
import random
from json_repair import repair_json

api_keys = json.loads(os.getenv("API_KEYS"))

# utility functions

def query(system_message, user_query):
    try:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_query}
        ]

        random_index_api_key = random.randint(0, len(api_keys) - 1)
        client = Groq(api_key=api_keys[random_index_api_key])
        models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
        random_index_model = random.randint(0, len(models) - 1)
        response = client.chat.completions.create(
            model=models[random_index_model],
            messages=messages,
            temperature=0.6
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Error during Groq query: {e}")
        return "ERROR: Unable to generate response at the moment."

def clean_json(response: str) -> dict:
    """
    Removes Markdown formatting and repairs malformed JSON using jsonrepair.
    Returns a Python dictionary.
    """
    cleaned = response.replace("```json", "").replace("```", "").strip()
    repaired = repair_json(cleaned)
    return json.loads(repaired)

def update(overall_nutrient_intake_sheet,nutrient_sheet_per_food_item):

  for key,val in nutrient_sheet_per_food_item.items():
    overall_nutrient_intake_sheet[key].append(val)

  return overall_nutrient_intake_sheet

# agents

def nutri_orchestrator(user_query):
    classification_prompt = os.getenv("CLASSIFICATION_PROMPT").format(user_query=user_query)
    classification_system_message = os.getenv("CLASSIFICATION_SYSTEM_PROMPT")
    return query(system_message=classification_system_message, user_query=classification_prompt)

def omni_knowledge_bot(user_query):
    omni_knowledge_bot_prompt = os.getenv("OMNI_KNOWLEDGE_BOT_PROMPT").format(user_query=user_query)
    omni_knowledge_bot_system_message = os.getenv("OMNI_KNOWLEDGE_BOT_SYSTEM_MESSAGE")
    return query(system_message=omni_knowledge_bot_system_message, user_query=omni_knowledge_bot_prompt)

def nutri_scanner(nutrient_sheet_per_food_item, user_query):
    nutriscanner_prompt = os.getenv("NUTRISCANNER_PROMPT").format(user_query=user_query,nutrient_sheet_per_food_item=nutrient_sheet_per_food_item)
    nutriscanner_system_message = os.getenv("NUTRISCANNER_SYSTEM_MESSAGE")
    return query(system_message=nutriscanner_system_message, user_query=nutriscanner_prompt)

def gap_detector(overall_nutrient_intake_sheet,balanced_diet_sheet):
  gap_sheet = {}
  for key,value in balanced_diet_sheet.items():
    intake_list = overall_nutrient_intake_sheet.get(key, [])
    gap_sheet[key]=value - sum(intake_list) / len(intake_list) if intake_list else 0
  return gap_sheet

def diet_builder(gap_sheet):
    diet_builder_prompt = os.getenv("DIET_BUILDER_PROMPT").format(gap_sheet=gap_sheet)
    diet_builder_system_message = os.getenv("DIET_BUILDER_SYSTEM_MESSAGE")
    return query(system_message=diet_builder_system_message, user_query=diet_builder_prompt)

def nutri_reflector(gap_sheet):
    nutri_reflector_prompt = os.getenv("NUTRI_REFLECTOR_PROMPT").format(gap_sheet=gap_sheet)
    nutri_reflector_system_message = os.getenv("NUTRI_REFLECTOR_SYSTEM_MESSAGE")
    return query(system_message=nutri_reflector_system_message, user_query=nutri_reflector_prompt)



