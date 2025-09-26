import * as dotenv from "dotenv";
dotenv.config();

const ninjaAPIkey = process.env.ninjaAPIkey;

const getCoordinates = async (city, country = "") => {
  try {
    if (!city || typeof city !== 'string' || city.trim() === '') {
      throw new Error("City name is required and must be a non-empty string");
    }

    if (!ninjaAPIkey) {
      throw new Error("ninjaAPIkey not found in environment variables. Please check your .env file");
    }

    const headers = new Headers();
    headers.append("X-Api-Key", ninjaAPIkey);

    const requestOptions = {
      method: "GET",
      headers: headers,
      redirect: "follow",
    };

    const url = `https://api.api-ninjas.com/v1/geocoding?city=${encodeURIComponent(city)}&country=${encodeURIComponent(country)}`;

    const response = await fetch(url, requestOptions);

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}: ${response.statusText}`);
    }

    const geoCodes = await response.json();

    if (!geoCodes || !Array.isArray(geoCodes) || geoCodes.length === 0) {
      throw new Error(`No coordinates found for city: ${city}${country ? `, country: ${country}` : ''}`);
    }

    const { latitude, longitude } = geoCodes[0];

    if (typeof latitude !== 'number' || typeof longitude !== 'number') {
      throw new Error("Invalid coordinates received from API");
    }

    return { lat: latitude, long: longitude };
  } catch (error) {
    console.error("Error in getCoordinates:", error.message);
    throw error;
  }
};

export default getCoordinates;
