import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Status } from "../contracts";
import type { BodyScene, BodySceneFactory, BodyView, Focus, LayerId } from "./view";
import { STRUCTURES, structuresIn, type RegionId, type StructureId } from "./structures";

const BASE = import.meta.env.BASE_URL;
const MODEL_URL = `${BASE}models/body-male.glb`;
/** Higher-detail structures for one region, fetched the first time it is zoomed into. */
const regionDetailUrl = (region: RegionId) => `${BASE}models/body-male.${region}.glb`;
const FLY_SECONDS = 0.6;
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
  let lungs: THREE.Mesh | null = null;
  let view: BodyView | null = null;
  let body: THREE.Object3D | null = null;
  let framedFocus = "";
  const detailRequested = new Set<RegionId>();
  let fly: { from: [THREE.Vector3, THREE.Vector3]; to: [THREE.Vector3, THREE.Vector3]; t: number } | null = null;
  let disposed = false;

  const draco = new DRACOLoader().setDecoderPath(`${BASE}draco/`);
  const loader = new GLTFLoader().setDRACOLoader(draco);
  loader
    .loadAsync(MODEL_URL)
    .then((gltf) => {
      if (disposed) return;
      gltf.scene.traverse((o) => {
        if (!(o instanceof THREE.Mesh)) return;
        // GLTFLoader strips dots from node names, so the structure id travels in glTF extras.
        const { kind, layer, id } = o.userData as { kind: Part["kind"]; layer: LayerId; id: string };
        const material = new THREE.MeshStandardMaterial({
          color: layerColor(layer),
          roughness: 0.65,
          metalness: 0,
          transparent: true,
        });
        o.material = material;
        parts.set(id, { mesh: o, material, kind, layer });
      });
      heart = parts.get("heart")?.mesh ?? null;
      lungs = parts.get("lungs")?.mesh ?? null;
      if (heart) centreOnItself(heart);
      if (lungs) centreOnItself(lungs);
      scene.add(gltf.scene);
      body = gltf.scene;
      const box = new THREE.Box3().setFromObject(body);
      controls.maxDistance = box.getSize(new THREE.Vector3()).y * 4;
      controls.minDistance = 0.05;
      jumpTo(box);
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

  /** Camera target and position that fit `box`, looking from the current direction. */
  function shotOf(box: THREE.Box3, margin: number): [THREE.Vector3, THREE.Vector3] {
    const size = box.getSize(new THREE.Vector3());
    const centre = box.getCenter(new THREE.Vector3());
    const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const fitHeight = size.y / 2 / Math.tan(halfFov);
    const fitWidth = size.x / 2 / (Math.tan(halfFov) * camera.aspect);
    const distance = Math.max(fitHeight, fitWidth, 0.12) * margin + size.z / 2;
    const dir = camera.position.clone().sub(controls.target);
    if (dir.lengthSq() < 1e-9) dir.set(0, 0, 1);
    return [centre, centre.clone().add(dir.normalize().multiplyScalar(distance))];
  }

  function jumpTo(box: THREE.Box3) {
    camera.position.set(0, 0, 1);
    controls.target.set(0, 0, 0);
    const [target, position] = shotOf(box, 1.12);
    controls.target.copy(target);
    camera.position.copy(position);
    controls.update();
  }

  function flyTo(box: THREE.Box3, margin = 1.12) {
    fly = { from: [controls.target.clone(), camera.position.clone()], to: shotOf(box, margin), t: 0 };
  }

  function boxOf(ids: StructureId[]): THREE.Box3 {
    const box = new THREE.Box3();
    for (const id of ids) {
      const p = parts.get(id);
      if (p) box.expandByObject(p.mesh);
    }
    return box;
  }

  function regionOf(focus: Focus): RegionId | null {
    if (focus.level === "region") return focus.region;
    if (focus.level === "structure") return STRUCTURES[focus.structure].region;
    return null;
  }

  function loadDetail(region: RegionId) {
    if (detailRequested.has(region)) return;
    detailRequested.add(region);
    loader
      .loadAsync(regionDetailUrl(region))
      .then((gltf) => {
        if (disposed) return;
        gltf.scene.traverse((o) => {
          const p = o instanceof THREE.Mesh ? parts.get(o.userData.id) : undefined;
          if (!p) return;
          const detail = (o as THREE.Mesh).geometry;
          // Keep the coarse mesh's local origin (the heart is centred on itself to pulse).
          detail.translate(-p.mesh.position.x, -p.mesh.position.y, -p.mesh.position.z);
          p.mesh.geometry.dispose();
          p.mesh.geometry = detail;
        });
        host.dataset.detail = [...detailRequested].join(" ");
      })
      .catch(() => detailRequested.delete(region));
  }

  function applyFocus(focus: Focus) {
    const key = JSON.stringify(focus);
    if (!body || key === framedFocus) return;
    framedFocus = key;
    const region = regionOf(focus);
    if (region) loadDetail(region);
    if (focus.level === "body") flyTo(new THREE.Box3().setFromObject(body));
    else if (focus.level === "region") flyTo(boxOf(structuresIn(focus.region)));
    else flyTo(boxOf([focus.structure]), 1.8);
  }

  function apply(next: BodyView) {
    view = next;
    applyFocus(next.focus);
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
      } else if (next.wholeBody) {
        // Whole-body Indicators: a soft tint across everything that is not glowing itself.
        p.material.color.copy(layerColor(p.layer)).lerp(status[next.wholeBody], 0.45);
        p.material.emissive.copy(status[next.wholeBody]);
        p.material.emissiveIntensity = 0.15;
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

  const start = performance.now();
  let last = start;
  renderer.setAnimationLoop((now: number) => {
    const t = (now - start) / 1000;
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (heart) {
      const bpm = view?.heartRate ?? 0;
      // A short beat: quick swell then relax, once per beat.
      const phase = bpm > 0 ? (t * bpm) / 60 - Math.floor((t * bpm) / 60) : 1;
      const beat = phase < 0.15 ? Math.sin((phase / 0.15) * Math.PI) : 0;
      heart.scale.setScalar(1 + 0.08 * beat);
    }
    if (lungs) {
      const rate = view?.breathRate ?? 0;
      // Smooth in-and-out, once per breath.
      const swell = rate > 0 ? 0.5 - 0.5 * Math.cos((t * rate * 2 * Math.PI) / 60) : 0;
      lungs.scale.set(1 + 0.03 * swell, 1 + 0.02 * swell, 1 + 0.04 * swell);
    }
    if (fly) {
      fly.t = Math.min(1, fly.t + dt / FLY_SECONDS);
      const k = 1 - Math.pow(1 - fly.t, 3); // ease out
      controls.target.lerpVectors(fly.from[0], fly.to[0], k);
      camera.position.lerpVectors(fly.from[1], fly.to[1], k);
      if (fly.t >= 1) fly = null;
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
