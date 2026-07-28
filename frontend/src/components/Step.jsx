import { useState } from 'react'
import { motion } from 'framer-motion'
import BillUpload from './BillUpload'
import AddressConfirm from './AddressConfirm'

export default function Step({ step, onAnswer, error }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!value.toString().trim()) return
    onAnswer(value.toString().trim())
  }

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <p className="step-question">{step.question}</p>
      {step.hint && <p className="step-hint">{step.hint}</p>}

      {step.type === 'bill-upload' ? (
        <BillUpload onAnswer={onAnswer} error={error} />
      ) : step.type === 'address-confirm' ? (
        <AddressConfirm onAnswer={onAnswer} error={error} placeholder={step.placeholder} />
      ) : step.type === 'choice' ? (
        <div className="choices">
          {step.choices.map(choice => (
            <button
              key={choice.value}
              className="choice-btn"
              onClick={() => onAnswer(choice.value)}
            >
              <span>{choice.icon}</span>
              <span>{choice.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="input-row">
            <div className="input-wrapper">
              <input
                autoFocus
                className="text-input"
                type={step.type === 'number' ? 'number' : 'text'}
                placeholder={step.placeholder || 'Type your answer...'}
                value={value}
                onChange={e => setValue(e.target.value)}
                min={step.type === 'number' ? 0.1 : undefined}
                step={step.type === 'number' ? 'any' : undefined}
                style={step.unit ? { paddingRight: '42px' } : {}}
              />
              {step.unit && <span className="input-unit">{step.unit}</span>}
            </div>
            <button type="submit" className="submit-btn">Next →</button>
          </div>
          {error && <p className="step-error">{error}</p>}
        </form>
      )}
    </motion.div>
  )
}
