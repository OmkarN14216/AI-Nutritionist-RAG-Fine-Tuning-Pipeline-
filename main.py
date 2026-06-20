import os
import json
from typing import Any

from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

from core.patient_intake import validate_patient_intake
from core.pipeline import run_planning_pipeline
from rag.store_builder import ICMRClinicalRetriever
from prompt_engine.compiler import NutritionPromptCompiler

client = Groq(api_key=GROQ_API_KEY)


def _load_rag_scoring_enabled(config_path="config/rag_scoring.json"):
    if not os.path.exists(config_path):
        return True
    try:
        with open(config_path, "r", encoding="utf-8") as file_handle:
            config_data = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return True
    return bool(config_data.get("ENABLE_RAG_SCORING", True))


def write_log_file(filename: str, content: Any):
    os.makedirs("logs", exist_ok=True)
    filepath = os.path.join("logs", filename)
    try:
        if filename.endswith(".json"):
            with open(filepath, "w", encoding="utf-8") as file_handle:
                json.dump(content, file_handle, indent=2, default=str)
        else:
            with open(filepath, "w", encoding="utf-8") as file_handle:
                file_handle.write(str(content))
    except Exception as exc:
        print(f"Failed to write log to {filepath}: {exc}")


def run_nutritionist_pipeline():
    print("\n==================================================")
    print("LAYER 1: Patient Intake")
    print("==================================================")

    patient_payload = validate_patient_intake({
        "age": 24,
        "gender": "male",
        "weight_kg": 84.0,
        "height_cm": 174.0,
        "waist_cm": 96.0,
        "neck_cm": 39.0,
        "activity_level": "sedentary",
        "goal": "weight_loss",
        "target_weight_kg": 72.0,
        "target_weeks": 12,
        "dietary_preference": "eggitarian",
        "medical_conditions": ["gerd"],
        "allergies": [],
        "climate_hot": True,
    })
    print(f"Intake Profile Loaded: {json.dumps(patient_payload, indent=2)}")

    print("\n==================================================")
    print("LAYER 5: Executing Semantic Local RAG Database Lookups")
    print("==================================================")

    retrieved_contexts = []
    try:
        db_retriever = ICMRClinicalRetriever(db_dir="rag/vector_db")
        search_query = (
            "dietary guidelines for management "
            "of obesity and gastric reflux acid acidity gerd"
        )
        retrieved_contexts = db_retriever.retrieve_clinical_context(
            user_query=search_query,
            top_k=3,
        )
        print("\nRetrieved Context Chunks:")
        for context in retrieved_contexts:
            print(f"- {context[:120]}...")
    except Exception as exc:
        print(f"RAG retrieval unavailable, using deterministic fallback contexts: {exc}")

    print("\n==================================================")
    print("LAYERS 2-4, 6-9: Deterministic Planning Pipeline")
    print("==================================================")

    pipeline_result = run_planning_pipeline(
        user_payload=patient_payload,
        retrieved_contexts=retrieved_contexts or None,
        enable_rag_scoring=_load_rag_scoring_enabled(),
        verbose=True,
    )

    calc_results = pipeline_result["calc_results"]
    rule_results = pipeline_result["rule_results"]
    filtered_foods = pipeline_result["filtered_foods"]
    allocation = pipeline_result["allocation"]
    portion_plan = pipeline_result["portion_plan"]
    audit_report = pipeline_result["audit_report"]
    planner_signals = pipeline_result["planner_signals"]

    print(f"\nBMI Category : {calc_results['anthropometrics']['bmi_category']}")
    print(f"Target Calories : {calc_results['thermodynamics']['target_dietary_calories_kcal']} kcal")
    print(f"Target Protein : {calc_results['target_macronutrients_absolute']['protein_grams']} g")
    print(f"Forbidden Ingredients: {len(rule_results['forbidden_ingredients'])} items")
    print(f"Allowed Foods : {len(filtered_foods)}")

    print("\nStructured RAG Signals Extracted:")
    for signal in planner_signals.signals:
        print(
            f"- Category: {signal.food_category} | "
            f"Delta: {signal.score_delta} | Source: {signal.source}"
        )

    write_log_file("rag_signals.json", planner_signals.to_list())
    write_log_file("meal_plan.json", pipeline_result["meal_plan"])
    write_log_file("optimized_plan.json", pipeline_result["optimized_plan"])
    write_log_file("portion_plan.json", portion_plan)
    write_log_file("audit_report.json", audit_report)

    print("\n==================================================")
    print("LAYER 10: Compiling System Prompt & Explanation")
    print("==================================================")

    master_prompt = NutritionPromptCompiler.compile_master_system_prompt(
        user_profile=patient_payload,
        calculation_results=calc_results,
        rule_constraints=rule_results,
        retrieved_icmr_contexts=pipeline_result["retrieved_contexts"],
        filtered_foods=filtered_foods,
        meal_allocation=allocation,
        meal_plan=portion_plan,
        audit_report=audit_report,
    )

    write_log_file("final_prompt.txt", master_prompt)

    print("\nSending consolidated prompt to Llama (Explanation only)...")
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": master_prompt}],
            temperature=0.3,
        )
        diet_plan = completion.choices[0].message.content
        print("\n================ GENERATED DIET PLAN ================\n")
        print(diet_plan)
        print("\n=====================================================\n")
        write_log_file("final_response.txt", diet_plan)
    except Exception as exc:
        print(f"\nGroq LLM Connection Error: {exc}")


if __name__ == "__main__":
    run_nutritionist_pipeline()
