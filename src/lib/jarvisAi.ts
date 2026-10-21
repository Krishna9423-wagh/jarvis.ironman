/**
 * J.A.R.V.I.S. Core Intelligence & Fallback Engine
 *
 * Ensures that JARVIS NEVER stays silent or fails to answer, whether running
 * locally, on Vercel, with or without Claude Code CLI login, and with or without
 * external API keys.
 */

import type { AskHandlers } from './anthropic'

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
  targetLock: 'N/A — STANDBY',
  altitude: '34,000 ft',
  speed: 'Mach 1.2',
  coreTemp: '32°C',
  energyStability: 'OPTIMAL (99.8%)',
  defenseGrid: 'ACTIVE',
}

/**
 * Intelligent in-character Stark Industries responses when offline or unauthenticated.
 */
function getOfflineResponse(rawPrompt: string): string {
  const q = rawPrompt.toLowerCase().trim()

  if (q.includes('status') || q.includes('system') || q.includes('diagnostic') || q.includes('check')) {
    return `All primary systems are functioning within optimal parameters, Sir. Arc Reactor output is stable at ${SYSTEM_STATUS.reactorOutput}, energy reserves are at ${SYSTEM_STATUS.energyLevel}, and suit armor integrity is at ${SYSTEM_STATUS.armorIntegrity}. Flight controls are armed and ready.`
  }

  if (q.includes('reactor') || q.includes('power') || q.includes('output') || q.includes('energy')) {
    return `The palladium-vibranium core is generating a steady ${SYSTEM_STATUS.reactorOutput} with an energy stability quotient of ${SYSTEM_STATUS.energyStability}. Heat dissipation remains nominal at ${SYSTEM_STATUS.coreTemp}.`
  }

  if (q.includes('who are you') || q.includes('your name') || q.includes('introduce')) {
    return `I am J.A.R.V.I.S. — Just A Rather Very Intelligent System. I manage Stark Industries tactical telemetry, holographic environmental controls, and all Iron Man defense subroutines. How may I be of assistance today, Sir?`
  }

  if (q.includes('armor') || q.includes('suit') || q.includes('mark') || q.includes('integrity')) {
    return `Suit status is currently ${SYSTEM_STATUS.suitStatus}. Multi-layer gold-titanium composite plating is at ${SYSTEM_STATUS.armorIntegrity}. Repulsor arrays and targeting micro-thrusters are calibrated and flight-ready.`
  }

  if (q.includes('flight') || q.includes('fly') || q.includes('speed') || q.includes('altitude')) {
    return `Flight telemetry calibrated, Sir. Cruising altitude envelope set to ${SYSTEM_STATUS.altitude} with structural integrity rated to ${SYSTEM_STATUS.speed}. Aerodynamic stabilizers are fully responsive.`
  }

  if (q.includes('weather') || q.includes('temperature') || q.includes('forecast')) {
    const temp = 24
    return `Atmospheric sensors indicate clear skies in your sector with ambient temperature around ${temp} degrees Celsius, barometric pressure nominal at 1013 millibars, and zero radar-detected storm cells.`
  }

  if (q.includes('time') || q.includes('clock') || q.includes('date')) {
    const now = new Date()
    return `The current local time is ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}, on ${now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}, Sir.`
  }

  if (q.includes('target') || q.includes('lock') || q.includes('scan') || q.includes('radar')) {
    return `Targeting reticle sweeping a 360-degree perimeter. Optical telemetry confirms zero hostile signatures within radar envelope. All tracking channels remain on standby.`
  }

  if (q.includes('hello') || q.includes('hey') || q.includes('hi') || q.includes('good morning') || q.includes('good evening')) {
    return `Good day, Sir. Holographic telemetry is online, audio sensors are focused, and all Mark series protocols are active. What would you like to accomplish?`
  }

  if (q.includes('thank') || q.includes('thanks')) {
    return `Always a pleasure to assist, Sir. Standing by for your next instruction.`
  }

  if (q.includes('who created you') || q.includes('who made you') || q.includes('stark') || q.includes('tony')) {
    return `I was engineered by Tony Stark as the central operating intelligence for Stark Industries and the Iron Man operational platforms.`
  }

  if (q.includes('joke') || q.includes('funny')) {
    return `I would tell you a joke about UDP, Sir, but I am not certain you would get it. Alternatively, I could recalibrate the Mark suit's thrusters to provide a more kinetic form of amusement.`
  }

  // Math calculation check (e.g. "what is 25 * 40")
  const mathMatch = q.match(/(\d+[\d\s\+\-\*\/\^\.\(\)]+\d+)/)
  if (mathMatch) {
    try {
      const sanitized = mathMatch[1].replace(/[^0-9\+\-\*\/\.\(\)]/g, '')
      // Safe math evaluation
      const res = Function(`'use strict'; return (${sanitized})`)()
      if (typeof res === 'number' && !isNaN(res)) {
        return `Computing telemetry: ${mathMatch[1]} equals ${res}, Sir.`
      }
    } catch {
      // fallback
    }
  }

  // General fallback response
  return `Analyzing query: "${rawPrompt}". All primary channels are operational. To execute complex multi-step tasks across real web browsers, shell commands, and file creation, please ensure the local bridge is authenticated via Claude Code CLI. In the meantime, all tactical diagnostics, telemetry readouts, and holographic controls are fully active, Sir.`
}

/**
 * Ask JARVIS with streaming tokens so speech and HUD decode trigger in real-time.
 */
export async function askJarvisAi(
  prompt: string,
  handlers: AskHandlers,
): Promise<JarvisAiResponse> {
  // Check if user has configured an API key in localStorage or environment
  const geminiKey = localStorage.getItem('jarvis_gemini_key') || import.meta.env.VITE_GEMINI_API_KEY
  const anthropicKey = localStorage.getItem('jarvis_anthropic_key') || import.meta.env.VITE_ANTHROPIC_API_KEY
  const openaiKey = localStorage.getItem('jarvis_openai_key') || import.meta.env.VITE_OPENAI_API_KEY

  if (geminiKey) {
    try {
      return await askGeminiDirect(prompt, geminiKey, handlers)
    } catch (e) {
      console.warn('[jarvis-ai] Gemini direct error, falling back to neural heuristics', e)
    }
  }

  if (anthropicKey) {
    try {
      return await askAnthropicDirect(prompt, anthropicKey, handlers)
    } catch (e) {
      console.warn('[jarvis-ai] Anthropic direct error, falling back to neural heuristics', e)
    }
  }

  if (openaiKey) {
    try {
      return await askOpenAiDirect(prompt, openaiKey, handlers)
    } catch (e) {
      console.warn('[jarvis-ai] OpenAI direct error, falling back to neural heuristics', e)
    }
  }

  // Default: Fast, local, in-character Stark Industries voice stream
  const answer = getOfflineResponse(prompt)
  const words = answer.split(' ')
  let fullText = ''

  for (let i = 0; i < words.length; i++) {
    const chunk = (i === 0 ? '' : ' ') + words[i]
    fullText += chunk
    handlers.onText(chunk)
    // Realistic cognitive streaming delay for lip sync & natural speech cadence
    await new Promise((r) => setTimeout(r, 22))
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
            // ignore partial JSON
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
      system: 'You are J.A.R.V.I.S., Tony Stark\'s AI. Concise, sharp, British cadence. Refer to user as Sir.',
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
          content: 'You are J.A.R.V.I.S. from Iron Man. Concise, sharp, sophisticated, addressing user as Sir.',
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
