import { Link } from 'react-router-dom'
import { Leaf } from 'lucide-react'
import { APP_NAME } from '../config.js'

// Logo + name. Clicking it always goes to the login page.
// onClick is optional (the login page uses it to reset its form).
export default function Brand({ onClick }) {
  return (
    <Link to="/login" className="brand" onClick={onClick}>
      <Leaf size={38} fill="currentColor" strokeWidth={1.5} />
      <span>{APP_NAME}</span>
    </Link>
  )
}
