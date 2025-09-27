import queryAI from "./queryAI.js";

const responseBuilder = async (weatherData) => {
  const PROMPT = `Based on the following real-time weather data, provide a brief 1-2 sentence comparison summary of the cities: ${JSON.stringify(weatherData, null, 2)}


Compare temperatures, weather conditions, and mention which city is warmest/coolest, rain probability, best to visit and also activites to perform in that particular locality Keep it conversational concise but mention realtime temperature for each city.`;


  try {
    console.log("🔨 building reponse...")
    const response = await queryAI(PROMPT);
    return response;
  } catch (err) {
    throw new Error(`[responseBuilder] failed\nReason: ${err.message}`);
  }
};

export default responseBuilder;
