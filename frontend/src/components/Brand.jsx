import { Link } from 'react-router-dom'
import logo from '../assets/logo.png'
import { APP_NAME } from '../config.js'

// Logo. Clicking it always goes to the login page.
// onClick is optional (the login page uses it to reset its form).
export default function Brand({ onClick }) {
  return (
    <Link to="/login" className="brand" onClick={onClick}>
      <img src={logo} alt={APP_NAME} />
    </Link>
  )
}
