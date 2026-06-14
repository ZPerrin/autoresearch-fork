import { useEffect, useRef, useState } from 'react'

const CONTROLS = [
  ['Wheel', 'Zoom at pointer'],
  ['Drag', 'Pan document'],
  ['Double-click / 0', 'Fit page'],
  ['+ / =', 'Zoom in'],
  ['-', 'Zoom out'],
  ['[ / Left', 'Previous sample'],
  ['] / Right', 'Next sample'],
] as const

export default function ViewerHelp() {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    const onPointerDown = (event: PointerEvent) => {
      const root = rootRef.current
      if (root != null && !root.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className="viewer-help" ref={rootRef}>
      <button
        type="button"
        className="viewer-help-trigger"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen(value => !value)}
      >
        Controls
      </button>
      {open && (
        <div className="viewer-help-popover" role="dialog" aria-label="Viewer controls">
          {CONTROLS.map(([key, label]) => (
            <div className="viewer-help-row" key={key}>
              <kbd>{key}</kbd>
              <span>{label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
