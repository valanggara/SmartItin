export function BrandLogo({ className }: { className?: string }) {
  return (
    <img
      src="/smartitin-logo.png"
      alt="SmartItin — Plan less. Wander more."
      className={className ?? 'mx-auto h-auto w-64 sm:w-80'}
    />
  )
}
