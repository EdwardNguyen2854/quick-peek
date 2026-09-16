import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OcctKernel } from 'occt-wasm';

type StepMeshData = {
  positions: Float32Array;
  normals: Float32Array;
  indices: Uint32Array;
};

let kernelPromise: Promise<OcctKernel> | null = null;
const meshCache = new Map<string, Promise<StepMeshData>>();
const thumbnailCache = new Map<string, Promise<string>>();
let thumbnailQueue: Promise<void> = Promise.resolve();

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

function buildModel(mesh: StepMeshData, edgeOpacity = 0.38) {
  const group = new THREE.Group();
  const geometry = makeGeometry(mesh);

  const material = new THREE.MeshStandardMaterial({
    color: 0xd7dce3,
    roughness: 0.78,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });

  const solid = new THREE.Mesh(geometry, material);
  group.add(solid);

  const edgesGeometry = new THREE.EdgesGeometry(geometry, 28);
  const edges = new THREE.LineSegments(
    edgesGeometry,
    new THREE.LineBasicMaterial({
      color: 0x475569,
      transparent: true,
      opacity: edgeOpacity,
    }),
  );
  group.add(edges);

  return group;
}

function fitModel(model: THREE.Object3D, camera: THREE.PerspectiveCamera) {
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  model.position.sub(center);

  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const distance = maxDim / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)));

  camera.near = Math.max(maxDim / 10000, 0.001);
  camera.far = Math.max(maxDim * 1000, 1000);
  camera.position.set(distance * 0.86, -distance * 1.18, distance * 0.78);
  camera.updateProjectionMatrix();

  return maxDim;
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

function renderThumbnail(mesh: StepMeshData): string {
  const width = 720;
  const height = 430;

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    preserveDrawingBuffer: true,
  });
  renderer.setPixelRatio(1);
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf7f7f5);

  const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100000);
  camera.up.set(0, 0, 1);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x94a3b8, 2.1));
  const key = new THREE.DirectionalLight(0xffffff, 2.6);
  key.position.set(2, -3, 4);
  scene.add(key);

  const model = buildModel(mesh, 0.34);
  scene.add(model);
  fitModel(model, camera);

  renderer.render(scene, camera);
  const image = renderer.domElement.toDataURL('image/png');

  disposeObject(model);
  renderer.dispose();
  renderer.forceContextLoss();

  return image;
}

function loadStepThumbnail(url: string): Promise<string> {
  const cached = thumbnailCache.get(url);
  if (cached) return cached;

  const promise = loadStepMesh(url)
    .then((mesh) => new Promise<string>((resolve, reject) => {
      thumbnailQueue = thumbnailQueue
        .then(() => {
          try {
            resolve(renderThumbnail(mesh));
          } catch (error) {
            reject(error);
          }
        })
        .catch(() => undefined);
    }))
    .catch((error) => {
      thumbnailCache.delete(url);
      throw error;
    });

  thumbnailCache.set(url, promise);
  return promise;
}

export function StepThumbnail({ url, label }: { url: string; label: string }) {
  const [image, setImage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setImage('');
    setError('');

    loadStepThumbnail(url)
      .then((dataUrl) => {
        if (!cancelled) setImage(dataUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'STEP preview failed');
      });

    return () => {
      cancelled = true;
    };
  }, [url]);

  if (error) {
    return (
      <div className="step-thumbnail error">
        <span>3D preview unavailable</span>
        <small>{error}</small>
      </div>
    );
  }

  if (!image) {
    return (
      <div className="step-thumbnail loading">
        <span className="thumbnail-spinner" />
        <small>Tessellating STEP…</small>
      </div>
    );
  }

  return <img className="step-thumbnail-image" src={image} alt={`${label} 3D preview`} />;
}

export default function StepViewer({ url }: { url: string }) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState('Loading 3D geometry…');
  const [error, setError] = useState('');

  useEffect(() => {
    const element = canvasRef.current;
    if (!element) return;

    let disposed = false;
    let animationFrame = 0;
    let model: THREE.Group | null = null;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf7f7f5);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100000);
    camera.up.set(0, 0, 1);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    element.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x64748b, 2.25));
    const key = new THREE.DirectionalLight(0xffffff, 2.9);
    key.position.set(2, -3, 4);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 1.1);
    fill.position.set(-3, 2, 1);
    scene.add(fill);

    async function load() {
      try {
        setStatus('Tessellating STEP…');
        const mesh = await loadStepMesh(url);
        if (disposed) return;

        model = buildModel(mesh, 0.42);
        scene.add(model);

        const maxDim = fitModel(model, camera);
        controls.target.set(0, 0, 0);
        controls.update();

        const axes = new THREE.AxesHelper(maxDim * 0.16);
        scene.add(axes);

        setError('');
        setStatus('');
      } catch (err) {
        if (!disposed) {
          setStatus('');
          setError(err instanceof Error ? err.message : 'STEP tessellation failed');
        }
      }
    }

    function resize() {
      if (!element) return;
      const width = Math.max(element.clientWidth, 1);
      const height = Math.max(element.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    }

    function animate() {
      if (disposed) return;
      controls.update();
      renderer.render(scene, camera);
      animationFrame = requestAnimationFrame(animate);
    }

    window.addEventListener('resize', resize);
    resize();
    animate();
    load();

    return () => {
      disposed = true;
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', resize);
      controls.dispose();
      disposeObject(scene);
      renderer.dispose();
      element.innerHTML = '';
    };
  }, [url]);

  return (
    <div className="step-viewer">
      <div className="step-viewer-canvas" ref={canvasRef} />
      <div className="viewer-hint">Drag to rotate · wheel to zoom · right-drag to pan</div>
      {status && <div className="step-viewer-status">{status}</div>}
      {error && <div className="step-viewer-error">{error}</div>}
    </div>
  );
}
