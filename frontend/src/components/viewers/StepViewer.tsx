import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OcctKernel } from 'occt-wasm';

type StepMeshData = {
  positions: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
};

type StepViewportProps = {
  url: string;
  active?: boolean;
  compact?: boolean;
  label?: string;
};

let kernelPromise: Promise<OcctKernel> | null = null;
const meshCache = new Map<string, Promise<StepMeshData>>();

function getKernel() {
  if (!kernelPromise) {
    kernelPromise = OcctKernel.init().catch((error) => {
      kernelPromise = null;
      throw error;
    });
  }
  return kernelPromise;
}

function loadStepMesh(url: string): Promise<StepMeshData> {
  const cached = meshCache.get(url);
  if (cached) return cached;

  const promise = (async () => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not load STEP file (HTTP ${response.status})`);

    const buffer = await response.arrayBuffer();
    const kernel = await getKernel();
    let shape: ReturnType<OcctKernel['importStep']> | null = null;

    try {
      shape = kernel.importStep(buffer);
      const mesh = kernel.tessellate(shape, {
        linearDeflection: 0.02,
        angularDeflection: 0.35,
        relative: true,
      });

      if (!mesh.positions.length || !mesh.indices.length) {
        throw new Error('STEP file did not produce any visible triangles.');
      }

      return {
        positions: new Float32Array(mesh.positions),
        normals: new Float32Array(mesh.normals),
        indices: new Uint32Array(mesh.indices),
      };
    } finally {
      if (shape !== null) kernel.release(shape);
    }
  })().catch((error) => {
    meshCache.delete(url);
    throw error;
  });

  meshCache.set(url, promise);
  return promise;
}

function makeGeometry(mesh: StepMeshData) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(mesh.positions, 3));

  if (mesh.normals.length === mesh.positions.length) {
    geometry.setAttribute('normal', new THREE.BufferAttribute(mesh.normals, 3));
  } else {
    geometry.computeVertexNormals();
  }

  geometry.setIndex(new THREE.BufferAttribute(mesh.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

function buildModel(mesh: StepMeshData, compact: boolean) {
  const group = new THREE.Group();
  const geometry = makeGeometry(mesh);

  const material = new THREE.MeshStandardMaterial({
    color: 0xd7dce3,
    roughness: 0.78,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });

  group.add(new THREE.Mesh(geometry, material));

  const edgesGeometry = new THREE.EdgesGeometry(geometry, 28);
  group.add(new THREE.LineSegments(
    edgesGeometry,
    new THREE.LineBasicMaterial({
      color: 0x475569,
      transparent: true,
      opacity: compact ? 0.34 : 0.42,
    }),
  ));

  return group;
}

function fitModel(model: THREE.Object3D, camera: THREE.PerspectiveCamera, padding: number) {
  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  const sphere = box.getBoundingSphere(new THREE.Sphere());

  model.position.sub(center);

  const radius = Math.max(sphere.radius, 0.5);
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * Math.max(camera.aspect, 0.1));
  const limitingFov = Math.max(Math.min(verticalFov, horizontalFov), 0.1);
  const distance = (radius / Math.sin(limitingFov / 2)) * padding;

  camera.near = Math.max(radius / 10000, 0.001);
  camera.far = Math.max(radius * 10000, 1000);
  camera.position.set(distance * 0.72, -distance * 0.96, distance * 0.68);
  camera.updateProjectionMatrix();

  return radius;
}

function disposeObject(root: THREE.Object3D) {
  root.traverse((object) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
      object.geometry.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach((material) => material.dispose());
    }
  });
}

function StepViewport({ url, active = true, compact = false, label }: StepViewportProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState('Loading 3D geometry…');
  const [error, setError] = useState('');
  const [snapshot, setSnapshot] = useState('');

  useEffect(() => {
    if (!active) return;

    const element = canvasRef.current;
    if (!element) return;

    let disposed = false;
    let animationFrame = 0;
    let model: THREE.Group | null = null;

    setError('');
    setStatus('Loading 3D geometry…');

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf7f7f5);

    const camera = new THREE.PerspectiveCamera(compact ? 38 : 42, 1, 0.1, 100000);
    camera.up.set(0, 0, 1);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      preserveDrawingBuffer: compact,
    });
    renderer.setPixelRatio(compact ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    element.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.enableRotate = true;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.touches.ONE = THREE.TOUCH.ROTATE;
    controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x64748b, compact ? 2.05 : 2.25));

    const key = new THREE.DirectionalLight(0xffffff, compact ? 2.5 : 2.9);
    key.position.set(2, -3, 4);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xffffff, compact ? 0.85 : 1.1);
    fill.position.set(-3, 2, 1);
    scene.add(fill);

    function resize() {
      if (!element) return;
      const width = Math.max(element.clientWidth, 1);
      const height = Math.max(element.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);

      if (model) {
        const radius = fitModel(model, camera, compact ? 1.12 : 1.18);
        controls.target.set(0, 0, 0);
        controls.minDistance = Math.max(radius * 0.02, 0.001);
        controls.maxDistance = radius * 100;
        controls.update();
      }
    }

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(element);

    async function load() {
      try {
        setStatus('Tessellating STEP…');
        const mesh = await loadStepMesh(url);
        if (disposed) return;

        model = buildModel(mesh, compact);
        scene.add(model);

        const radius = fitModel(model, camera, compact ? 1.12 : 1.18);
        controls.target.set(0, 0, 0);
        controls.minDistance = Math.max(radius * 0.02, 0.001);
        controls.maxDistance = radius * 100;
        controls.update();

        if (!compact) {
          scene.add(new THREE.AxesHelper(radius * 0.28));
        }

        renderer.render(scene, camera);

        if (compact) {
          try {
            setSnapshot(renderer.domElement.toDataURL('image/png'));
          } catch {
            // Snapshot is only a fallback for off-screen cards.
          }
        }

        setStatus('');
      } catch (err) {
        if (!disposed) {
          setStatus('');
          setError(err instanceof Error ? err.message : 'STEP tessellation failed');
        }
      }
    }

    function animate() {
      if (disposed) return;
      controls.update();
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(animate);
    }

    load();
    animate();

    return () => {
      disposed = true;
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      controls.dispose();
      disposeObject(scene);
      renderer.dispose();
      renderer.forceContextLoss();
      element.replaceChildren();
    };
  }, [url, active, compact]);

  return (
    <div
      className={`step-viewport ${compact ? 'compact' : 'full'} ${active ? 'active' : 'paused'}`}
      aria-label={label ? `Interactive 3D preview of ${label}` : 'Interactive STEP 3D preview'}
    >
      {(!active && snapshot) && <img className="step-paused-snapshot" src={snapshot} alt="" />}
      <div className="step-viewer-canvas" ref={canvasRef} />
      {compact ? (
        <div className="step-card-hint">Drag rotate · wheel zoom · right-drag pan</div>
      ) : (
        <div className="viewer-hint">Drag to rotate · wheel to zoom · right-drag to pan</div>
      )}
      {active && status && <div className="step-viewer-status">{status}</div>}
      {error && <div className="step-viewer-error">{error}</div>}
      {!active && !snapshot && !error && <div className="step-viewer-status">3D preview paused off-screen</div>}
    </div>
  );
}

export function StepCardViewer({ url, label }: { url: string; label: string }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(false);

  useEffect(() => {
    const element = rootRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => setActive(entry.isIntersecting),
      {
        root: null,
        rootMargin: '260px 0px',
        threshold: 0.01,
      },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="step-card-viewer" ref={rootRef}>
      <StepViewport url={url} label={label} active={active} compact />
    </div>
  );
}

export default function StepViewer({ url }: { url: string }) {
  return <StepViewport url={url} active />;
}
