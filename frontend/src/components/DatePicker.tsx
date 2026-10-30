import { useEffect, useRef, useState, type ReactNode } from 'react'

// Fully custom-rendered (no native <input type="date">) so it looks pixel
// identical in every browser — WebKit/Safari renders native date-input
// internals (unfilled-state color, segment layout) very differently from
// Chrome/Blink, and there's no reliable cross-browser CSS way to normalize
// just the "unset" state without also affecting filled values.

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]
const WEEKDAY_LABELS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function toISODate(year: number, month: number, day: number): string {
  return `${year}-${pad(month + 1)}-${pad(day)}`
}

function parseISODate(value: string): { year: number; month: number; day: number } | null {
  if (!value) return null
  const [y, m, d] = value.split('-').map(Number)
  if (!y || !m || !d) return null
  return { year: y, month: m - 1, day: d }
}

interface DatePickerProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  min?: string
  icon?: ReactNode
}

export function DatePicker({ value, onChange, placeholder, min, icon }: DatePickerProps) {
  const [open, setOpen] = useState(false)
  const parsed = parseISODate(value)
  const now = new Date()
  const [viewYear, setViewYear] = useState(parsed?.year ?? now.getFullYear())
  const [viewMonth, setViewMonth] = useState(parsed?.month ?? now.getMonth())
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function daysInMonth(year: number, month: number): number {
    return new Date(year, month + 1, 0).getDate()
  }

  function firstWeekday(year: number, month: number): number {
    return new Date(year, month, 1).getDay()
  }

  const numDays = daysInMonth(viewYear, viewMonth)
  const startWeekday = firstWeekday(viewYear, viewMonth)
  const cells: (number | null)[] = [
    ...Array(startWeekday).fill(null),
    ...Array.from({ length: numDays }, (_, i) => i + 1),
  ]

  function selectDay(day: number) {
    onChange(toISODate(viewYear, viewMonth, day))
    setOpen(false)
  }

  function prevMonth() {
    if (viewMonth === 0) {
      setViewMonth(11)
      setViewYear(viewYear - 1)
    } else {
      setViewMonth(viewMonth - 1)
    }
  }

  function nextMonth() {
    if (viewMonth === 11) {
      setViewMonth(0)
      setViewYear(viewYear + 1)
    } else {
      setViewMonth(viewMonth + 1)
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex w-full items-center gap-2 rounded-lg border border-sand-200 bg-cream py-2 text-left outline-none focus:border-teal-500 ${
          icon ? 'pl-9 pr-3' : 'px-3'
        } ${value ? 'text-teal-700' : 'text-teal-700/40'}`}
      >
        {icon && <span className="pointer-events-none absolute left-3 text-teal-700/50">{icon}</span>}
        {value || placeholder || 'Select date'}
      </button>

      {open && (
        <div className="absolute z-10 mt-1 w-64 rounded-lg border border-sand-200 bg-cream p-3 shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <button type="button" onClick={prevMonth} className="px-2 text-teal-600 hover:text-teal-700">
              ‹
            </button>
            <span className="text-sm font-medium text-teal-700">
              {MONTH_NAMES[viewMonth]} {viewYear}
            </span>
            <button type="button" onClick={nextMonth} className="px-2 text-teal-600 hover:text-teal-700">
              ›
            </button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-xs text-teal-700/50">
            {WEEKDAY_LABELS.map((w) => (
              <div key={w}>{w}</div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-sm">
            {cells.map((day, i) => {
              if (day === null) return <div key={i} />
              const iso = toISODate(viewYear, viewMonth, day)
              const isSelected = iso === value
              const isDisabled = min ? iso < min : false
              return (
                <button
                  key={i}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => selectDay(day)}
                  className={`rounded-full py-1 ${
                    isSelected
                      ? 'bg-teal-500 text-cream'
                      : isDisabled
                        ? 'cursor-not-allowed text-teal-700/20'
                        : 'text-teal-700 hover:bg-teal-500/10'
                  }`}
                >
                  {day}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
