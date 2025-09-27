# Weather Query Flow

User sends query → "what is the temperature in Manali and Delhi?"

## Processing Steps

1. **Parser**
    - Extracts cities → ["Manali", "Delhi"] 
    - _Note: currenly looking for worksarounds beyond RAG for user stories, but for now, i'm gonna just use regex._

2. **Orchestrator**
    - For each city:
      - Call `getWeatherInfo(city)` a simple loop maybe
      - Store success/failure in structured object

3. **Aggregator**
    - Convert `{ city: weatherData }` → readable data for Gemini

4. **Gemini**
    - Generate polished summary from aggregated data

5. **Return**
    - Final answer to user 