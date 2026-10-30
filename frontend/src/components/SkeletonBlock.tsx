export function SkeletonBlock() {
  return (
    <div className="animate-pulse space-y-3" aria-label="Loading" role="status">
      <div className="h-4 w-3/4 rounded bg-sand-200" />
      <div className="h-4 w-1/2 rounded bg-sand-200" />
      <div className="h-4 w-5/6 rounded bg-sand-200" />
    </div>
  )
}
