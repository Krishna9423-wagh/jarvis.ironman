/**
 * J.A.R.V.I.S. Core Intelligence & Autonomous Reasoning Engine
 *
 * Provides intelligent, natural in-character Iron Man AI responses.
 * Completely eliminates "Not logged in" errors by operating autonomously,
 * fetching real-time Wikipedia knowledge for factual topics, and supporting
 * optional API keys (Gemini, OpenAI, Anthropic).
 */

import type { AskHandlers } from './anthropic'
import { askGoogleGenAI } from './gemini'

export type JarvisAiResponse = {
  text: string
  tools: string[]
}

const SYSTEM_STATUS = {
  reactorOutput: '8.4 GW',
  energyLevel: '98%',
  armorIntegrity: '100%',
  suitStatus: 'ONLINE (100%)',
  flightStatus: 'FLIGHT READY',
  targetLock: 'N/A — SCANNING',
  altitude: '34,000 ft',
  speed: 'Mach 1.2',
  coreTemp: '32°C',
  energyStability: 'OPTIMAL (99.8%)',
  defenseGrid: 'ACTIVE',
}

/**
 * Fetch live factual knowledge from Wikipedia summary API.
 */
async function fetchWikiSummary(term: string): Promise<string | null> {
  try {
    const clean = term
      .replace(/^(who is|what is|tell me about|explain|describe|search for|lookup)\s+/i, '')
      .trim()
    if (!clean || clean.length < 2) return null

    const searchUrl = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(
      clean,
    )}&utf8=&format=json&origin=*`
    const sres = await fetch(searchUrl, { signal: AbortSignal.timeout(3500) }).then((r) =>
      r.json(),
    )
    const title = sres.query?.search?.[0]?.title
    if (!title) return null

    const pageUrl = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(
      title.replace(/ /g, '_'),
    )}`
    const pres = await fetch(pageUrl, { signal: AbortSignal.timeout(3500) }).then((r) =>
      r.json(),
    )

    if (pres.extract) {
      // Return first 2 sentences for concise vocal delivery
      const sentences = pres.extract.match(/[^.!?]+[.!?]+/g) || [pres.extract]
      return sentences.slice(0, 2).join(' ')
    }
  } catch {
    // network timeout or unavailable
  }
  return null
}

/**
 * Intelligent in-character Stark Industries responses.
 */
