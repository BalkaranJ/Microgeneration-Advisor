import { useState } from 'react'

export default function BillUpload({ onAnswer, error: submitError }) {
  const [mode, setMode] = useState('upload') // 'upload' | 'manual'
  const [status, setStatus] = useState('idle') // 'idle' | 'uploading' | 'review' | 'error'
  const [preview, setPreview] = useState(null)
  const [extractError, setExtractError] = useState(null)
  const [result, setResult] = useState(null)
  const [value, setValue] = useState('')

  async function handleFile(file) {
    if (!file) return
    setPreview(URL.createObjectURL(file))
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
    onAnswer(value.toString().trim())
  }

  function resetToUpload() {
    setStatus('idle')
    setPreview(null)
    setResult(null)
    setExtractError(null)
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
          ← Upload a bill photo instead
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
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={e => handleFile(e.target.files?.[0])}
              hidden
            />
            <span className="upload-icon">📷</span>
            <span>Upload a photo of your bill</span>
            <span className="upload-hint">Enmax, Atco, or Epcor — JPEG or PNG</span>
          </label>
          <button type="button" className="link-btn" onClick={() => setMode('manual')}>
            Enter usage manually instead
          </button>
        </>
      )}

      {status === 'uploading' && (
        <div className="upload-progress">
          {preview && <img src={preview} alt="Bill preview" className="upload-thumb" />}
          <span className="spin">⚙️</span>
          <span>Reading your bill...</span>
        </div>
      )}

      {status === 'error' && (
        <div className="upload-review">
          <p className="step-error">{extractError}</p>
          <div className="review-actions">
            <button type="button" className="choice-btn" onClick={resetToUpload}>
              Try another photo
            </button>
            <button type="button" className="choice-btn" onClick={() => setMode('manual')}>
              Enter manually instead
            </button>
          </div>
        </div>
      )}

      {status === 'review' && (
        <form onSubmit={handleConfirm} className="upload-review">
          {preview && <img src={preview} alt="Bill preview" className="upload-thumb" />}
          {result?.annual_usage_kwh ? (
            <p className="review-note">
              We read <strong>{result.usage_kwh} kWh</strong> for your{' '}
              {result.period_start && result.period_end
                ? `${result.period_start} to ${result.period_end}`
                : 'billing period'} — that's about{' '}
              <strong>{result.annual_usage_kwh} kWh/year</strong>. Confirm or edit below.
            </p>
          ) : (
            <p className="review-note">
              We couldn't confidently estimate your annual usage from this bill.
              Please confirm or enter it manually below.
            </p>
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
            Try another photo
          </button>
          {submitError && <p className="step-error">{submitError}</p>}
        </form>
      )}
    </div>
  )
}
