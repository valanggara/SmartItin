import type { ReactNode } from 'react'

interface SelectFieldProps {
  value: string | number
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
  children: ReactNode
  icon?: ReactNode
}

// Safari renders <select> with its own skeuomorphic chrome (3D gradient +
// spinner arrows) that ignores most CSS unless the native appearance is
// reset first — this normalizes it to a flat look with a hand-drawn arrow,
// consistent across browsers (Chrome's native arrow is also replaced by
// the same custom one, so both browsers render identically).
export function SelectField({ value, onChange, children, icon }: SelectFieldProps) {
  return (
    <div className="relative">
      {icon && (
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-teal-700/50">{icon}</span>
      )}
      <select
        value={value}
        onChange={onChange}
        className={`w-full appearance-none rounded-lg border border-sand-200 bg-cream py-2 pr-8 text-teal-700 outline-none focus:border-teal-500 ${
          icon ? 'pl-9' : 'pl-3'
        }`}
      >
        {children}
      </select>
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-teal-700/50">
        ▾
      </span>
    </div>
  )
}
