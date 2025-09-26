import getWeatherInfo from "./utils/getWeather.js";

const main = async () => {
  try {
    const defaultCity = "london";

    const weatherData = await getWeatherInfo(defaultCity);

    if (weatherData) {
      console.log("Weather data retrieved successfully!");
    }
  } catch (error) {
    console.error("Failed to get weather information:", error.message);
    process.exit(1);
  }
};

main();