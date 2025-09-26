import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";
dotenv.config();

const callGemini = async (prompt) => {
  const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

  console.log("........");
  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
    });
    if (response) {
      return response.text;
    } else {
      throw new Error("something went  wrong while intracitng with the LLM");
    }
  } catch (e) {
    console.error(e.message);
    throw error;
  }
};

export default callGemini;
