import callGemini from "./queryAI.js";

const cityParser = async (userStory) => {
  // Build the prompt for Gemini
  const PROMPT = `
You are a helpful assistant that extracts city names from user queries about weather.
The input can be messy, contain typos, multiple cities, or mixed languages.
Return a JSON array of city names extracted from the input.
If no city found, return an empty array.

Examples:
Input: "What's the temperature in Delhi and Manali?"
Output: ["Delhi", "Manali"]

Input: "weather for NYC, Los Angeles, and San Fransisco"
Output: ["New York", "Los Angeles", "San Francisco"]

Input: "Tell me the weather in kaaasdfadsfsia"
Output: []

Now, extract city names from this input:
"${userStory}"
`;

  const response = await callGemini(PROMPT);
  let cleanResponse = response
    .replace(/```json/g, "") // to remove opening ```json
    .replace(/```/g, "") // to remove closing ```
    .trim(); // to remove extra spaces/newlines

  try {
    cleanResponse = JSON.parse(cleanResponse);
    return cleanResponse;
  } catch (e) {
    console.error(`[cityParser] failed\nReason: ${e.message}`);
    return [];
  }
};


export default cityParser;
