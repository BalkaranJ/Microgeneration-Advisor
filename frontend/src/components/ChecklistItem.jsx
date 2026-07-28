export default function ChecklistItem({ text }) {
  return (
    <div className="checklist-item">
      <div className="checklist-circle" />
      <span className="checklist-text">{text}</span>
    </div>
  )
}
