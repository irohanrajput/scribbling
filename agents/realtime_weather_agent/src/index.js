import getWeatherInfo from "./utils/getWeather.js";
import callGemini from "./utils/queryAI.js";

const main = async (city) => {
  try {
    const weatherData = await getWeatherInfo(city);
    console.log(weatherData);

    const PROMPT = `Analyze the following weather data for ${city}:
      Current time: ${weatherData.current_time}
      Current temperature: ${weatherData.current_temperature}°C
      Sunrise: ${weatherData.sunrise}
      Sunset: ${weatherData.sunset}
      Maximum temperature: ${weatherData.temperature_max}°C
      Minimum temperature: ${weatherData.temperature_min}°C
      Precipitation probability: ${weatherData.precipitation_probability_max}%
      
      Please provide a brief weather summary and recommendations for activities based on these conditions.`;

    if (weatherData) {
      const response = await callGemini(PROMPT);
      console.log(response);
    } else {
      throw Error("weather api is cool, can't call gemini but. ");
    }
  } catch (error) {
    console.error("Failed to get weather information:", error.message);
    process.exit(1);
  }
};

main("london");
