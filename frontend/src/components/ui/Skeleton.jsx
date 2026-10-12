// Grey placeholder block shown while data loads.
export default function Skeleton({ height = 16, width = '100%', radius = 8, style }) {
  return <span className="skeleton" aria-hidden="true" style={{ height, width, borderRadius: radius, ...style }} />
}
