import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import SceneFallback from './SceneFallback'

// The landing-page 3D scene: the "Multi-Language Tech Matrix".
// 18 floating cubes show a language or tool on every face, and 32 small voxels orbit around them.
// The whole cluster turns towards the mouse, a click gives it a spin, it pauses when scrolled out of
// view or when the tab is hidden, and it stays still for people who prefer reduced motion.

const SPECS = [
  { name: 'Python', symbol: '\u{1F40D} PY', bg: '#ffe600', accent: '#3776ab', size: 1.22, pos: [-3.8, 2.6, 1.4], rot: [0.012, 0.016] },
  { name: 'TypeScript', symbol: 'TS //', bg: '#00f0ff', accent: '#007acc', size: 1.2, pos: [3.8, 2.7, -0.6], rot: [-0.01, 0.014] },
  { name: 'Rust', symbol: '\u{1F980} RS', bg: '#ff66c4', accent: '#b7410e', size: 1.25, pos: [4.4, -0.2, 1.1], rot: [-0.014, 0.014] },
  { name: 'Go Lang', symbol: 'GO >>', bg: '#4efa94', accent: '#00add8', size: 1.18, pos: [-1.4, 3.5, -1.2], rot: [0.009, 0.016] },
  { name: 'React', symbol: '\u269B UI', bg: '#ffffff', accent: '#61dafb', size: 1.2, pos: [-4.6, 0.1, 0.8], rot: [0.015, -0.012] },
  { name: 'FastAPI', symbol: '\u26A1 API', bg: '#ffe600', accent: '#05998b', size: 1.2, pos: [1.4, 3.4, 1.0], rot: [-0.015, -0.01] },
  { name: 'Postgres', symbol: '\u{1F418} SQL', bg: '#60a5fa', accent: '#336791', size: 1.2, pos: [-3.7, -2.5, -0.8], rot: [0.012, 0.012] },
  { name: 'Next.js', symbol: '\u25B2 NEXT', bg: '#ffffff', accent: '#000000', size: 1.18, pos: [3.6, -2.6, 0.6], rot: [-0.011, -0.014] },
  { name: 'Docker', symbol: '\u{1F433} OPS', bg: '#38bdf8', accent: '#2496ed', size: 1.22, pos: [-1.2, -3.5, 1.2], rot: [0.013, -0.01] },
  { name: 'Node.js', symbol: '\u{1F7E2} JS', bg: '#86efac', accent: '#22c55e', size: 1.18, pos: [1.3, -3.4, -1.0], rot: [-0.013, 0.012] },
  { name: 'C++', symbol: '\u26A1 C++', bg: '#cbd5e1', accent: '#00599c', size: 1.16, pos: [-2.1, 0.4, -2.4], rot: [0.014, 0.01] },
  { name: 'Kotlin', symbol: '\u{1F7E3} KT', bg: '#c084fc', accent: '#7f52ff', size: 1.18, pos: [2.0, 0.5, 2.2], rot: [-0.012, 0.016] },
  { name: 'Swift', symbol: '\u{1F54A} SW', bg: '#f97316', accent: '#ea580c', size: 1.18, pos: [-5.0, -1.8, -1.5], rot: [0.011, 0.015] },
  { name: 'Java', symbol: '\u2615 JV', bg: '#f87171', accent: '#dc2626', size: 1.2, pos: [5.0, 1.5, 1.8], rot: [-0.012, 0.01] },
  { name: 'GraphQL', symbol: '\u25C8 GQL', bg: '#f472b6', accent: '#e11d48', size: 1.15, pos: [0.0, 1.8, -2.6], rot: [0.016, -0.012] },
  { name: 'Redis', symbol: '\u26A1 RDS', bg: '#ef4444', accent: '#991b1b', size: 1.18, pos: [2.6, -1.8, -2.1], rot: [-0.014, 0.015] },
  { name: 'Vue.js', symbol: '\u25B2 VUE', bg: '#34d399', accent: '#059669', size: 1.18, pos: [-2.4, -1.4, 2.2], rot: [0.013, -0.013] },
  { name: 'Ruby', symbol: '\u{1F48E} RB', bg: '#fb7185', accent: '#be123c', size: 1.16, pos: [0.0, -2.0, 2.8], rot: [0.01, 0.016] },
]
const VOXEL_COLORS = [0xffe600, 0x4efa94, 0x00f0ff, 0xff66c4, 0xffffff, 0xc084fc, 0x38bdf8]
const VOXELS = 32
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

// Draws one cube face. The artwork is laid out on a 512 x 512 grid and scaled to the canvas size.
function drawFace(canvas, spec) {
  const ctx = canvas.getContext('2d')
  ctx.setTransform(canvas.width / 512, 0, 0, canvas.height / 512, 0, 0)
  ctx.fillStyle = spec.bg
  ctx.fillRect(0, 0, 512, 512)
  ctx.lineWidth = 28
  ctx.strokeStyle = '#000000'
  ctx.strokeRect(14, 14, 484, 484)
  ctx.fillStyle = spec.accent
  ctx.fillRect(36, 36, 100, 16)
  ctx.fillRect(440, 36, 36, 36)
  ctx.strokeRect(440, 36, 36, 36)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#000000'
  ctx.font = '700 115px "Space Grotesk", "Courier New", monospace, sans-serif'
  ctx.fillText(spec.symbol, 256, 215, 420)
  ctx.fillRect(36, 355, 440, 92)
  ctx.fillStyle = '#ffffff'
  ctx.font = '700 46px "Space Grotesk", sans-serif'
  ctx.fillText(spec.name.toUpperCase(), 256, 404, 400)
}

