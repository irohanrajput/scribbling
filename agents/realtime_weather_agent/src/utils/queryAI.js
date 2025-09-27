import { GoogleGenAI } from "@google/genai";
import * as dotenv from "dotenv";
dotenv.config();

const queryAI = async (prompt) => {
  const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
    });
    if (response) {
      return response.text;
    } else {
      throw new Error("something went wrong while intracitng with the LLM");
    }
  } catch (e) {
    throw new Error(`[queryAi] failed\nReason: ${e.message}`);
  }
};


export default queryAI;
