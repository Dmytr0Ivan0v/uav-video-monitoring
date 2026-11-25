// three.js view of one VO run against ground truth: both paths, the camera at a moment, the error between them.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { NavigationDoc, VoRun } from './types';

// motion capture is z up, three.js is y up
const toScene = (x: number, y: number, z: number) => new THREE.Vector3(x, z, -y);

export interface SceneColors {
  gt: string;
  vo: string;
  degraded: string;
  lost: string;
  error: string;
  grid: string;
  camera: string;
}

export interface NavScene {
  showRun(run: VoRun): void;
  showPose(index: number): void;
  resize(): void;
  dispose(): void;
}

// frustum of the camera in its optical frame: x right, y down, z forward, m
const FRUSTUM = [
  [0, 0, 0],
  [-0.08, -0.06, 0.12],
  [0.08, -0.06, 0.12],
  [0.08, 0.06, 0.12],
  [-0.08, 0.06, 0.12],
] as const;
const FRUSTUM_EDGES = [0, 1, 0, 2, 0, 3, 0, 4, 1, 2, 2, 3, 3, 4, 4, 1];

export function createScene(canvas: HTMLCanvasElement, doc: NavigationDoc, colors: SceneColors): NavScene {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 50);

  const gtPoints = doc.gt.map(([, x, y, z]) => toScene(x, y, z));
  const sphere = new THREE.Box3().setFromPoints(gtPoints).getBoundingSphere(new THREE.Sphere());
  const center = sphere.center;
  // from above and to the side, far enough to see the whole path in a 45 degree view
  camera.position.copy(center).add(new THREE.Vector3(1, 0.9, 1.2).normalize().multiplyScalar(sphere.radius * 1.7));
  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(center);
  controls.enableDamping = true;

  const grid = new THREE.GridHelper(2, 20, colors.grid, colors.grid);
  grid.position.set(center.x, Math.min(...gtPoints.map((p) => p.y)) - 0.05, center.z);
  scene.add(grid);

  const line = (points: THREE.Vector3[], color: string) =>
    new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color }));
  scene.add(line(gtPoints, colors.gt));

  // VO path with a colour per status: one vertex colour per pose
  const vo = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ vertexColors: true }));
  scene.add(vo);

  const frustum = new THREE.LineSegments(
    new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(FRUSTUM_EDGES.length * 3, 3)),
    new THREE.LineBasicMaterial({ color: colors.camera }),
  );
  scene.add(frustum);
  const error = line([new THREE.Vector3(), new THREE.Vector3()], colors.error);
  scene.add(error);
  const marker = new THREE.Mesh(new THREE.SphereGeometry(0.012, 12, 8), new THREE.MeshBasicMaterial({ color: colors.gt }));
  scene.add(marker);

  let run: VoRun | null = null;
  let frame = 0;

  function showRun(r: VoRun): void {
    run = r;
    const status = (k: number) => r.statuses[k];
    const pos: number[] = [];
    const col: number[] = [];
    const c = new THREE.Color();
    for (const p of r.poses) {
      const v = toScene(p[1], p[2], p[3]);
      pos.push(v.x, v.y, v.z);
      const s = status(p[9]);
      c.set(s === 'DEGRADED' ? colors.degraded : s === 'LOST' ? colors.lost : colors.vo);
      col.push(c.r, c.g, c.b);
    }
    vo.geometry.dispose();
    vo.geometry = new THREE.BufferGeometry()
      .setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
      .setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    showPose(Math.min(frame, r.poses.length - 1));
  }

  function showPose(i: number): void {
    if (!run) return;
    frame = i;
    const p = run.poses[i]!;
    const q = new THREE.Quaternion(p[4], p[5], p[6], p[7]);
    const t = new THREE.Vector3(p[1], p[2], p[3]);
    const corners = FRUSTUM.map(([x, y, z]) => {
      const w = new THREE.Vector3(x, y, z).applyQuaternion(q).add(t);
      return toScene(w.x, w.y, w.z);
    });
    const attr = frustum.geometry.getAttribute('position') as THREE.BufferAttribute;
    FRUSTUM_EDGES.forEach((k, n) => attr.setXYZ(n, corners[k]!.x, corners[k]!.y, corners[k]!.z));
    attr.needsUpdate = true;
    const g = doc.gt[i]!;
    const gt = toScene(g[1], g[2], g[3]);
    (error.geometry.getAttribute('position') as THREE.BufferAttribute).setXYZ(0, corners[0]!.x, corners[0]!.y, corners[0]!.z);
    (error.geometry.getAttribute('position') as THREE.BufferAttribute).setXYZ(1, gt.x, gt.y, gt.z);
    error.geometry.getAttribute('position').needsUpdate = true;
    marker.position.copy(gt);
  }

  function resize(): void {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  let stopped = false;
  const loop = () => {
    if (stopped) return;
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  };
  resize();
  loop();

  return {
    showRun,
    showPose,
    resize,
    dispose() {
      stopped = true;
      controls.dispose();
      renderer.dispose();
    },
  };
}
