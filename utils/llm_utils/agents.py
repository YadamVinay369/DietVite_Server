import json
from dotenv import load_dotenv
import os
load_dotenv()
from groq import Groq
from datetime import datetime, timedelta,date
import random
import math
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

def missy_monitor(days_skipped):
    days_string = ", ".join(str(d) for d in days_skipped)
    missy_monitor_prompt = os.getenv("MISSY_MONITOR_PROMPT").format(days_string=days_string)
    missy_monitor_system_message = os.getenv("MISSY_MONITOR_SYSTEM_MESSAGE")
    return query(system_message=missy_monitor_system_message, user_query=missy_monitor_prompt)

def calculate_diet_score_with_penalty(
    overall_nutrient_intake_sheet,
    balanced_diet_sheet,
    daily_frequency_list,
    frequency_of_missing,
    start_date,
    ideal_frequency=3,
    penalty_strength=2,
    over_penalty_multiplier=1.5,
    high_risk_nutrients=("Calories (kcal)","Sodium (mg)","Potassium (mg)","Iron (mg)","Vitamin D (mg)"),
    cheat_threshold_over=2.0,
    cheat_threshold_freq=6,
    max_discipline_days=60):
    nutrient_scores = []
    cheat_days = set()

    num_days = len(next(iter(overall_nutrient_intake_sheet.values()))) if overall_nutrient_intake_sheet else 0

    # 1️⃣ Nutrient Accuracy Calculation
    for nutrient, ideal_val in balanced_diet_sheet.items():
        daily_intakes = overall_nutrient_intake_sheet.get(nutrient, [])
        if not daily_intakes or ideal_val == 0:
            continue

        day_scores = []
        for day_idx, actual in enumerate(daily_intakes):
            deviation_ratio = abs(actual - ideal_val) / ideal_val
            penalty_factor = penalty_strength

            # 🚨 Overconsumption penalty
            if actual > ideal_val:
                overshoot_factor = (actual / ideal_val) - 1
                if nutrient in high_risk_nutrients:
                    penalty_factor *= over_penalty_multiplier * (1 + overshoot_factor ** 2)
                else:
                    penalty_factor *= (1 + overshoot_factor ** 2)

                # ✅ Mark cheating day
                if actual / ideal_val >= cheat_threshold_over:
                    print(f"Cheat nutrient: {nutrient}, Day: {day_idx}, Actual: {actual}, Ideal: {ideal_val}")
                    cheat_days.add(day_idx)

            score = math.exp(-penalty_factor * deviation_ratio)
            day_scores.append(score)

        nutrient_scores.append(sum(day_scores) / len(day_scores))

    avg_nutrient_score = sum(nutrient_scores) / len(nutrient_scores) if nutrient_scores else 0

    # 2️⃣ Frequency Penalty
    freq_scores = []
    for day_idx, freq in enumerate(daily_frequency_list):
        daily_freq_score = 1 / (1 + abs(freq - ideal_frequency))
        freq_scores.append(daily_freq_score)

        if freq > cheat_threshold_freq:
            cheat_days.add(day_idx)

    avg_freq_penalty = sum(freq_scores) / len(freq_scores) if freq_scores else 0

    # 3️⃣ Missing Days Penalty
    missing_penalty = 1 / (1 + frequency_of_missing)

    # 4️⃣ Discipline Bonus (more days → higher score, capped at max_discipline_days)
    discipline_bonus = math.log1p(min(num_days, max_discipline_days)) / math.log1p(max_discipline_days)
    # This will be between 0–1, giving a % boost

    # 5️⃣ Final Score (weights + discipline)
    base_score = avg_nutrient_score * 0.7 + avg_freq_penalty * 0.2 + missing_penalty * 0.1
    final_score = base_score * (0.8 + 0.2 * discipline_bonus)  # 20% max bonus from discipline
    final_score *= 100

    # 🔄 Convert cheat indices → dates
    if isinstance(start_date, datetime):
        start_dt = start_date
    elif isinstance(start_date, date):
        start_dt = datetime.combine(start_date, datetime.min.time())
    elif isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%d-%m-%Y")
    cheat_dates = [(start_dt + timedelta(days=i)).strftime("%d-%m-%Y") for i in sorted(cheat_days)]

    return round(final_score, 2), cheat_dates


