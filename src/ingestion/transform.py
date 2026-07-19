"""Flattens raw USDA food records into indexable FoodDocuments."""

from typing import Any

from ingestion.models import CoreNutrients, FoodDocument, NutrientDetail

# USDA nutrient numbers (stable across API versions) for the curated core set.
# Foundation Foods report energy under one of several numbers depending on how
# it was derived (lab-measured "208" is rare; most records only carry the
# Atwater-calculated "957"/"958"), so calories use a fallback chain instead of
# a single number.
CALORIE_NUTRIENT_NUMBERS = ("208", "957", "958")
CORE_NUTRIENT_FIELDS = {
    "203": "protein_g",
    "204": "fat_g",
    "205": "carbohydrate_g",
    "291": "fiber_g",
    "269": "sugars_g",
    "301": "calcium_mg",
    "303": "iron_mg",
    "306": "potassium_mg",
    "307": "sodium_mg",
    "401": "vitamin_c_mg",
    "328": "vitamin_d_ug",
}
REQUIRED_CORE_FIELDS = ("calories_kcal", "protein_g", "fat_g", "carbohydrate_g")


def _extract_nutrients(
    raw_nutrients: list[dict[str, Any]],
) -> tuple[CoreNutrients, list[NutrientDetail]]:
    core_values: dict[str, float] = {}
    calories_by_number: dict[str, float] = {}
    all_nutrients: list[NutrientDetail] = []

    for entry in raw_nutrients:
        amount = entry.get("amount")
        name = entry.get("name")
        unit = entry.get("unitName")
        number = entry.get("number")
        if amount is None or name is None or unit is None or not isinstance(number, str):
            continue

        all_nutrients.append(
            NutrientDetail(nutrient_number=number, name=name, unit=unit, value=amount)
        )

        if number in CALORIE_NUTRIENT_NUMBERS:
            calories_by_number[number] = amount

        field = CORE_NUTRIENT_FIELDS.get(number)
        if field is not None:
            core_values[field] = amount

    for number in CALORIE_NUTRIENT_NUMBERS:
        if number in calories_by_number:
            core_values["calories_kcal"] = calories_by_number[number]
            break

    for field in REQUIRED_CORE_FIELDS:
        core_values.setdefault(field, 0.0)

    return CoreNutrients(**core_values), all_nutrients


def _build_search_text(food_name: str, food_category: str | None, core: CoreNutrients) -> str:
    category_part = f" Category: {food_category}." if food_category else ""
    return (
        f"{food_name}.{category_part} Typical nutrition per 100g: "
        f"{core.calories_kcal:g} kcal, {core.protein_g:g}g protein, "
        f"{core.fat_g:g}g fat, {core.carbohydrate_g:g}g carbohydrate."
    )


def _extract_food_category(raw: dict[str, Any]) -> str | None:
    category = raw.get("foodCategory")
    if isinstance(category, dict):
        return category.get("description")
    return category


def transform_food(raw: dict[str, Any]) -> FoodDocument:
    """Flatten one raw USDA food record into a FoodDocument."""
    fdc_id = raw["fdcId"]
    food_name = raw["description"]
    food_category = _extract_food_category(raw)
    data_type = raw["dataType"]

    core, all_nutrients = _extract_nutrients(raw.get("foodNutrients", []))
    search_text = _build_search_text(food_name, food_category, core)

    return FoodDocument(
        fdc_id=fdc_id,
        food_name=food_name,
        food_category=food_category,
        data_type=data_type,
        search_text=search_text,
        nutrients=core,
        all_nutrients=all_nutrients,
    )
