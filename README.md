# AgenticNutriRAG

## Dataset

Nutrition data comes from the [USDA FoodData Central](https://fdc.nal.usda.gov/)
API. Ingestion is scoped to the **Foundation Foods** data type only (394
records as of this API snapshot) rather than the full FoodData Central corpus
(300k+ records across Foundation, SR Legacy, Survey (FNDDS), and Branded
types). This bounds embedding cost/time and keeps the dataset's nutrient data
high-quality (Foundation Foods are lab-analyzed, not self-reported or
aggregated).

Run the ingestion pipeline with:

```bash
uv run python -m ingestion.pipeline
```

It fetches every Foundation Foods record via the USDA API (paginated),
flattens each into a description string plus a structured nutrient object,
embeds the description with the OpenAI embeddings API, and indexes it into
Elasticsearch (index `usda_foods`) using the FDC ID as a stable document ID
so re-running the ingestion is idempotent. Verified end-to-end against a live
Elasticsearch 8.15.0 instance: 394/394 Foundation Foods indexed, re-running
produces the same document count (no duplicates).

**Known data gap**: USDA doesn't report an energy/calorie value for every
Foundation Foods record (about 18% in the current snapshot lack one under any
of the numbers checked - `208`, `957`, `958`). Those documents get
`calories_kcal: 0.0` rather than a fabricated estimate.
