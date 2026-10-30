import { useState } from 'react'

export function FallbackImage({ src, alt, className }: { src: string; alt: string; className: string }) {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    // Renders a same-sized placeholder instead of nothing — an image that
    // fails to load (or was never found) used to collapse to zero height,
    // which shifted whatever's absolutely positioned over it (e.g. a
    // "Recommended" badge) down onto the text below instead of the image
    // area it was meant to sit on.
    return <div className={`${className} bg-sand-200`} aria-label={`${alt} (no image available)`} />
  }
  return <img src={src} alt={alt} className={className} loading="lazy" onError={() => setFailed(true)} />
}

export function MapsLink({ href, className }: { href: string; className?: string }) {
  if (!href) return null
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className={`text-xs font-medium text-teal-600 underline ${className ?? ''}`}
    >
      View on Google Maps →
    </a>
  )
}
