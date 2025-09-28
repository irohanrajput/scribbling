import getWeatherInfo from "./utils/getWeather.js";
import cityParser from "./utils/cityParser.js";
import responseBuilder from "./utils/responseBuilder.js";

const main = async (userStory) => {
  try {
    const cities = await cityParser(userStory);
    process.stdout.write(`✅ 🏙️  Cities Found:`);
    for (const city of cities) {
      process.stdout.write(` ${city} | `);
    }
    console.log("");

    let weatherData = [];

    for (const city of cities) {
      weatherData.push(await getWeatherInfo(city));
    }

    const response = await responseBuilder(weatherData);
    console.log("\n🌈 ✨ Weather Results: ", response);
    return response;
  } catch (error) {
    console.error(`Failed to get weather information\n${error}`);
  }
};

const story =
  "tvgw d;sck'adgdoi fnjlkm;snbf delhi adjfsy radfa  ghziabad adsjfadsf wna eather in lodon";

main(story);
