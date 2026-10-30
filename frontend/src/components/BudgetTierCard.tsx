import type { BudgetTier } from '../types'
import type { TierDefaults } from '../tiers'

interface BudgetTierCardProps {
  tier: BudgetTier
  defaults: TierDefaults
  selected: boolean
  onSelect: () => void
}

export function BudgetTierCard({ defaults, selected, onSelect }: BudgetTierCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`flex-1 rounded-2xl border-2 p-5 text-left transition ${
        selected
          ? 'border-teal-500 bg-teal-500/5 shadow-md'
          : 'border-sand-200 bg-cream hover:border-teal-500/50'
      }`}
    >
      <p className="font-display text-xl text-teal-700">{defaults.label}</p>
      <p className="mt-1 text-sm font-medium text-teal-700/80">{defaults.tagline}</p>
      <ul className="mt-2 space-y-0.5 text-sm text-teal-700/70">
        {defaults.bullets.map((bullet) => (
          <li key={bullet}>- {bullet}</li>
        ))}
      </ul>
    </button>
  )
}
