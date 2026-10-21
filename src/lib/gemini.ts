import { GoogleGenAI } from '@google/genai'
import type { AskHandlers } from './anthropic'

export async function askGoogleGenAI(
  prompt: string,
  apiKey: string,
  handlers: AskHandlers,
): Promise<{ text: string; tools: string[] }> {
  const ai = new GoogleGenAI({ apiKey })

  try {
    // Attempt standard generateContentStream with Google Search tool support
    const responseStream = await ai.models.generateContentStream({
      model: 'gemini-2.0-flash',
      contents: prompt,
      config: {
        systemInstruction:
          "You are J.A.R.V.I.S., Tony Stark's personal AI assistant. " +
          'Speak with British poise, dry wit, precision, and loyalty, addressing the user as Sir. ' +
          'Provide concise answers suitable for holographic HUD and vocal speech.',
        tools: [{ googleSearch: {} }],
      },
    })

    let fullText = ''
    for await (const chunk of responseStream) {
      const text = chunk.text
      if (text) {
        fullText += text
        handlers.onText(text)
      }
    }

    return { text: fullText, tools: ['google_search'] }
  } catch (err) {
    // If tools or specific options fail, fallback to direct content generation
    console.warn('[gemini] stream error, falling back to direct prompt', err)
    const res = await ai.models.generateContent({
      model: 'gemini-2.0-flash',
      contents: prompt,
    })
    const out = res.text || ''
    if (out) handlers.onText(out)
    return { text: out, tools: [] }
  }
}
