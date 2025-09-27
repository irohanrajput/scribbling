import queryAI from "./queryAI.js";

const responseBuilder = async (weatherData, userStory) => {
  const PROMPT = `
You are an expert weather assistant. You will be provided with an array of weather data for multiple cities and the original user story. Each weather item contains:
- city: name of the city
- current_time: current time in the city
- current_temperature: current temperature in °C
- sunrise: array of sunrise times
- sunset: array of sunset times
- temperature_max: maximum temperature for the day in °C
- temperature_min: minimum temperature for the day in °C
- precipitation_probability_max: maximum chance of precipitation in %

Your task is to return a JSON object with the following structure:

{
  "single_city": {
    "<city1>": {
      "city": "<city name>",
      "realtime_summary": "<brief summary using 'realtime data'>",
      "current_temperature": <value in °C>,
      "weather_description": "<sunny/rainy/hot/cold/...>",
      "sunrise": "<HH:MM AM/PM>",
      "sunset": "<HH:MM AM/PM>",
      "max_temperature": <value in °C>,
      "min_temperature": <value in °C>,
      "chance_of_rain": <value in %>,
      "clothes_recommendation": "<what to wear>",
      "activities_places_to_visit": "<suggested activities or places>"
    },
    "<city2>": { ... }
  },
  "comparison": {
    "warmest_city": "<city with highest current temperature>",
    "coolest_city": "<city with lowest current temperature>",
    "most_likely_rain": "<city with highest precipitation probability>",
    "best_for_outdoor_activities": "<city with best weather for outdoor activities>",
    "summary": "<brief comparison of all cities based on current weather>"
  },
  "userstory_context": {
    "user_mentioned_activities": ["<activities/interests mentioned in user story>"],
    "weather_activity_recommendations": "<how weather relates to mentioned activities/interests>",
    "contextual_advice": "<personalized advice based on user story context>"
  }
}

Instructions:
1. For each city, provide detailed weather information in the single_city section
2. In comparison, compare cities based on current weather conditions
3. In userstory_context, analyze the user story for any mentioned activities, interests, or context (like cricket, travel, work, etc.) and relate the weather to those activities
4. Make sure the JSON is valid and parseable
5. Format sunrise/sunset times as HH:MM AM/PM

User Story: "${userStory}"
Weather Data: ${JSON.stringify(weatherData)}
`;

  try {
    const response = await queryAI(PROMPT);
    return response;
  } catch (err) {
    throw new Error(`[responseBuilder] failed\nReason: ${err.message}`);
  }
};

export default responseBuilder;
