import type { ReactNode } from 'react'
import { SkeletonBlock } from './SkeletonBlock'

interface SectionShellProps {
  title: string
  icon?: ReactNode
  loading: boolean
  errorMessage?: string | null
  children: ReactNode
}

export function SectionShell({ title, icon, loading, errorMessage, children }: SectionShellProps) {
  return (
    <section className="rounded-2xl border border-sand-200 bg-cream p-6 shadow-sm sm:p-8">
      <h2 className="mb-4 flex items-center gap-2 text-2xl text-teal-700">
        {icon && (
          <span aria-hidden="true" className="text-teal-600">
            {icon}
          </span>
        )}
        {title}
      </h2>
      {loading ? (
        <SkeletonBlock />
      ) : errorMessage ? (
        <p className="text-sm text-coral-600">Couldn't load this section: {errorMessage}</p>
      ) : (
        <div className="animate-fade-in">{children}</div>
      )}
    </section>
  )
}
