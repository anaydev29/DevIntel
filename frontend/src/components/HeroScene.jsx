import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import SceneFallback from './SceneFallback'

// The landing-page 3D scene: a blue data core with two rings of coloured chips orbiting it.
// It tilts towards the mouse, spins faster when you click it, pauses when it is off-screen
// or the tab is hidden, and stays still for people who prefer reduced motion.

const PALETTE = [0xffe14d, 0xff5ca8, 0x3ddc97, 0x4d7cff, 0xe6e2ff]
const BLACK = 0x000000
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

// Small deterministic random generator, so the scene looks the same on every load
function makeRandom(seed) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

// A coloured box with a thick black outline: a slightly larger black box drawn inside-out behind it
function chip(w, h, d, color) {
  const group = new THREE.Group()
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.6, metalness: 0 }),
  )
  const hull = new THREE.Mesh(
    new THREE.BoxGeometry(w + 0.1, h + 0.1, d + 0.1),
    new THREE.MeshBasicMaterial({ color: BLACK, side: THREE.BackSide }),
  )
  group.add(hull, body)
  return group
}

function build(canvas, host) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0x000000, 0)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100)
  scene.add(new THREE.AmbientLight(0xffffff, 1.15))
  const key = new THREE.DirectionalLight(0xffffff, 2.6)
  key.position.set(5, 7, 9)
  scene.add(key)

  const rig = new THREE.Group()
  scene.add(rig)

  // The core: a low-poly sphere with a black outline
  const core = new THREE.Group()
  const coreGeo = new THREE.IcosahedronGeometry(1.9, 1)
  const coreHull = new THREE.Mesh(coreGeo, new THREE.MeshBasicMaterial({ color: BLACK, side: THREE.BackSide }))
  coreHull.scale.setScalar(1.07)
  const coreBody = new THREE.Mesh(
    coreGeo,
    new THREE.MeshStandardMaterial({ color: 0x4d7cff, flatShading: true, roughness: 0.5, metalness: 0 }),
  )
  core.add(coreHull, coreBody)
  rig.add(core)

  // Two tilted orbits, each with a thin black ring and chips travelling along it
  const rand = makeRandom(7)
  const orbits = [
    { radius: 3.3, tilt: [1.15, 0.2], speed: 0.38, count: 6 },
    { radius: 4.4, tilt: [-0.6, 0.9], speed: -0.26, count: 8 },
  ]
  const movers = []
  orbits.forEach((orbit, oi) => {
    const group = new THREE.Group()
    group.rotation.set(orbit.tilt[0], orbit.tilt[1], 0)
    group.add(new THREE.Mesh(
      new THREE.TorusGeometry(orbit.radius, 0.045, 8, 120),
      new THREE.MeshBasicMaterial({ color: BLACK }),
    ))
    for (let i = 0; i < orbit.count; i++) {
      const color = PALETTE[Math.floor(rand() * PALETTE.length)]
      const node = rand() > 0.5 ? chip(0.95, 0.6, 0.16, color) : chip(0.5, 0.5, 0.5, color)
      group.add(node)
      movers.push({
        node,
        radius: orbit.radius,
        phase: (i / orbit.count) * Math.PI * 2 + oi,
        speed: orbit.speed,
        spinX: 0.4 + rand() * 0.8,
        spinY: 0.4 + rand() * 0.8,
      })
    }
    rig.add(group)
  })

  const pointer = { x: 0, y: 0 }
  const eased = { x: 0, y: 0 }
  let yaw = 0
  let boost = 0
  let t = 0
  let last = performance.now()
  let raf = 0
  let running = false
  let visible = true

  function update(dt) {
    t += dt
    const follow = Math.min(1, dt * 4)
    eased.x += (pointer.x - eased.x) * follow
    eased.y += (pointer.y - eased.y) * follow
    boost *= Math.pow(0.04, dt)
    yaw += dt * (0.22 + boost)
    rig.rotation.y = yaw + eased.x * 0.8
    rig.rotation.x = -eased.y * 0.5 + Math.sin(t * 0.6) * 0.05
    core.rotation.y -= dt * 0.35
    for (const m of movers) {
      const a = m.phase + t * m.speed
      m.node.position.set(Math.cos(a) * m.radius, Math.sin(a) * m.radius, 0)
      m.node.rotation.x += dt * m.spinX
      m.node.rotation.y += dt * m.spinY
    }
  }

  function frame(now) {
    raf = 0
    if (!running) return
    const dt = Math.min((now - last) / 1000, 0.05)
    last = now
    update(dt)
    renderer.render(scene, camera)
    raf = requestAnimationFrame(frame)
  }
  function start() {
    if (running || reduceMotion) return
    running = true
    last = performance.now()
    raf = requestAnimationFrame(frame)
  }
  function stop() {
    running = false
    if (raf) cancelAnimationFrame(raf)
    raf = 0
  }

  function resize() {
    const w = Math.max(1, host.clientWidth)
    const h = Math.max(1, host.clientHeight)
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.position.set(0, 0.4, 15.5 / Math.min(1, w / h))
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
    renderer.render(scene, camera)
  }

  update(0.6) // start from a pleasing pose, also for the still image used with reduced motion
  resize()

  const observer = new ResizeObserver(resize)
  observer.observe(host)
  const io = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting
    if (visible && !document.hidden) start()
    else stop()
  })
  io.observe(host)
  const onVisibility = () => (document.hidden || !visible ? stop() : start())
  document.addEventListener('visibilitychange', onVisibility)

  const onMove = (e) => {
    pointer.x = clamp((e.clientX / window.innerWidth) * 2 - 1, -1, 1)
    pointer.y = clamp((e.clientY / window.innerHeight) * 2 - 1, -1, 1)
  }
  const onLeave = () => { pointer.x = 0; pointer.y = 0 }
  const onDown = () => { boost = Math.min(boost + 2.4, 5) }
  if (!reduceMotion) {
    window.addEventListener('pointermove', onMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', onLeave)
    canvas.addEventListener('pointerdown', onDown)
  }

  return () => {
    stop()
    observer.disconnect()
    io.disconnect()
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('pointermove', onMove)
    document.documentElement.removeEventListener('pointerleave', onLeave)
    canvas.removeEventListener('pointerdown', onDown)
    scene.traverse((obj) => {
      obj.geometry?.dispose()
      const mat = obj.material
      if (Array.isArray(mat)) mat.forEach((m) => m.dispose())
      else mat?.dispose()
    })
    renderer.dispose()
  }
}

export default function HeroScene() {
  const hostRef = useRef(null)
  const canvasRef = useRef(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cleanup
    try {
      cleanup = build(canvasRef.current, hostRef.current)
    } catch (err) {
      console.warn('The 3D scene is not available on this device:', err)
      setFailed(true)
    }
    return () => cleanup?.()
  }, [])

  if (failed) return <SceneFallback />
  return (
    <div ref={hostRef} style={{ position: 'absolute', inset: 0 }}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label="Interactive 3D illustration: a blue data core with coloured chips orbiting it. It tilts as you move the mouse."
      />
    </div>
  )
}
