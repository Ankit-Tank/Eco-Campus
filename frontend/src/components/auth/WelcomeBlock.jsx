import { Leaf } from 'lucide-react'

// Leaf icon + heading + one line of text. Shown at the top of every login step.
export default function WelcomeBlock({ title, subtitle }) {
  return (
    <div className="login-welcome">
      <Leaf size={56} fill="currentColor" strokeWidth={1.25} />
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  )
}
