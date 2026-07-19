"""Data models shared across the ingestion pipeline."""

from pydantic import BaseModel


class CoreNutrients(BaseModel):
    """Curated macro/micronutrient values used for structured lookups, per 100g."""

    calories_kcal: float
    protein_g: float
    fat_g: float
    carbohydrate_g: float
    fiber_g: float | None = None
    sugars_g: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None
    potassium_mg: float | None = None
    sodium_mg: float | None = None
    vitamin_c_mg: float | None = None
    vitamin_d_ug: float | None = None


class NutrientDetail(BaseModel):
    """A single nutrient measurement as reported by USDA, for full detail lookups."""

    nutrient_number: str
    name: str
    unit: str
    value: float


class FoodDocument(BaseModel):
    """The flattened representation of one USDA food, ready to embed and index."""

    fdc_id: int
    food_name: str
    food_category: str | None
    data_type: str
    search_text: str
    nutrients: CoreNutrients
    all_nutrients: list[NutrientDetail]
