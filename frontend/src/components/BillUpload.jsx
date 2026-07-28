import { useState } from 'react'

function formatMonth(monthStr) {
  const [year, month] = (monthStr || '').split('-')
  if (!year || !month) return monthStr || '—'
  const d = new Date(Number(year), Number(month) - 1, 1)
  return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

function formatMoney(value) {
  return value != null ? `$${value.toFixed(2)}` : '—'
}

const ANNUAL_SOURCE_LABEL = {
  monthly_history: 'a full 12 months of billing history',
  monthly_history_estimated: 'a partial year of billing history, extrapolated to 12 months',
  current_period_extrapolated: "this bill's current period, extrapolated to a full year",
}

export default function BillUpload({ onAnswer, error: submitError }) {
  const [mode, setMode] = useState('upload') // 'upload' | 'manual'
  const [status, setStatus] = useState('idle') // 'idle' | 'uploading' | 'review' | 'error'
  const [preview, setPreview] = useState(null)
  const [previewIsImage, setPreviewIsImage] = useState(true)
  const [fileName, setFileName] = useState(null)
  const [extractError, setExtractError] = useState(null)
  const [result, setResult] = useState(null)
  const [value, setValue] = useState('')

  async function handleFile(file) {
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setPreviewIsImage(file.type.startsWith('image/'))
    setFileName(file.name)
    setStatus('uploading')
    setExtractError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('http://localhost:8000/extract-bill', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Could not read the bill.')

      setResult(data)
      setValue(data.annual_usage_kwh ? String(data.annual_usage_kwh) : '')
      setStatus('review')
    } catch (e) {
      setExtractError(e.message)
      setStatus('error')
    }
  }

  function handleConfirm(e) {
    e.preventDefault()
    if (!value.toString().trim()) return
    onAnswer(
      value.toString().trim(),
      result
        ? {
            electricity_charge_incl_gst: result.electricity_charge_incl_gst,
            bill_period_usage_kwh: result.usage_kwh,
          }
        : undefined
    )
  }

  function resetToUpload() {
    setStatus('idle')
    setPreview(null)
    setPreviewIsImage(true)
    setFileName(null)
    setResult(null)
    setExtractError(null)
  }

  function renderPreview() {
    if (!preview) return null
    if (previewIsImage) {
      return <img src={preview} alt="Bill preview" className="upload-thumb" />
    }
    return (
      <div className="upload-file-chip">
        <span>📄</span>
        <span>{fileName}</span>
      </div>
    )
  }

  if (mode === 'manual') {
    return (
      <form onSubmit={handleConfirm}>
        <div className="input-row">
          <div className="input-wrapper">
            <input
              autoFocus
              className="text-input"
              type="number"
              placeholder="9000"
              value={value}
              onChange={e => setValue(e.target.value)}
              min="0.1"
              step="any"
              style={{ paddingRight: '42px' }}
            />
            <span className="input-unit">kWh</span>
          </div>
          <button type="submit" className="submit-btn">Next →</button>
        </div>
        <button type="button" className="link-btn" onClick={() => setMode('upload')}>
          ← Upload a bill photo or PDF instead
        </button>
        {submitError && <p className="step-error">{submitError}</p>}
      </form>
    )
  }

  return (
    <div className="bill-upload">
      {status === 'idle' && (
        <>
          <label className="upload-dropzone">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,application/pdf"
              onChange={e => handleFile(e.target.files?.[0])}
              hidden
            />
            <span className="upload-icon">📷</span>
            <span>Upload a photo or PDF of your bill</span>
            <span className="upload-hint">Enmax, Atco, or Epcor — JPEG, PNG, or PDF</span>
          </label>
          <button type="button" className="link-btn" onClick={() => setMode('manual')}>
            Enter usage manually instead
          </button>
        </>
      )}

      {status === 'uploading' && (
        <div className="upload-progress">
          {renderPreview()}
          <span className="spin">⚙️</span>
          <span>Reading your bill...</span>
        </div>
      )}

      {status === 'error' && (
        <div className="upload-review">
          <p className="step-error">{extractError}</p>
          <div className="review-actions">
            <button type="button" className="choice-btn" onClick={resetToUpload}>
              Try another file
            </button>
            <button type="button" className="choice-btn" onClick={() => setMode('manual')}>
              Enter manually instead
            </button>
          </div>
        </div>
      )}

      {status === 'review' && (
        <form onSubmit={handleConfirm} className="upload-review">
          {renderPreview()}
          {result?.annual_usage_kwh ? (
            <p className="review-note">
              Based on {ANNUAL_SOURCE_LABEL[result.annual_source] || "this bill"}
              {result.bill_date ? ` (bill dated ${result.bill_date})` : ''}, your estimated
              annual usage is <strong>{result.annual_usage_kwh} kWh</strong>. Confirm or edit below.
            </p>
          ) : (
            <p className="review-note">
              We couldn't confidently estimate your annual usage from this bill.
              Please confirm or enter it manually below.
            </p>
          )}

          {(result?.avg_cost_per_day != null ||
            result?.electricity_charge_excl_gst != null ||
            result?.electricity_charge_gst != null ||
            result?.electricity_charge_incl_gst != null) && (
            <div className="bill-details">
              {result.avg_cost_per_day != null && (
                <div className="bill-detail-row">
                  <span>Avg. cost/day</span>
                  <span>{formatMoney(result.avg_cost_per_day)}</span>
                </div>
              )}
              {result.electricity_charge_excl_gst != null && (
                <div className="bill-detail-row">
                  <span>Electricity charge (before GST)</span>
                  <span>{formatMoney(result.electricity_charge_excl_gst)}</span>
                </div>
              )}
              {result.electricity_charge_gst != null && (
                <div className="bill-detail-row">
                  <span>GST</span>
                  <span>{formatMoney(result.electricity_charge_gst)}</span>
                </div>
              )}
              {result.electricity_charge_incl_gst != null && (
                <div className="bill-detail-row">
                  <span>Electricity charge (with GST)</span>
                  <span>{formatMoney(result.electricity_charge_incl_gst)}</span>
                </div>
              )}
            </div>
          )}

          {result?.monthly_history?.length > 0 && (
            <details className="monthly-history">
              <summary>Monthly history ({result.monthly_history.length} months read)</summary>
              <div className="monthly-history-list">
                {result.monthly_history.map((m, i) => (
                  <div key={i} className="monthly-history-row">
                    <span>{formatMonth(m.month)}</span>
                    <span>{m.kwh != null ? `${m.kwh} kWh` : '—'}</span>
                    <span>{formatMoney(m.cost)}</span>
                  </div>
                ))}
              </div>
            </details>
          )}

          <div className="input-row">
            <div className="input-wrapper">
              <input
                autoFocus
                className="text-input"
                type="number"
                value={value}
                onChange={e => setValue(e.target.value)}
                min="0.1"
                step="any"
                style={{ paddingRight: '42px' }}
              />
              <span className="input-unit">kWh</span>
            </div>
            <button type="submit" className="submit-btn">Confirm →</button>
          </div>
          <button type="button" className="link-btn" onClick={resetToUpload}>
            Try another file
          </button>
          {submitError && <p className="step-error">{submitError}</p>}
        </form>
      )}
    </div>
  )
}
