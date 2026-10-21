import React, { useState, useEffect } from 'react'
import { useStore } from '../store'

interface IronManHudProps {
  onAsk: (question: string) => void
  isListening: boolean
  onToggleMic: () => void
}

export const IronManHud: React.FC<IronManHudProps> = ({ onAsk, isListening, onToggleMic }) => {
  const phase = useStore((s) => s.phase)
  const turns = useStore((s) => s.turns)
  const [inputText, setInputText] = useState('')
  const [radarAngle, setRadarAngle] = useState(0)
  const [waveOffset, setWaveOffset] = useState(0)

  // Animated radar rotation and audio wave oscillation
  useEffect(() => {
    let animId: number
    const update = () => {
      setRadarAngle((a) => (a + 1.8) % 360)
      setWaveOffset((w) => (w + 0.12) % (Math.PI * 2))
      animId = requestAnimationFrame(update)
    }
    animId = requestAnimationFrame(update)
    return () => cancelAnimationFrame(animId)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim()) return
    onAsk(inputText.trim())
    setInputText('')
  }

  // Get the latest turn for live display
  const latestTurn = turns.length > 0 ? turns[turns.length - 1] : null
  const latestJarvis = [...turns].reverse().find((t) => t.role === 'jarvis')

  return (
    <div className="ironman-hud-overlay">
      {/* Cinematic Stark Workshop Backdrop Ambience */}
      <div className="ironman-backdrop-glow" />

      {/* Main Outer Amber Framing HUD Bracket */}
      <div className="hud-frame-container">
        {/* Top Header */}
        <div className="hud-top-bracket">
          <div className="bracket-notch-left" />
          <div className="hud-header-center">
            <h1 className="hud-main-title">J.A.R.V.I.S.</h1>
            <div className="hud-sub-telemetry">
              <span>MARK VII INTERFACE</span>
              <span className="dot-sep">•</span>
              <span className="phase-indicator">{phase.toUpperCase()}</span>
              <span className="dot-sep">•</span>
              <span>TACTICAL HUD</span>
            </div>
          </div>
          <div className="bracket-notch-right" />
        </div>

        {/* Left Telemetry Column */}
        <div className="hud-col hud-col-left">
          {/* Suit Diagnostics Status Block */}
          <div className="hud-card diagnostic-card">
            <div className="hud-card-header">
              <span className="hud-tag">STATUS REPORT</span>
              <span className="hud-live-tag">LIVE</span>
            </div>
            <div className="diag-line green-text">
              <span className="diag-label">SUIT STATUS:</span>
              <span className="diag-value">ONLINE (100%)</span>
            </div>
            <div className="diag-line cyan-text">
              <span className="diag-label">SYSTEM DIAGNOSTICS:</span>
              <span className="diag-value">OPTIMAL</span>
            </div>
            <div className="diag-line amber-text">
              <span className="diag-label">REACTOR OUTPUT:</span>
              <span className="diag-value">8.4 GW</span>
            </div>
            <div className="diag-line cyan-text">
              <span className="diag-label">FLIGHT STATUS:</span>
              <span className="diag-value">FLIGHT READY</span>
            </div>
            <div className="diag-line dim-text">
              <span className="diag-label">TARGET LOCK:</span>
              <span className="diag-value">N/A</span>
            </div>
          </div>

          {/* Dual Holographic Gauges (Energy & Armor) */}
          <div className="hud-card dual-gauges-card">
            <div className="gauge-item">
              <div className="gauge-circular">
                <svg viewBox="0 0 40 40" className="gauge-svg">
                  <circle cx="20" cy="20" r="16" className="gauge-bg" />
                  <circle
                    cx="20"
                    cy="20"
                    r="16"
                    className="gauge-fill energy-fill"
                    strokeDasharray="100"
                    strokeDashoffset="2"
                  />
                </svg>
                <span className="gauge-percent">98%</span>
              </div>
              <span className="gauge-label">ENERGY</span>
            </div>

            <div className="gauge-item">
              <div className="gauge-circular">
                <svg viewBox="0 0 40 40" className="gauge-svg">
                  <circle cx="20" cy="20" r="16" className="gauge-bg" />
                  <circle
                    cx="20"
                    cy="20"
                    r="16"
                    className="gauge-fill armor-fill"
                    strokeDasharray="100"
                    strokeDashoffset="0"
                  />
                </svg>
                <span className="gauge-percent">100%</span>
              </div>
              <span className="gauge-label">ARMOR</span>
            </div>
          </div>

          {/* Left Audio Input Oscilloscope Waveform */}
          <div className="hud-card audio-wave-card">
            <div className="hud-card-header">
              <span className="hud-tag">AUDIO INPUT</span>
              <span className="hud-subtag">24-BIT / 96kHz</span>
            </div>
            <div className="wave-display">
              <svg viewBox="0 0 200 60" className="wave-svg">
                <defs>
                  <linearGradient id="waveGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#00e5ff" stopOpacity="0.3" />
                    <stop offset="50%" stopColor="#00f0ff" stopOpacity="1" />
                    <stop offset="100%" stopColor="#00e5ff" stopOpacity="0.3" />
                  </linearGradient>
                </defs>
                <path
                  d={`M 0 30 Q 25 ${30 + Math.sin(waveOffset) * 18}, 50 30 T 100 30 T 150 30 T 200 30`}
                  fill="none"
                  stroke="url(#waveGrad)"
                  strokeWidth="2.5"
                  className="wave-line-main"
                />
                <path
                  d={`M 0 30 Q 30 ${30 + Math.cos(waveOffset * 1.5) * 12}, 70 30 T 140 30 T 200 30`}
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="1.2"
                  strokeOpacity="0.6"
                />
              </svg>
            </div>
            <div className="wave-footer-telemetry">
              <span>GAIN: +12dB</span>
              <span>FILTER: LOWPASS</span>
              <span>CH: L+R</span>
            </div>
          </div>
        </div>

        {/* Center Holographic Ring Overlay Around Arc Reactor */}
        <div className="hud-center-rings">
          <div className="reactor-reticle-ring ring-outer">
            <span className="angle-tick tick-0">0°</span>
            <span className="angle-tick tick-90">90°</span>
            <span className="angle-tick tick-180">180°</span>
            <span className="angle-tick tick-270">270°</span>
          </div>

          <div className="reactor-reticle-ring ring-segmented" />
          <div className="reactor-reticle-ring ring-inner-dashes" />

          {/* Telemetry Tag on Reactor */}
          <div className="reactor-core-tag">
            <span className="reactor-core-lbl">REACTOR OUTPUT</span>
            <span className="reactor-core-val">8.4 GW</span>
          </div>

          {/* Bottom Holographic Emitter Pedestal */}
          <div className="hologram-pedestal-base">
            <div className="pedestal-glow-beam" />
            <div className="pedestal-disc" />
          </div>
        </div>

        {/* Right Telemetry Column */}
        <div className="hud-col hud-col-right">
          {/* Radar Sweep Scanner */}
          <div className="hud-card radar-card">
            <div className="hud-card-header">
              <span className="hud-tag">AUDIO INPUT</span>
              <span className="hud-tag radar-mode">RADAR SCAN</span>
            </div>
            <div className="radar-screen">
              <div className="radar-grid" />
              <div className="radar-circle-1" />
              <div className="radar-circle-2" />
              <div
                className="radar-sweep-beam"
                style={{ transform: `rotate(${radarAngle}deg)` }}
              />
              <div className="radar-blip blip-1" />
              <div className="radar-blip blip-2" />
              <div className="radar-blip blip-3" />
            </div>
          </div>

          {/* Flight & Stability Readouts */}
          <div className="hud-card flight-card">
            <div className="flight-stat-row">
              <div className="flight-item">
                <span className="fl-label">ALTITUDE</span>
                <span className="fl-value">34k ft</span>
              </div>
              <div className="flight-item">
                <span className="fl-label">SPEED</span>
                <span className="fl-value">Mach 1.2</span>
              </div>
            </div>

            <div className="flight-stat-row">
              <div className="flight-item">
                <span className="fl-label">BATTERY</span>
                <span className="fl-value green-text">98% [===]</span>
              </div>
              <div className="flight-item">
                <span className="fl-label">LEVEL</span>
                <span className="fl-value green-text">100%</span>
              </div>
            </div>
          </div>

          {/* Lower Soundwave & Energy Stability Analyzer */}
          <div className="hud-card stability-card">
            <div className="hud-card-header">
              <span className="hud-tag">TEMP: 32°C</span>
              <span className="hud-tag green-text">STABILITY: 99.8%</span>
            </div>
            <div className="stability-wave-container">
              <svg viewBox="0 0 200 45" className="stability-svg">
                <path
                  d={`M 0 22 Q 20 ${22 - Math.sin(waveOffset * 1.8) * 14}, 45 22 T 90 22 T 140 22 T 200 22`}
                  fill="none"
                  stroke="#00f0ff"
                  strokeWidth="2"
                />
                <path
                  d="M 0 35 L 30 32 L 60 20 L 90 25 L 120 12 L 150 18 L 180 8 L 200 15"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />
              </svg>
            </div>
            <div className="stability-labels">
              <span>ENERGY STABILITY</span>
              <span>HARMONIC HARVEST</span>
            </div>
          </div>
        </div>

        {/* Live Conversation Display (Question & Answer) */}
        {latestTurn && (
          <div className="hud-live-turn-display">
            <div className="turn-box">
              <div className="turn-speaker-badge">
                {latestTurn.role === 'user' ? 'YOU (VOICE/INPUT)' : 'J.A.R.V.I.S.'}
              </div>
              <div className="turn-text-content">
                {latestJarvis ? latestJarvis.text : latestTurn.text}
              </div>
            </div>
          </div>
        )}

        {/* Bottom Interactive Command Bar */}
        <div className="hud-bottom-command-bar">
          <div className="quick-commands-row">
            <button
              type="button"
              className="quick-chip"
              onClick={() => onAsk('Run full system diagnostics and suit status report')}
            >
              Diagnostic Scan
            </button>
            <button
              type="button"
              className="quick-chip"
              onClick={() => onAsk('What is the current Arc Reactor output and energy stability?')}
            >
              Reactor Output
            </button>
            <button
              type="button"
              className="quick-chip"
              onClick={() => onAsk('Check Mark suit armor integrity and flight parameters')}
            >
              Armor Status
            </button>
            <button
              type="button"
              className="quick-chip"
              onClick={() => onAsk('Who are you and what are your capabilities?')}
            >
              Introduce JARVIS
            </button>
            <button
              type="button"
              className="quick-chip"
              onClick={() => onAsk('Initiate radar target sweep and check perimeter')}
            >
              Radar Sweep
            </button>
          </div>

          <form className="hud-input-form" onSubmit={handleSubmit}>
            <button
              type="button"
              className={`hud-mic-btn ${isListening ? 'mic-active' : ''}`}
              onClick={onToggleMic}
              title={isListening ? 'Microphone Active — Listening' : 'Click to Speak'}
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
              <span>{isListening ? 'LISTENING...' : 'VOICE'}</span>
            </button>

            <input
              type="text"
              className="hud-text-input"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask JARVIS a question or give a command, Sir..."
            />

            <button type="submit" className="hud-send-btn">
              <span>TRANSMIT</span>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
