import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OcctKernel } from 'occt-wasm';

let kernelPromise: Promise<OcctKernel> | null = null;

function getKernel() {
  if (!kernelPromise) {
    kernelPromise = OcctKernel.init().catch((err) => {
      kernelPromise = null;
      throw err;
    });
  }
  return kernelPromise;
}

export default function StepViewer({ url }: { url: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState('Loading STEP geometry…');
  const [error, setError] = useState('');

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let disposed = false;
    let animationFrame = 0;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100000);
    camera.up.set(0, 0, 1);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    el.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x64748b, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 2.8);
    key.position.set(1, -2, 3);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 1.3);
    fill.position.set(-2, 1, 1);
    scene.add(fill);

    const model = new THREE.Group();
    scene.add(model);

    async function loadStep() {
      let shape: ReturnType<OcctKernel['importStep']> | null = null;
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Could not load STEP file (HTTP ${response.status})`);

        const buffer = await response.arrayBuffer();
        if (disposed) return;

        setStatus('Tessellating STEP geometry…');
        const kernel = await getKernel();
        if (disposed) return;

        shape = kernel.importStep(buffer);
        const meshData = kernel.tessellate(shape, {
          linearDeflection: 0.1,
          angularDeflection: 0.5,
          relative: true,
        });
        kernel.release(shape);
        shape = null;

        if (!meshData.positions.length || !meshData.indices.length) {
          throw new Error('STEP file did not produce any visible triangles.');
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(meshData.positions, 3));
        if (meshData.normals.length === meshData.positions.length) {
          geometry.setAttribute('normal', new THREE.BufferAttribute(meshData.normals, 3));
        } else {
          geometry.computeVertexNormals();
        }
        geometry.setIndex(new THREE.BufferAttribute(meshData.indices, 1));
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();

        const material = new THREE.MeshStandardMaterial({
          color: 0xd9dee7,
          roughness: 0.72,
          metalness: 0.04,
          side: THREE.DoubleSide,
        });
        const solid = new THREE.Mesh(geometry, material);
        model.add(solid);

        const edgesGeometry = new THREE.EdgesGeometry(geometry, 28);
        const edges = new THREE.LineSegments(
          edgesGeometry,
          new THREE.LineBasicMaterial({ color: 0x334155, transparent: true, opacity: 0.5 }),
        );
        model.add(edges);

        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        model.position.sub(center);

        const maxDim = Math.max(size.x, size.y, size.z) || 1;
        const distance = maxDim / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)));
        camera.near = Math.max(maxDim / 10000, 0.001);
        camera.far = Math.max(maxDim * 1000, 1000);
        camera.position.set(distance * 0.8, -distance * 1.15, distance * 0.8);
        camera.updateProjectionMatrix();

        controls.target.set(0, 0, 0);
        controls.update();

        const axes = new THREE.AxesHelper(maxDim * 0.2);
        scene.add(axes);

        if (!disposed) {
          setStatus('');
          setError('');
        }
      } catch (err) {
        if (shape) {
          try {
            const kernel = await getKernel();
            kernel.release(shape);
          } catch {}
        }
        if (!disposed) {
          setStatus('');
          setError(err instanceof Error ? err.message : 'STEP tessellation failed');
        }
      }
    }

    function resize() {
      if (!el) return;
      const width = Math.max(el.clientWidth, 1);
      const height = Math.max(el.clientHeight, 1);
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
    loadStep();

    return () => {
      disposed = true;
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', resize);
      controls.dispose();
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh || obj instanceof THREE.LineSegments) {
          obj.geometry.dispose();
          const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      el.innerHTML = '';
    };
  }, [url]);

  return (
    <div className="step-viewer">
      <div className="step-viewer-canvas" ref={ref} />
      <div className="viewer-hint">Tessellated STEP · rotate · pan · zoom</div>
      {status && <div className="step-viewer-status">{status}</div>}
      {error && <div className="step-viewer-error">{error}</div>}
    </div>
  );
}
