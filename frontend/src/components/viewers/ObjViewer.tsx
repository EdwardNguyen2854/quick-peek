import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export default function ObjViewer({ url }: { url: string }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.innerHTML = '';

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);
    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 100000);
    camera.position.set(4, 3, 6);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;

    scene.add(new THREE.HemisphereLight(0xffffff, 0xcccccc, 2.2));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(5, 8, 5);
    scene.add(light);
    scene.add(new THREE.GridHelper(10, 10, 0xe5e7eb, 0xf3f4f6));

    let loadedObject: THREE.Object3D | null = null;
    let disposed = false;

    function fitObject(obj: THREE.Object3D) {
      const box = new THREE.Box3().setFromObject(obj);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      obj.position.sub(center);
      const maxDim = Math.max(size.x, size.y, size.z) || 1;
      camera.position.set(maxDim * 1.4, maxDim * 1.1, maxDim * 1.8);
      camera.near = Math.max(maxDim / 1000, 0.001);
      camera.far = maxDim * 1000;
      camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0);
      controls.update();
    }

    new OBJLoader().load(url, (obj) => {
      if (disposed) return;
      obj.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          if (!mesh.material) mesh.material = new THREE.MeshStandardMaterial();
        }
      });
      loadedObject = obj;
      scene.add(obj);
      fitObject(obj);
    }, undefined, (err) => {
      if (disposed) return;
      const canvas = renderer.domElement;
      const ctx = canvas.getContext('webgl');
      console.error('OBJ load failed', err, ctx);
    });

    function resize() {
      if (!el) return;
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(el.clientWidth, el.clientHeight);
    }
    function animate() {
      if (disposed) return;
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }
    window.addEventListener('resize', resize);
    animate();

    return () => {
      disposed = true;
      window.removeEventListener('resize', resize);
      controls.dispose();
      if (loadedObject) {
        loadedObject.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.geometry?.dispose();
            const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
            materials.forEach((m) => m?.dispose());
          }
        });
      }
      renderer.dispose();
      el.innerHTML = '';
    };
  }, [url]);

  return <div className="step-viewer" ref={ref}><div className="viewer-hint">Rotate · pan · zoom</div></div>;
}
