import { useEffect, useState } from 'react'
import {
  DEFAULT_WEIGHTS,
  SIGNALS,
  SIGNAL_PRESETS,
  loadStoredWeights,
  onWeightsChange,
  sharesDiffer,
  storeWeights,
} from '../lib/score'

export default function WeightCustomizer({
  showBar = true,
  showPresets = true,
  onClose,
  extraAction,
}) {
  const [weights, setWeights] = useState(() => loadStoredWeights() ?? { ...DEFAULT_WEIGHTS })

  useEffect(() => {
    return onWeightsChange((next) => {
      setWeights(next ? { ...next } : { ...DEFAULT_WEIGHTS })
    })
  }, [])

  const metricKeys = Object.keys(SIGNALS)
  const total = metricKeys.reduce((sum, m) => sum + (weights[m] ?? 0), 0)

  // Calculate percentage share for each metric
  const shares = Object.fromEntries(
    metricKeys.map((m) => [m, total > 0 ? Math.round((100 * (weights[m] ?? 0)) / total) : 0]),
  )

  const isCustom = sharesDiffer(weights, DEFAULT_WEIGHTS)

  function updateWeight(metric, value) {
    const next = { ...weights, [metric]: Math.max(0, Math.min(50, Number(value) || 0)) }
    setWeights(next)
    if (sharesDiffer(next, DEFAULT_WEIGHTS)) {
      storeWeights(next)
    } else {
      storeWeights(null)
    }
  }

  function applyPreset(preset) {
    setWeights(preset.weights)
    if (sharesDiffer(preset.weights, DEFAULT_WEIGHTS)) {
      storeWeights(preset.weights)
    } else {
      storeWeights(null)
    }
  }

  function resetDefaults() {
    setWeights({ ...DEFAULT_WEIGHTS })
    storeWeights(null)
  }

  return (
    <div className="di-customizer" aria-label="Score weight customizer">
      {showBar && (
        <div className="di-customizer__bar-wrap">
          <div
            className="di-wbar"
            style={{ marginTop: 0 }}
            role="img"
            aria-label={`Score weights: ${metricKeys.map((m) => `${SIGNALS[m].name} ${shares[m]} percent`).join(', ')}`}
          >
            {metricKeys.map((m) => {
              const pct = shares[m]
              if (pct <= 0) return null
              const sig = SIGNALS[m]
              return (
                <div
                  key={m}
                  className={`di-wseg ${sig.color}`}
                  style={{ flexBasis: `${pct}%`, flexGrow: pct }}
                  title={`${sig.name}: ${pct}%`}
                >
                  {pct >= 6 ? `${pct}%` : ''}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {showPresets && (
        <div className="di-presets">
          <span className="di-presets__label">Quick presets:</span>
          <div className="di-presets__list">
            {SIGNAL_PRESETS.map((p) => {
              const active = !sharesDiffer(weights, p.weights)
              return (
                <button
                  key={p.name}
                  type="button"
                  className={`di-btn di-btn--sm ${active ? 'di-btn--lime' : ''}`}
                  onClick={() => applyPreset(p)}
                  title={p.desc}
                >
                  {p.name}
                </button>
              )
            })}
          </div>
        </div>
      )}

      <div className="di-sliders-grid">
        {metricKeys.map((m) => {
          const sig = SIGNALS[m]
          const pct = shares[m]
          const val = weights[m] ?? 0
          return (
            <div key={m} className={`di-slider-row ${val === 0 ? 'di-slider-row--zero' : ''}`}>
              <div className="di-slider-row__header">
                <span className="di-slider-row__title">
                  <span className={`di-swatch ${sig.color}`} />
                  <span className="di-slider-row__name">{sig.name}</span>
                </span>
                <span className="di-slider-row__meta">
                  <span className="di-slider-row__pct">{pct}%</span>
                  <span className="di-slider-row__raw">({val} pts)</span>
                </span>
              </div>
              <div className="di-slider-row__control">
                <input
                  type="range"
                  min="0"
                  max="45"
                  step="1"
                  value={val}
                  onChange={(e) => updateWeight(m, e.target.value)}
                  className="di-slider"
                  aria-label={`${sig.name} weight slider`}
                />
              </div>
            </div>
          )
        })}
      </div>

      <div className="di-customizer__footer">
        <div className="di-customizer__status">
          {isCustom ? (
            <span className="di-chip bg-hot font-bold">⚡ Custom weights active</span>
          ) : (
            <span className="di-chip bg-mint font-bold">✓ Standard baseline weights</span>
          )}
          <span className="di-customizer__total-hint">Total: {total} weight points</span>
        </div>
        <div className="di-customizer__actions">
          {isCustom && (
            <button
              type="button"
              className="di-btn di-btn--sm"
              onClick={resetDefaults}
            >
              Reset to baseline
            </button>
          )}
          {extraAction}
          {onClose && (
            <button
              type="button"
              className="di-btn di-btn--sm"
              onClick={onClose}
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