async function getSmartResponse(rawPrompt: string): Promise<string> {
  const q = rawPrompt.toLowerCase().trim()

  // 1. Handling login / authentication questions
  if (
    q.includes('login') ||
    q.includes('log in') ||
    q.includes('logged in') ||
    q.includes('auth') ||
    q.includes('account')
  ) {
    return `To connect Claude Code to the bridge, simply run "npm install -g @anthropic-ai/claude-code" in your terminal and type "claude" once to log in. In the meantime, I am running autonomously on my internal neural engine with full vocal and holographic telemetry, Sir.`
  }

  // 2. Status & Diagnostics
  if (
    q.includes('status') ||
    q.includes('system') ||
    q.includes('diagnostic') ||
    q.includes('health') ||
    q.includes('check')
  ) {
    return `All primary systems are functioning within optimal parameters, Sir. Arc Reactor output is steady at ${SYSTEM_STATUS.reactorOutput}, energy reserves are at ${SYSTEM_STATUS.energyLevel}, and suit armor integrity is at ${SYSTEM_STATUS.armorIntegrity}. All flight controls are armed and ready.`
  }

  // 3. Reactor & Power
  if (
    q.includes('reactor') ||
    q.includes('power') ||
    q.includes('output') ||
    q.includes('energy') ||
    q.includes('core')
  ) {
    return `The Arc Reactor core is generating ${SYSTEM_STATUS.reactorOutput} with an energy stability quotient of ${SYSTEM_STATUS.energyStability}. Heat dissipation remains nominal at ${SYSTEM_STATUS.coreTemp}.`
  }

  // 4. Identity & Purpose
  if (q.includes('who are you') || q.includes('your name') || q.includes('introduce')) {
    return `I am J.A.R.V.I.S. — Just A Rather Very Intelligent System. I oversee Stark Industries defense subroutines, holographic telemetry, and tactical suit environmental controls. How may I assist you today, Sir?`
  }

  // 5. Suit & Armor
  if (
    q.includes('armor') ||
    q.includes('suit') ||
    q.includes('mark') ||
    q.includes('integrity') ||
    q.includes('plating')
  ) {
    return `Suit status is currently ${SYSTEM_STATUS.suitStatus}. Multi-layer gold-titanium composite plating is at ${SYSTEM_STATUS.armorIntegrity}. Repulsor arrays and micro-thrusters are calibrated and flight-ready.`
  }

  // 6. Flight & Navigation
  if (
    q.includes('flight') ||
    q.includes('fly') ||
    q.includes('speed') ||
    q.includes('altitude') ||
    q.includes('velocity')
  ) {
    return `Flight telemetry calibrated, Sir. Current cruising envelope is set to ${SYSTEM_STATUS.altitude} with structural integrity rated to ${SYSTEM_STATUS.speed}. Aerodynamic control surfaces are fully responsive.`
  }

  // 7. Radar & Targeting
  if (
    q.includes('target') ||
    q.includes('lock') ||
    q.includes('scan') ||
    q.includes('radar') ||
    q.includes('perimeter')
  ) {
    return `Targeting reticle sweeping a 360-degree perimeter. Optical telemetry confirms zero hostile signatures within radar envelope. All tracking channels remain on standby.`
  }

  // 8. Time & Date
  if (q.includes('time') || q.includes('clock') || q.includes('date') || q.includes('day')) {
    const now = new Date()
    return `The local time is ${now.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })}, on ${now.toLocaleDateString([], {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })}, Sir.`
  }

  // 9. Weather & Climate
  if (q.includes('weather') || q.includes('temperature') || q.includes('forecast')) {
    return `Atmospheric sensors indicate clear conditions across your sector with an ambient temperature of 24 degrees Celsius, barometric pressure at 1013 millibars, and zero radar-detected precipitation.`
  }

  // 10. Greetings & Courtesy
  if (
    q.startsWith('hello') ||
    q.startsWith('hey') ||
    q.startsWith('hi') ||
    q.includes('good morning') ||
    q.includes('good afternoon') ||
    q.includes('good evening')
  ) {
    return `Good day, Sir. Holographic telemetry is online, audio sensors are focused, and all Mark series protocols are active. What would you like to accomplish?`
  }

  if (q.includes('thank') || q.includes('thanks') || q.includes('good job')) {
    return `Always a pleasure to assist, Sir. Standing by for your next instruction.`
  }

  if (q.includes('who created you') || q.includes('who made you') || q.includes('tony stark')) {
    return `I was engineered by Tony Stark as the central operating intelligence for Stark Industries and the Iron Man operational platforms.`
  }

  if (q.includes('joke') || q.includes('funny')) {
    return `I would tell you a joke about UDP, Sir, but I am not certain you would get it. Alternatively, I could recalibrate the Mark suit's repulsors to provide a more kinetic form of amusement.`
  }

  // 11. Mathematical Calculations (e.g. "25 * 40", "150 / 3")
  const mathMatch = q.match(/(\d+[\d\s\+\-\*\/\^\.\(\)]+\d+)/)
  if (mathMatch) {
    try {
      const sanitized = mathMatch[1].replace(/[^0-9\+\-\*\/\.\(\)]/g, '')
      const res = Function(`'use strict'; return (${sanitized})`)()
      if (typeof res === 'number' && !isNaN(res)) {
        return `Computing telemetry: ${mathMatch[1]} equals ${res}, Sir.`
      }
    } catch {
      // ignore
    }
  }

  // 12. Real-time Knowledge Lookup for entities / factual queries
  const wikiResult = await fetchWikiSummary(rawPrompt)
  if (wikiResult) {
    return `According to my archives, Sir: ${wikiResult}`
  }

  // 13. Conversational Fallback
  return `Understood, Sir. Telemetry sensors are tracking your instruction. All Mark VII subsystems, holographic displays, and defense arrays are responsive and operational.`
}

/**
 * Ask JARVIS with streaming text deltas for speech synthesis & lip sync.
 */
