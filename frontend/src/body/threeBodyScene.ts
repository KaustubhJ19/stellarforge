import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Status } from "../contracts";
import type { BodyScene, BodySceneFactory, BodyView, LayerId } from "./view";

const BASE = import.meta.env.BASE_URL;
const MODEL_URL = `${BASE}models/body-male.glb`;
/** Glowing structures stay visible even when their layer is faded. */
const GLOW_MIN_OPACITY = 0.85;

function cssColor(name: string, fallback: string): THREE.Color {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return new THREE.Color(v || fallback);
}

interface Part {
  mesh: THREE.Mesh;
  material: THREE.MeshStandardMaterial;
  kind: "structure" | "outline";
  layer: LayerId;
}

/** Real WebGL body drawn with Three.js from the Spike B GLB. */
export const threeBodyScene: BodySceneFactory = (host) => {
  if (typeof WebGL2RenderingContext === "undefined") {
    throw new Error("this browser has no WebGL");
  }
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 1.4);
  key.position.set(1, 2, 3);
  scene.add(key);

  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 50);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;

  const status: Record<Status, THREE.Color> = {
    green: cssColor("--status-green", "#3ccf7a"),
    amber: cssColor("--status-amber", "#f5b53d"),
    red: cssColor("--status-red", "#ff5a5a"),
  };
  const layerColor = (layer: LayerId) => cssColor(`--layer-${layer}`, "#cccccc");

  const parts = new Map<string, Part>();
  let heart: THREE.Mesh | null = null;
  let view: BodyView | null = null;
  let disposed = false;

  const draco = new DRACOLoader().setDecoderPath(`${BASE}draco/`);
  new GLTFLoader()
    .setDRACOLoader(draco)
    .loadAsync(MODEL_URL)
    .then((gltf) => {
      if (disposed) return;
      gltf.scene.traverse((o) => {
        if (!(o instanceof THREE.Mesh)) return;
        const { kind, layer } = o.userData as { kind: Part["kind"]; layer: LayerId };
        const material = new THREE.MeshStandardMaterial({
          color: layerColor(layer),
          roughness: 0.65,
          metalness: 0,
          transparent: true,
        });
        o.material = material;
        parts.set(o.name, { mesh: o, material, kind, layer });
      });
      heart = parts.get("heart")?.mesh ?? null;
      if (heart) centreOnItself(heart);
      scene.add(gltf.scene);
      frame(gltf.scene);
      if (view) apply(view);
      host.dataset.loaded = "true";
    })
    .catch((e: Error) => {
      host.dataset.error = e.message;
    });

  function centreOnItself(mesh: THREE.Mesh) {
    mesh.geometry.computeBoundingBox();
    const c = mesh.geometry.boundingBox!.getCenter(new THREE.Vector3());
    mesh.geometry.translate(-c.x, -c.y, -c.z);
    mesh.position.add(c);
  }

  function frame(object: THREE.Object3D) {
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const centre = box.getCenter(new THREE.Vector3());
    controls.target.copy(centre);
    camera.position.set(centre.x, centre.y, centre.z + size.y * 1.7);
    controls.minDistance = 0.15;
    controls.maxDistance = size.y * 4;
    controls.update();
  }

  function apply(next: BodyView) {
    view = next;
    for (const [name, p] of parts) {
      const layer = next.layers[p.layer];
      const s = p.kind === "structure" ? next.structures[name] : undefined;
      const glow = s?.status ?? null;
      let opacity = s?.opacity ?? layer.opacity;
      if (glow) opacity = Math.max(opacity, GLOW_MIN_OPACITY);
      p.mesh.visible = layer.visible && opacity > 0.01;
      p.material.opacity = opacity;
      p.material.depthWrite = opacity > 0.9;
      p.mesh.renderOrder = glow ? 2 : p.kind === "structure" ? 1 : 0;
      if (glow) {
        p.material.color.copy(status[glow]);
        p.material.emissive.copy(status[glow]);
        p.material.emissiveIntensity = 0.55;
      } else {
        p.material.color.copy(layerColor(p.layer));
        p.material.emissive.setRGB(0, 0, 0);
      }
    }
  }

  const ro = new ResizeObserver(() => {
    const { clientWidth: w, clientHeight: h } = host;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  });
  ro.observe(host);

  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const t = clock.getElapsedTime();
    if (heart) {
      const bpm = view?.heartRate ?? 0;
      // A short beat: quick swell then relax, once per beat.
      const phase = bpm > 0 ? (t * bpm) / 60 - Math.floor((t * bpm) / 60) : 1;
      const beat = phase < 0.15 ? Math.sin((phase / 0.15) * Math.PI) : 0;
      heart.scale.setScalar(1 + 0.08 * beat);
    }
    controls.update();
    renderer.render(scene, camera);
  });

  const handle: BodyScene = {
    apply,
    dispose() {
      disposed = true;
      renderer.setAnimationLoop(null);
      ro.disconnect();
      controls.dispose();
      draco.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
  return handle;
};