function build(canvas, host) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0x000000, 0)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000)

  // Newer three.js versions measure light in physical units, which is about PI times dimmer
  const k = parseInt(THREE.REVISION, 10) >= 155 ? Math.PI : 1
  scene.add(new THREE.AmbientLight(0xffffff, 1.5 * k))
  const yellow = new THREE.DirectionalLight(0xffe600, 2.4 * k)
  yellow.position.set(7, 9, 8)
  const cyan = new THREE.DirectionalLight(0x00f0ff, 2.0 * k)
  cyan.position.set(-7, -4, 6)
  const pink = new THREE.DirectionalLight(0xff66c4, 1.6 * k)
  pink.position.set(0, -6, -4)
  scene.add(yellow, cyan, pink)

  const main = new THREE.Group()
  scene.add(main)

  const anisotropy = renderer.capabilities.getMaxAnisotropy()
  const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x000000 })

  // The 18 technology cubes
  const faces = []
  const cubes = SPECS.map((spec) => {
    const face = document.createElement('canvas')
    face.width = 256
    face.height = 256
    drawFace(face, spec)
    const texture = new THREE.CanvasTexture(face)
    texture.anisotropy = anisotropy
    texture.colorSpace = THREE.SRGBColorSpace
    faces.push({ face, spec, texture })

    const geometry = new THREE.BoxGeometry(spec.size, spec.size, spec.size)
    const mesh = new THREE.Mesh(geometry, new THREE.MeshPhongMaterial({ map: texture, flatShading: true, shininess: 75 }))
    mesh.position.set(spec.pos[0], spec.pos[1], spec.pos[2])
    mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry), edgeMaterial))
    main.add(mesh)
    return { mesh, rot: spec.rot, baseY: spec.pos[1] }
  })

  // The 32 orbiting voxels. They are added to the scene, not the group, so they keep orbiting
  // while the cluster turns towards the mouse.
  const voxelGeometry = new THREE.BoxGeometry(0.26, 0.26, 0.26)
  const voxelEdges = new THREE.EdgesGeometry(voxelGeometry)
  const voxels = []
  for (let i = 0; i < VOXELS; i++) {
    const mesh = new THREE.Mesh(
      voxelGeometry,
      new THREE.MeshPhongMaterial({ color: VOXEL_COLORS[i % VOXEL_COLORS.length], flatShading: true }),
    )
    mesh.add(new THREE.LineSegments(voxelEdges, edgeMaterial))
    scene.add(mesh)
    voxels.push({
      mesh,
      angle: (i / VOXELS) * Math.PI * 2,
      radius: 5.4 + (i % 5) * 0.45,
      speed: 0.006 + (i % 3) * 0.003,
      yOff: Math.sin(i * 1.2) * 2.8,
    })
  }

  const pointer = { x: 0, y: 0 }
  const eased = { x: 0, y: 0 }
  let yaw = 0
  let boost = 0
  let t = 0
  let last = performance.now()
  let raf = 0
  let running = false
  let visible = true
  let disposed = false

  function update(dt) {
    t += dt
    const frames = dt * 60 // the motion was designed per frame at 60 fps
    const follow = 1 - Math.pow(0.95, frames)
    eased.x += (pointer.x * 0.65 - eased.x) * follow
    eased.y += (pointer.y * 0.65 - eased.y) * follow
    boost *= Math.pow(0.04, dt)
    yaw += dt * (0.2 + boost)
    main.rotation.y = yaw + eased.x
    main.rotation.x = Math.sin(t * 0.22) * 0.1 - eased.y

    cubes.forEach((c, i) => {
      c.mesh.rotation.x += c.rot[0] * frames
      c.mesh.rotation.y += c.rot[1] * frames
      c.mesh.position.y = c.baseY + Math.sin(t * 1.4 + i * 0.7) * 0.18
    })
    voxels.forEach((v) => {
      v.angle += v.speed * frames
      v.mesh.position.x = Math.cos(v.angle) * v.radius
      v.mesh.position.z = Math.sin(v.angle) * v.radius
      v.mesh.position.y = v.yOff + Math.sin(t * 1.6 + v.angle) * 0.3
      v.mesh.rotation.x += 0.02 * frames
      v.mesh.rotation.y += 0.025 * frames
    })
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
    camera.position.set(0, 0, 17.5 / Math.min(1, w / h))
    camera.updateProjectionMatrix()
    renderer.render(scene, camera)
  }

  update(0.5) // a pleasing starting pose, also used for the still image with reduced motion
  resize()

  // The first drawing may use a fallback font. Draw the faces again when the real font is ready.
  document.fonts?.load?.('700 46px "Space Grotesk"')
    .then(() => {
      if (disposed) return
      faces.forEach(({ face, spec, texture }) => { drawFace(face, spec); texture.needsUpdate = true })
      if (!running) renderer.render(scene, camera)
    })
    .catch(() => {})

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
    pointer.y = clamp(-((e.clientY / window.innerHeight) * 2 - 1), -1, 1)
  }
  const onLeave = () => { pointer.x = 0; pointer.y = 0 }
  const onDown = () => { boost = Math.min(boost + 2.4, 5) }
  if (!reduceMotion) {
    window.addEventListener('pointermove', onMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', onLeave)
    canvas.addEventListener('pointerdown', onDown)
  }

  return () => {
    disposed = true
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
      if (Array.isArray(mat)) mat.forEach((m) => { m.map?.dispose(); m.dispose() })
      else if (mat) { mat.map?.dispose(); mat.dispose() }
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
        aria-label="Interactive 3D illustration: eighteen cubes showing programming languages and tools float in a cluster with small blocks orbiting around them. The cluster turns towards the mouse."
      />
    </div>
  )
}
