import getWeatherInfo from "./utils/getWeather.js";
import cityParser from "./utils/cityParser.js";
import responseBuilder from "./utils/responseBuilder.js";

const main = async (userStory) => {
  try {
    const cities = await cityParser(userStory);
    for (const city of cities){
      console.log(city)
    }

    let weatherData = [];

    for (const city of cities) {
      weatherData.push(await getWeatherInfo(city));
    }

    const response = await responseBuilder(weatherData)
    console.log("\n🌈 Weather Results:", response)
    return response;

  } catch (error) {
    console.error(`Failed to get weather information\n${error}`);
    throw error;
  }
};


const story = "what is wrong iwht thie delhi, adsf sadf singapur and also kasia gazibad"


main(story)






