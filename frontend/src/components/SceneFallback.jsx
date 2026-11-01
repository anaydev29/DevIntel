// Shown instead of the 3D scene when WebGL is not available or the scene fails to load.
export default function SceneFallback({ message = '3D view not available on this device' }) {
  return (
    <div className="di-fallback" role="img" aria-label="Decorative illustration">
      <div className="di-fallback__shape" style={{ position: 'relative' }} />
      <p>{message}</p>
    </div>
  )
}
