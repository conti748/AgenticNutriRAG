from ingestion.transform import transform_food


def _nutrient(number: str, name: str, unit: str, amount: float) -> dict:
    return {"number": number, "name": name, "unitName": unit, "amount": amount}


RAW_FOOD = {
    "fdcId": 747447,
    "description": "Hummus, commercial",
    "dataType": "Foundation",
    "foodCategory": "Legumes and Legume Products",
    "foodNutrients": [
        # Foundation Foods typically report energy under 957/958 (Atwater
        # factors), not 208 - see ingestion/transform.py's CALORIE_NUTRIENT_NUMBERS.
        _nutrient("957", "Energy (Atwater General Factors)", "KCAL", 166.0),
        _nutrient("203", "Protein", "G", 7.14),
        _nutrient("204", "Total lipid (fat)", "G", 9.6),
        _nutrient("205", "Carbohydrate, by difference", "G", 14.3),
        _nutrient("301", "Calcium, Ca", "MG", 38.0),
        _nutrient("999", "Some Untracked Nutrient", "MG", 1.0),
    ],
}


def test_transform_food_extracts_core_fields() -> None:
    food = transform_food(RAW_FOOD)

    assert food.fdc_id == 747447
    assert food.food_name == "Hummus, commercial"
    assert food.food_category == "Legumes and Legume Products"
    assert food.data_type == "Foundation"
    assert food.nutrients.calories_kcal == 166.0
    assert food.nutrients.protein_g == 7.14
    assert food.nutrients.fat_g == 9.6
    assert food.nutrients.carbohydrate_g == 14.3
    assert food.nutrients.calcium_mg == 38.0


def test_transform_food_prefers_208_over_atwater_energy_numbers() -> None:
    raw = {
        **RAW_FOOD,
        "foodNutrients": [
            *RAW_FOOD["foodNutrients"],
            _nutrient("208", "Energy", "KCAL", 170.0),
        ],
    }

    food = transform_food(raw)

    assert food.nutrients.calories_kcal == 170.0


def test_transform_food_defaults_missing_required_core_fields() -> None:
    raw = {**RAW_FOOD, "foodNutrients": []}

    food = transform_food(raw)

    assert food.nutrients.calories_kcal == 0.0
    assert food.nutrients.protein_g == 0.0
    assert food.nutrients.fat_g == 0.0
    assert food.nutrients.carbohydrate_g == 0.0
    assert food.nutrients.calcium_mg is None


def test_transform_food_keeps_full_nutrient_detail() -> None:
    food = transform_food(RAW_FOOD)

    assert len(food.all_nutrients) == len(RAW_FOOD["foodNutrients"])
    names = {n.name for n in food.all_nutrients}
    assert "Some Untracked Nutrient" in names


def test_transform_food_builds_nonempty_search_text() -> None:
    food = transform_food(RAW_FOOD)

    assert food.food_name in food.search_text
    assert "kcal" in food.search_text


def test_transform_food_handles_object_food_category() -> None:
    raw = {**RAW_FOOD, "foodCategory": {"id": 1, "description": "Legumes"}}

    food = transform_food(raw)

    assert food.food_category == "Legumes"
