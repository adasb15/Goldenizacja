import { badgeTone } from '../../utils/formatters'

function StatusBadge({ value }) {
  return <span className={`badge badge--${badgeTone(value)}`}>{value}</span>
}

export { StatusBadge }
