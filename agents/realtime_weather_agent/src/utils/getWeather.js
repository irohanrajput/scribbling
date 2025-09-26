import { fetchWeatherApi } from "openmeteo";
import getCoordinates from "./getCoordinates.js";

const getWeatherInfo = async (city, country = "") => {
  try {
    if (!city || typeof city !== "string" || city.trim() === "") {
      throw new Error("City name is required and must be a non-empty string");
    }

    const coordinates = await getCoordinates(city, country);
    if (!coordinates || !coordinates.lat || !coordinates.long) {
      throw new Error(
        `Could not get coordinates for city: ${city}, country: ${country}`
      );
    }

    const { lat, long } = coordinates;

    const params = {
      latitude: lat,
      longitude: long,
      daily: [
        "sunrise",
        "sunset",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
      ],
      current: "temperature_2m",
      forecast_days: 1,
    };

    const url = "https://api.open-meteo.com/v1/forecast";
    let responses;

    try {
      responses = await fetchWeatherApi(url, params);
    } catch (error) {
      throw new Error(`Failed to fetch weather data: ${error.message}`);
    }

    if (!responses || responses.length === 0) {
      throw new Error("No weather data received from API");
    }

    const response = responses[0];
    if (!response) {
      throw new Error("Invalid weather response received");
    }

    try {
      const utcOffsetSeconds = response.utcOffsetSeconds();



      const current = response.current();
      const daily = response.daily();

      if (!current || !daily) {
        throw new Error("Missing current or daily weather data");
      }

      const sunrise = daily.variables(0);
      const sunset = daily.variables(1);

      if (!sunrise || !sunset) {
        throw new Error("Missing sunrise/sunset data");
      }

      const weatherData = {
        current: {
          time: new Date((Number(current.time()) + utcOffsetSeconds) * 1000),
          temperature: current.variables(0).value(),
        },
        daily: {
          time: [
            ...Array(
              (Number(daily.timeEnd()) - Number(daily.time())) /
                daily.interval()
            ),
          ].map(
            (_, i) =>
              new Date(
                (Number(daily.time()) +
                  i * daily.interval() +
                  utcOffsetSeconds) *
                  1000
              )
          ),
          sunrise: [...Array(sunrise.valuesInt64Length())].map(
            (_, i) =>
              new Date(
                (Number(sunrise.valuesInt64(i)) + utcOffsetSeconds) * 1000
              )
          ),
          sunset: [...Array(sunset.valuesInt64Length())].map(
            (_, i) =>
              new Date(
                (Number(sunset.valuesInt64(i)) + utcOffsetSeconds) * 1000
              )
          ),
          temperature_max: daily.variables(2).valuesArray()[0],
          temperature_min: daily.variables(3).valuesArray()[0],
          precipitation_probability_max: daily.variables(4).valuesArray()[0],
        },
      };


      console.log(weatherData);

      return weatherData;
    } catch (error) {
      throw new Error(`Failed to process weather data: ${error.message}`);
    }
  } catch (error) {
    console.error("Error in getWeatherInfo:", error.message);
    throw error;
  }
};

export default getWeatherInfo;