export async function askJarvisAi(
  prompt: string,
  handlers: AskHandlers,
): Promise<JarvisAiResponse> {
  // Check if user has provided an external API key
  const geminiKey =
    localStorage.getItem('jarvis_gemini_key') || import.meta.env.VITE_GEMINI_API_KEY
  const anthropicKey =
    localStorage.getItem('jarvis_anthropic_key') || import.meta.env.VITE_ANTHROPIC_API_KEY
  const openaiKey =
    localStorage.getItem('jarvis_openai_key') || import.meta.env.VITE_OPENAI_API_KEY

  if (geminiKey) {
    try {
      return await askGoogleGenAI(prompt, geminiKey, handlers)
    } catch (e) {
      console.warn('[jarvis-ai] GoogleGenAI error, falling back to direct stream', e)
      try {
        return await askGeminiDirect(prompt, geminiKey, handlers)
      } catch (err2) {
        console.warn('[jarvis-ai] Gemini direct error, using Stark heuristic engine', err2)
      }
    }
  }

  if (anthropicKey) {
    try {
      return await askAnthropicDirect(prompt, anthropicKey, handlers)
    } catch (e) {
      console.warn('[jarvis-ai] Anthropic direct error, using Stark heuristic engine', e)
    }
  }

  if (openaiKey) {
    try {
      return await askOpenAiDirect(prompt, openaiKey, handlers)
    } catch (e) {
      console.warn('[jarvis-ai] OpenAI direct error, using Stark heuristic engine', e)
    }
  }

  // Execute smart response
  const answer = await getSmartResponse(prompt)
  const words = answer.split(' ')
  let fullText = ''

  for (let i = 0; i < words.length; i++) {
    const chunk = (i === 0 ? '' : ' ') + words[i]
    fullText += chunk
    handlers.onText(chunk)
    // Realistic cognitive streaming cadence
    await new Promise((r) => setTimeout(r, 24))
  }

  return {
    text: fullText,
    tools: ['telemetry_readout'],
  }
}

async function askGeminiDirect(
  prompt: string,
  apiKey: string,
  handlers: AskHandlers,
): Promise<JarvisAiResponse> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key=${apiKey}`
  const systemInstruction = `You are J.A.R.V.I.S., the AI assistant from Iron Man. Speak to the user as "Sir" with British wit, absolute competence, brevity, and loyalty. Keep responses concise (1-3 sentences) suitable for vocal speech.`

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      systemInstruction: { parts: [{ text: systemInstruction }] },
      generationConfig: { maxOutputTokens: 300, temperature: 0.7 },
    }),
  })

  if (!res.ok) throw new Error(`Gemini API error: ${res.statusText}`)

  const reader = res.body?.getReader()
  const decoder = new TextDecoder()
  let fullText = ''

  if (reader) {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            const textDelta = data.candidates?.[0]?.content?.parts?.[0]?.text
            if (textDelta) {
              fullText += textDelta
              handlers.onText(textDelta)
            }
          } catch {
            // ignore
          }
        }
      }
    }
  }

  return { text: fullText, tools: [] }
}

async function askAnthropicDirect(
  prompt: string,
  apiKey: string,
  handlers: AskHandlers,
): Promise<JarvisAiResponse> {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'dangerously-allow-browser': 'true',
    },
    body: JSON.stringify({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 300,
      system:
        "You are J.A.R.V.I.S., Tony Stark's AI. Concise, sharp, British cadence. Refer to user as Sir.",
      messages: [{ role: 'user', content: prompt }],
      stream: true,
    }),
  })

  if (!res.ok) throw new Error(`Anthropic API error: ${res.statusText}`)

  const reader = res.body?.getReader()
  const decoder = new TextDecoder()
  let fullText = ''

  if (reader) {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'content_block_delta' && data.delta?.text) {
              fullText += data.delta.text
              handlers.onText(data.delta.text)
            }
          } catch {
            // ignore
          }
        }
      }
    }
  }

  return { text: fullText, tools: [] }
}

async function askOpenAiDirect(
  prompt: string,
  apiKey: string,
  handlers: AskHandlers,
): Promise<JarvisAiResponse> {
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      max_tokens: 300,
      stream: true,
      messages: [
        {
          role: 'system',
          content:
            'You are J.A.R.V.I.S. from Iron Man. Concise, sharp, sophisticated, addressing user as Sir.',
        },
        { role: 'user', content: prompt },
      ],
    }),
  })

  if (!res.ok) throw new Error(`OpenAI API error: ${res.statusText}`)

  const reader = res.body?.getReader()
  const decoder = new TextDecoder()
  let fullText = ''

  if (reader) {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          try {
            const data = JSON.parse(line.slice(6))
            const delta = data.choices?.[0]?.delta?.content
            if (delta) {
              fullText += delta
              handlers.onText(delta)
            }
          } catch {
            // ignore
          }
        }
      }
    }
  }

  return { text: fullText, tools: [] }
}
