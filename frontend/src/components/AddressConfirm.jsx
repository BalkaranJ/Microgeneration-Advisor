import { useState } from 'react'

export default function AddressConfirm({ onAnswer, error: submitError, placeholder }) {
  const [address, setAddress] = useState('')
  const [status, setStatus] = useState('idle') // 'idle' | 'checking' | 'review' | 'error'
  const [geo, setGeo] = useState(null)
  const [checkError, setCheckError] = useState(null)

  async function handleCheck(e) {
    e.preventDefault()
    const trimmed = address.trim()
    if (!trimmed) return

    setStatus('checking')
    setCheckError(null)

    try {
      const res = await fetch('http://localhost:8000/geocode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: trimmed }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Couldn't find that address.")
      setGeo(data)
      setStatus('review')
    } catch (e) {
      setCheckError(e.message)
      setStatus('error')
    }
  }

  function handleConfirm() {
    onAnswer(geo.display_name, { lat: geo.lat, lon: geo.lon, location: geo.display_name })
  }

  function handleEdit() {
    setStatus('idle')
    setGeo(null)
  }

  if (status === 'checking') {
    return (
      <div className="upload-progress">
        <span className="spin">⚙️</span>
        <span>Looking up your address...</span>
      </div>
    )
  }

  if (status === 'review' && geo) {
    return (
      <div className="upload-review">
        <p className="review-note">
          We found: <strong>{geo.display_name}</strong>. Is this your property?
        </p>
        <div className="review-actions">
          <button type="button" className="choice-btn" onClick={handleConfirm}>Yes, that's it →</button>
          <button type="button" className="choice-btn" onClick={handleEdit}>No, edit address</button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleCheck}>
      <div className="input-row">
        <div className="input-wrapper">
          <input
            autoFocus
            className="text-input"
            type="text"
            name="property-address-lookup"
            autoComplete="off"
            placeholder={placeholder || 'Type your address...'}
            value={address}
            onChange={e => setAddress(e.target.value)}
          />
        </div>
        <button type="submit" className="submit-btn">Check address →</button>
      </div>
      {checkError && <p className="step-error">{checkError}</p>}
      {submitError && <p className="step-error">{submitError}</p>}
    </form>
  )
}
