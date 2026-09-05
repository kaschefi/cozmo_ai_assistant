import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { RobotPose, VisualAnchorData, ObstacleData, BlockData } from './SemanticGridMap';

export interface Cozmo3DWorldMapProps {
  robot: RobotPose;
  anchors: VisualAnchorData[];
  obstacles: ObstacleData[];
  blocks?: BlockData[];
  path?: number[][];
  onPointClick?: (worldX: number, worldY: number) => void;
  onAnchorClick?: (anchor: VisualAnchorData) => void;
  onBlockClick?: (block: BlockData) => void;
  onSimulateDock?: () => void;
  onSpawnBlock?: (x: number, y: number) => void;
  className?: string;
}

interface SceneCollider {
  id: string;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  isRamp?: boolean;
  rampElevation?: number;
}

function solveRigidBodyCollisions(
  posX: number,
  posZ: number,
  robotRadius: number,
  colliders: SceneCollider[]
): { x: number; z: number; elevationY: number; hasCollision: boolean } {
  let resX = posX;
  let resZ = posZ;
  let maxElevation = 0;
  let collided = false;

  for (const box of colliders) {
    if (box.isRamp) {
      if (resX >= box.minX && resX <= box.maxX && resZ >= box.minZ && resZ <= box.maxZ) {
        const rampT = Math.max(0, Math.min(1, (resX - box.minX) / (box.maxX - box.minX)));
        maxElevation = Math.max(maxElevation, rampT * (box.rampElevation ?? 0.006));
      }
      continue;
    }

    const closestX = Math.max(box.minX, Math.min(resX, box.maxX));
    const closestZ = Math.max(box.minZ, Math.min(resZ, box.maxZ));
    const dx = resX - closestX;
    const dz = resZ - closestZ;
    const distSq = dx * dx + dz * dz;

    if (distSq < robotRadius * robotRadius) {
      collided = true;
      const dist = Math.sqrt(distSq);
      if (dist > 0.0001) {
        const overlap = robotRadius - dist;
        resX += (dx / dist) * overlap;
        resZ += (dz / dist) * overlap;
      } else {
        const dL = resX - box.minX;
        const dR = box.maxX - resX;
        const dB = resZ - box.minZ;
        const dF = box.maxZ - resZ;
        const minVal = Math.min(dL, dR, dB, dF);
        if (minVal === dL) resX = box.minX - robotRadius;
        else if (minVal === dR) resX = box.maxX + robotRadius;
        else if (minVal === dB) resZ = box.minZ - robotRadius;
        else resZ = box.maxZ + robotRadius;
      }
    }
  }

  return { x: resX, z: resZ, elevationY: maxElevation, hasCollision: collided };
}

export const Cozmo3DWorldMap: React.FC<Cozmo3DWorldMapProps> = ({
  robot,
  anchors,
  obstacles,
  blocks = [],
  path = [],
  onPointClick,
  onAnchorClick,
  onBlockClick,
  onSimulateDock,
  onSpawnBlock,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [cameraMode, setCameraMode] = useState<'free' | 'follow' | 'top'>('free');
  const [isLoadingModel, setIsLoadingModel] = useState<boolean>(true);
  const isSimulatingDock = Boolean(path && path.length > 1);
  const [isPlacingBlock, setIsPlacingBlock] = useState<boolean>(false);

  // References for live rendering
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cozmoModelRef = useRef<THREE.Group | null>(null);
  const cozmoBodyMeshRef = useRef<THREE.Group | null>(null);
  const chargerModelTemplateRef = useRef<THREE.Group | null>(null);
  const [chargerModelLoaded, setChargerModelLoaded] = useState<boolean>(false);

  const anchorsGroupRef = useRef<THREE.Group | null>(null);
  const obstaclesGroupRef = useRef<THREE.Group | null>(null);
  const blocksGroupRef = useRef<THREE.Group | null>(null);
  const pathGroupRef = useRef<THREE.Group | null>(null);
  const trailLineRef = useRef<THREE.Line | null>(null);
  const groundPlaneRef = useRef<THREE.Mesh | null>(null);

  const robotTargetPos = useRef({ x: 0, z: 0, rotY: 0 });
  const robotCurrentPos = useRef({ x: 0, z: 0, rotY: 0 });
  const cameraModeRef = useRef<'free' | 'follow' | 'top'>('free');
  const trailPointsRef = useRef<THREE.Vector3[]>([]);
  const collidersRef = useRef<SceneCollider[]>([]);

  // Update dynamic rigid-body colliders based on anchors, blocks, and obstacles
  useEffect(() => {
    const list: SceneCollider[] = [];

    // 1. Charger Station U-Wall Colliders & Ramp Bed
    const charger = anchors.find(
      (a) => a.label.toLowerCase().includes('charger') || a.label.toLowerCase().includes('dock')
    );
    if (charger) {
      const cx = (charger.x ?? -300) / 1000;
      const cz = -(charger.y ?? 0) / 1000;

      // Back Wall Collider (prevents driving out through rear)
      list.push({
        id: 'charger_back_wall',
        minX: cx + 0.016,
        maxX: cx + 0.055,
        minZ: cz - 0.046,
        maxZ: cz + 0.046,
      });

      // Left Flank Guide Rail Collider
      list.push({
        id: 'charger_left_rail',
        minX: cx - 0.022,
        maxX: cx + 0.016,
        minZ: cz + 0.030,
        maxZ: cz + 0.046,
      });

      // Right Flank Guide Rail Collider
      list.push({
        id: 'charger_right_rail',
        minX: cx - 0.022,
        maxX: cx + 0.016,
        minZ: cz - 0.046,
        maxZ: cz - 0.030,
      });

      // Ramp Bed Collider (smoothly elevates Cozmo as it enters from -X to +X)
      list.push({
        id: 'charger_ramp_bed',
        minX: cx - 0.038,
        maxX: cx + 0.016,
        minZ: cz - 0.028,
        maxZ: cz + 0.028,
        isRamp: true,
        rampElevation: 0.006,
      });
    }

    // 2. Light Cubes / Spawned Blocks Colliders (44mm x 44mm cubes)
    blocks.forEach((b) => {
      const bx = b.x / 1000;
      const bz = -b.y / 1000;
      const halfSize = ((b.radius ?? 22.0) * 1.0) / 1000;
      list.push({
        id: `block_${b.id}`,
        minX: bx - halfSize,
        maxX: bx + halfSize,
        minZ: bz - halfSize,
        maxZ: bz + halfSize,
      });
    });

    // 3. Unnamed Obstacles
    obstacles.forEach((obs, idx) => {
      const ox = obs.x / 1000;
      const oz = -obs.y / 1000;
      const r = (obs.radius ?? 25.0) / 1000;
      list.push({
        id: `obstacle_${idx}`,
        minX: ox - r,
        maxX: ox + r,
        minZ: oz - r,
        maxZ: oz + r,
      });
    });

    collidersRef.current = list;
  }, [anchors, blocks, obstacles]);

  // Synchronize cameraMode and handle Top / Follow instant positioning
  useEffect(() => {
    cameraModeRef.current = cameraMode;
    const controls = controlsRef.current;
    const camera = cameraRef.current;
    const cozmo = cozmoModelRef.current;
    if (!controls || !camera) return;

    if (cameraMode === 'top') {
      const targetX = cozmo ? cozmo.position.x : 0;
      const targetZ = cozmo ? cozmo.position.z : 0;
      camera.position.set(targetX, 3.2, targetZ + 0.001);
      controls.target.set(targetX, 0, targetZ);
      controls.update();
    } else if (cameraMode === 'follow') {
      const cur = robotCurrentPos.current;
      const followDist = 0.60;
      const followHeight = 0.32;
      const camX = cur.x - Math.cos(cur.rotY) * followDist;
      const camZ = cur.z + Math.sin(cur.rotY) * followDist;
      camera.position.set(camX, followHeight, camZ);
      controls.target.set(cur.x, 0.04, cur.z);
      controls.update();
    }
  }, [cameraMode]);

  // Convert telemetry mm to 3D world meters
  useEffect(() => {
    const xMeters = (robot.x || 0) / 1000;
    const zMeters = -(robot.y || 0) / 1000;
    const thetaRad = THREE.MathUtils.degToRad(robot.theta_deg || 0);

    robotTargetPos.current = {
      x: xMeters,
      z: zMeters,
      rotY: thetaRad,
    };
  }, [robot]);

  // Trigger Autonomous Docking Simulation along Bidirectional A* Path (directly invokes server simulation)
  const handleTriggerDockSimulation = useCallback(() => {
    if (onSimulateDock) {
      onSimulateDock();
    }
  }, [onSimulateDock]);

  // Initialize Three.js Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060913);
    scene.fog = new THREE.FogExp2(0x060913, 0.26);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.01,
      100
    );
    camera.position.set(0.70, 0.80, 1.05);
    cameraRef.current = camera;

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance',
      alpha: true,
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02; // Don't dip below floor
    controls.minDistance = 0.15;
    controls.maxDistance = 25.0;
    controls.target.set(0, 0.04, 0);
    controls.update();
    controlsRef.current = controls;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xd6e8ff, 1.5);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    keyLight.position.set(2.5, 4.5, 3.0);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.1;
    keyLight.shadow.camera.far = 15;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x00f0ff, 1.1);
    fillLight.position.set(-3.0, 2.5, -2.0);
    scene.add(fillLight);

    const rimLight = new THREE.PointLight(0xa855f7, 2.0, 8);
    rimLight.position.set(0, 2.0, -2.0);
    scene.add(rimLight);

    // 6. Ground Grid & Neon Hex Floor
    const gridHelper = new THREE.GridHelper(20, 100, 0x00f0ff, 0x1e293b);
    gridHelper.position.y = 0.0001;
    scene.add(gridHelper);

    const groundGeo = new THREE.PlaneGeometry(30, 30);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x050811,
      roughness: 0.85,
      metalness: 0.15,
    });
    const groundPlane = new THREE.Mesh(groundGeo, groundMat);
    groundPlane.rotation.x = -Math.PI / 2;
    groundPlane.receiveShadow = true;
    scene.add(groundPlane);
    groundPlaneRef.current = groundPlane;

    // Real-time breadcrumb trail line
    const trailMat = new THREE.LineBasicMaterial({
      color: 0x00f0ff,
      linewidth: 2,
      transparent: true,
      opacity: 0.85,
    });
    const trailGeo = new THREE.BufferGeometry();
    const trailLine = new THREE.Line(trailGeo, trailMat);
    scene.add(trailLine);
    trailLineRef.current = trailLine;

    // Groups for Dynamic Objects
    const anchorsGroup = new THREE.Group();
    scene.add(anchorsGroup);
    anchorsGroupRef.current = anchorsGroup;

    const obstaclesGroup = new THREE.Group();
    scene.add(obstaclesGroup);
    obstaclesGroupRef.current = obstaclesGroup;

    const blocksGroup = new THREE.Group();
    scene.add(blocksGroup);
    blocksGroupRef.current = blocksGroup;

    const pathGroup = new THREE.Group();
    scene.add(pathGroup);
    pathGroupRef.current = pathGroup;

    // 7. Load Repaired Cozmo 3D Model (.mtl + .obj)
    const mtlLoader = new MTLLoader();
    mtlLoader.setPath('/models/cozmo/');
    mtlLoader.setResourcePath('/models/cozmo/');

    mtlLoader.load(
      '3DModel.mtl?v=repaired_face1',
      (materials) => {
        materials.preload();
        const objLoader = new OBJLoader();
        objLoader.setMaterials(materials);
        objLoader.setPath('/models/cozmo/');

        objLoader.load(
          '3DModel.obj?v=repaired_face1',
          (object) => {
            object.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                if (child.material) {
                  if (Array.isArray(child.material)) {
                    child.material.forEach((m) => {
                      m.side = THREE.DoubleSide;
                      m.roughness = 0.65;
                      m.metalness = 0.15;
                    });
                  } else {
                    child.material.side = THREE.DoubleSide;
                    child.material.roughness = 0.65;
                    child.material.metalness = 0.15;
                  }
                }
              }
            });

            // Rotate Cozmo model 180 degrees to align forward movement
            object.rotation.y = Math.PI / 2;

            // Parent container for world navigation (X, Z position + Y heading)
            const cozmoContainer = new THREE.Group();

            // Inner body container for procedural micro-physics (suspension rumble, tilt, roll)
            const cozmoBody = new THREE.Group();
            cozmoBody.add(object);

            cozmoContainer.add(cozmoBody);
            cozmoBodyMeshRef.current = cozmoBody;

            // Glowing Ground Shadow
            const shadowGeo = new THREE.PlaneGeometry(0.14, 0.14);
            const canvas = document.createElement('canvas');
            canvas.width = 64;
            canvas.height = 64;
            const ctx = canvas.getContext('2d');
            if (ctx) {
              const grad = ctx.createRadialGradient(32, 32, 4, 32, 32, 32);
              grad.addColorStop(0, 'rgba(0, 240, 255, 0.6)');
              grad.addColorStop(0.4, 'rgba(0, 150, 255, 0.3)');
              grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
              ctx.fillStyle = grad;
              ctx.fillRect(0, 0, 64, 64);
            }
            const shadowTex = new THREE.CanvasTexture(canvas);
            const shadowMat = new THREE.MeshBasicMaterial({
              map: shadowTex,
              transparent: true,
              opacity: 0.7,
              depthWrite: false,
            });
            const groundHalo = new THREE.Mesh(shadowGeo, shadowMat);
            groundHalo.rotation.x = -Math.PI / 2;
            groundHalo.position.y = 0.003;
            cozmoContainer.add(groundHalo);

            scene.add(cozmoContainer);
            cozmoModelRef.current = cozmoContainer;
            setIsLoadingModel(false);
          },
          undefined,
          (err) => {
            console.error('Error loading 3DModel.obj:', err);
            setIsLoadingModel(false);
          }
        );
      },
      undefined,
      (err) => {
        console.error('Error loading 3DModel.mtl:', err);
        setIsLoadingModel(false);
      }
    );

    // 7b. Load Charger 3D Model (.mtl + .obj from 3DModel/Models/charger/OBJ)
    const chargerMtlLoader = new MTLLoader();
    chargerMtlLoader.setPath('/models/charger/');
    chargerMtlLoader.setResourcePath('/models/charger/');

    chargerMtlLoader.load(
      '3DModel.mtl?v=charger_v1',
      (materials) => {
        materials.preload();
        const chargerObjLoader = new OBJLoader();
        chargerObjLoader.setMaterials(materials);
        chargerObjLoader.setPath('/models/charger/');

        chargerObjLoader.load(
          '3DModel.obj?v=charger_v1',
          (chargerObj) => {
            chargerObj.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                if (child.material) {
                  const mats = Array.isArray(child.material) ? child.material : [child.material];
                  mats.forEach((m) => {
                    m.side = THREE.DoubleSide;
                    m.roughness = 0.55;
                    m.metalness = 0.25;
                  });
                }
              }
            });
            chargerModelTemplateRef.current = chargerObj;
            setChargerModelLoaded(true);
          },
          undefined,
          (err) => console.error('Error loading charger 3DModel.obj:', err)
        );
      },
      undefined,
      (err) => console.error('Error loading charger 3DModel.mtl:', err)
    );

    // 8. Animation & Render Loop with Autonomous Simulation & Micro-Physics
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = Math.min(0.05, clock.getDelta());
      const time = clock.getElapsedTime();

      // Breadcrumb trail point behind Cozmo
      const p = new THREE.Vector3(robotTargetPos.current.x, 0.005, robotTargetPos.current.z);
      const last = trailPointsRef.current[trailPointsRef.current.length - 1];
      if (!last || last.distanceTo(p) > 0.02) {
        trailPointsRef.current.push(p);
        if (trailPointsRef.current.length > 300) trailPointsRef.current.shift();
        if (trailLineRef.current) trailLineRef.current.geometry.setFromPoints(trailPointsRef.current);
      }

      // Smooth lerp robot position & rotation
      const cozmo = cozmoModelRef.current;
      const cozmoBody = cozmoBodyMeshRef.current;
      if (cozmo) {
        const target = robotTargetPos.current;
        const cur = robotCurrentPos.current;

        const prevX = cur.x;
        const prevZ = cur.z;

        cur.x += (target.x - cur.x) * Math.min(1, delta * 22);
        cur.z += (target.z - cur.z) * Math.min(1, delta * 22);

        let diffRot = target.rotY - cur.rotY;
        while (diffRot < -Math.PI) diffRot += Math.PI * 2;
        while (diffRot > Math.PI) diffRot -= Math.PI * 2;
        cur.rotY += diffRot * Math.min(1, delta * 24);

        // Continuous Rigid-Body Collision Resolution & Dynamic Ramp Elevation
        const robotRadiusMeters = 0.032; // 32mm physical collision radius
        const collision = solveRigidBodyCollisions(cur.x, cur.z, robotRadiusMeters, collidersRef.current);
        cur.x = collision.x;
        cur.z = collision.z;

        cozmo.position.set(cur.x, collision.elevationY, cur.z);
        cozmo.rotation.y = cur.rotY;

        // Procedural Vehicle Motion & Micro-Physics
        if (cozmoBody) {
          const moveDelta = Math.hypot(cur.x - prevX, cur.z - prevZ);
          const currentSpeed = delta > 0 ? moveDelta / delta : 0;
          const isMoving = currentSpeed > 0.012 || Math.abs(diffRot) > 0.03;

          if (isMoving) {
            const treadFreq = 42;
            const vibrationY = Math.sin(time * treadFreq) * 0.00065;
            const vibrationRoll = Math.sin(time * (treadFreq * 0.7)) * 0.008;
            const pitch = -Math.min(0.045, currentSpeed * 0.06);
            const turnRoll = Math.max(-0.06, Math.min(0.06, diffRot * 0.35));

            cozmoBody.position.y = vibrationY;
            cozmoBody.rotation.x = pitch;
            cozmoBody.rotation.z = turnRoll + vibrationRoll;
          } else {
            const idleHover = Math.sin(time * 2.2) * 0.0003;
            cozmoBody.position.y = idleHover;
            cozmoBody.rotation.x = THREE.MathUtils.lerp(cozmoBody.rotation.x, 0, delta * 8);
            cozmoBody.rotation.z = THREE.MathUtils.lerp(cozmoBody.rotation.z, 0, delta * 8);
          }
        }

        // Camera Follow Mode logic (Over-the-shoulder third-person camera)
        if (cameraModeRef.current === 'follow' && controlsRef.current && cameraRef.current) {
          const followDist = 0.60;
          const followHeight = 0.32;
          // Position camera directly behind Cozmo's heading vector (+X forward)
          const camX = cur.x - Math.cos(cur.rotY) * followDist;
          const camZ = cur.z + Math.sin(cur.rotY) * followDist;

          cameraRef.current.position.lerp(new THREE.Vector3(camX, followHeight, camZ), 0.12);
          controlsRef.current.target.lerp(new THREE.Vector3(cur.x, 0.04, cur.z), 0.12);
        }
      }

      // Pulse effects on anchors & blocks
      if (anchorsGroupRef.current) {
        anchorsGroupRef.current.children.forEach((anchorObj) => {
          const halo = anchorObj.getObjectByName('halo');
          if (halo) {
            const scale = 1 + Math.sin(time * 3) * 0.12;
            halo.scale.set(scale, scale, scale);
          }
        });
      }

      if (blocksGroupRef.current) {
        blocksGroupRef.current.children.forEach((blkObj) => {
          const halo = blkObj.getObjectByName('clearance_ring');
          if (halo) {
            const scale = 1 + Math.sin(time * 2.5) * 0.04;
            halo.scale.set(scale, scale, scale);
          }
          const leds = blkObj.getObjectByName('led_group');
          if (leds) {
            leds.children.forEach((led) => {
              if (led instanceof THREE.Mesh && led.material instanceof THREE.MeshStandardMaterial) {
                led.material.emissiveIntensity = 0.8 + Math.sin(time * 4) * 0.4;
              }
            });
          }
        });
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    // 9. Resize Handler
    const handleResize = () => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update Visual Anchors (Charger / Ground Landmarks)
  useEffect(() => {
    const group = anchorsGroupRef.current;
    if (!group) return;

    while (group.children.length > 0) {
      group.remove(group.children[0]);
    }

    anchors.forEach((anchor) => {
      const wx = (anchor.x || 0) / 1000;
      const wz = -(anchor.y || 0) / 1000;

      const anchorObj = new THREE.Group();
      anchorObj.position.set(wx, 0, wz);
      anchorObj.userData = { anchor };

      const isCharger = anchor.label.toLowerCase().includes('charger') || anchor.label.toLowerCase().includes('dock');
      const baseColor = isCharger ? 0x10b981 : 0x00d4ff;

      if (isCharger) {
        if (chargerModelTemplateRef.current) {
          const chargerMesh = chargerModelTemplateRef.current.clone(true);
          // Flipped 180 degrees so the entrance ramp faces Cozmo and the approach path
          chargerMesh.rotation.y = -Math.PI / 2;
          chargerMesh.position.set(0, 0, 0);
          anchorObj.add(chargerMesh);
        } else {
          // Procedural fallback dock cradle
          const dockGroup = new THREE.Group();
          const baseGeo = new THREE.BoxGeometry(0.085, 0.008, 0.095);
          const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.5, metalness: 0.7 });
          const dockBase = new THREE.Mesh(baseGeo, baseMat);
          dockBase.position.y = 0.004;
          dockGroup.add(dockBase);

          const backGeo = new THREE.BoxGeometry(0.085, 0.038, 0.014);
          const backWall = new THREE.Mesh(backGeo, baseMat);
          backWall.position.set(0, 0.022, 0.040);
          dockGroup.add(backWall);

          dockGroup.rotation.y = 0; // Flipped to match
          anchorObj.add(dockGroup);
        }

        // U-Shape Safety Barrier Clearance Boundary (Back & Side Walls)
        // Entrance is on -X (left), Back wall is on +X (right)
        const uPts: THREE.Vector3[] = [
          new THREE.Vector3(-0.018, 0.003, -0.052),   // Left flank front
          new THREE.Vector3(0.052, 0.003, -0.052),    // Right rear corner
          new THREE.Vector3(0.052, 0.003, 0.052),     // Left rear corner
          new THREE.Vector3(-0.018, 0.003, 0.052),    // Right flank front
        ];
        const uGeo = new THREE.BufferGeometry().setFromPoints(uPts);
        const uMat = new THREE.LineDashedMaterial({
          color: 0x10b981,
          dashSize: 0.014,
          gapSize: 0.008,
          linewidth: 2,
          transparent: true,
          opacity: 0.9,
        });
        const uBarrierLine = new THREE.Line(uGeo, uMat);
        uBarrierLine.computeLineDistances();
        anchorObj.add(uBarrierLine);

        // Docking Guidance Halo Ring (Inner charging cradle)
        const ringGeo = new THREE.RingGeometry(0.040, 0.048, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0x10b981,
          transparent: true,
          opacity: 0.75,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.003;
        ring.name = 'halo';
        anchorObj.add(ring);
      } else {
        // Floating Landmark Diamond
        const diamondGeo = new THREE.OctahedronGeometry(0.025, 0);
        const diamondMat = new THREE.MeshStandardMaterial({
          color: baseColor,
          emissive: baseColor,
          emissiveIntensity: 0.6,
          roughness: 0.2,
          metalness: 0.8,
        });
        const diamond = new THREE.Mesh(diamondGeo, diamondMat);
        diamond.name = 'diamond';
        diamond.position.y = 0.08;
        diamond.castShadow = true;
        anchorObj.add(diamond);

        const stemGeo = new THREE.CylinderGeometry(0.002, 0.002, 0.08, 8);
        const stemMat = new THREE.MeshBasicMaterial({
          color: baseColor,
          transparent: true,
          opacity: 0.5,
        });
        const stem = new THREE.Mesh(stemGeo, stemMat);
        stem.position.y = 0.04;
        anchorObj.add(stem);
      }

      // Billboard Text Label Sprite
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'rgba(10, 16, 26, 0.88)';
        ctx.roundRect(4, 4, 248, 56, 12);
        ctx.fill();
        ctx.strokeStyle = isCharger ? (anchor.is_locked ? '#f59e0b' : '#10b981') : '#00d4ff';
        ctx.lineWidth = 3;
        ctx.roundRect(4, 4, 248, 56, 12);
        ctx.stroke();

        ctx.font = 'bold 18px monospace';
        ctx.fillStyle = anchor.is_locked ? '#fcd34d' : '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const displayLabel = isCharger
          ? (anchor.is_locked ? 'CHARGER [LOCKED]' : 'CHARGER DOCK')
          : anchor.label.toUpperCase();
        ctx.fillText(displayLabel, 128, 32);
      }
      const labelTex = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({ map: labelTex, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.position.set(0, isCharger ? 0.09 : 0.14, 0);
      sprite.scale.set(0.18, 0.045, 1);
      anchorObj.add(sprite);

      group.add(anchorObj);
    });
  }, [anchors, chargerModelLoaded]);

  // Update 3D Cozmo Light Blocks (Light Cubes) with 5cm Safety Clearance Zones
  useEffect(() => {
    const group = blocksGroupRef.current;
    if (!group) return;

    while (group.children.length > 0) {
      group.remove(group.children[0]);
    }

    blocks.forEach((blk) => {
      const wx = (blk.x || 0) / 1000;
      const wz = -(blk.y || 0) / 1000;
      const cubeSizeM = 0.044; // 44mm physical cube
      const clearanceRadiusM = ((blk.radius || 25) + (blk.clearance_mm || 50)) / 1000; // ~0.075m (7.5cm from center, giving 5cm clearance from edge)

      const blkObj = new THREE.Group();
      blkObj.position.set(wx, 0, wz);
      blkObj.userData = { block: blk };

      // 1. Semi-transparent Safety Clearance Boundary Cylinder & Base Ring
      const clearCylGeo = new THREE.CylinderGeometry(clearanceRadiusM, clearanceRadiusM, 0.048, 32, 1, true);
      const clearCylMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.12,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      const clearCyl = new THREE.Mesh(clearCylGeo, clearCylMat);
      clearCyl.position.y = 0.024;
      blkObj.add(clearCyl);

      // Floor Warning Dashed Ring
      const ringGeo = new THREE.RingGeometry(clearanceRadiusM - 0.003, clearanceRadiusM, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.75,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.002;
      ring.name = 'clearance_ring';
      blkObj.add(ring);

      // 2. Cozmo Light Cube Physical Body (Glossy Dark Enclosure with White Corners)
      const cubeGeo = new THREE.BoxGeometry(cubeSizeM, cubeSizeM, cubeSizeM);
      const cubeMat = new THREE.MeshStandardMaterial({
        color: 0x181e29,
        roughness: 0.35,
        metalness: 0.5,
      });
      const cubeMesh = new THREE.Mesh(cubeGeo, cubeMat);
      cubeMesh.position.y = cubeSizeM / 2;
      cubeMesh.castShadow = true;
      cubeMesh.receiveShadow = true;
      blkObj.add(cubeMesh);

      // Cube Corner Glowing LEDs
      const ledGroup = new THREE.Group();
      ledGroup.name = 'led_group';
      const ledGeo = new THREE.BoxGeometry(0.008, 0.008, 0.008);
      const ledMat = new THREE.MeshStandardMaterial({
        color: 0x00f0ff,
        emissive: 0x00f0ff,
        emissiveIntensity: 0.9,
      });
      const c = cubeSizeM / 2 - 0.004;
      [
        [-c, c, -c],
        [c, c, -c],
        [-c, c, c],
        [c, c, c],
      ].forEach(([lx, ly, lz]) => {
        const led = new THREE.Mesh(ledGeo, ledMat);
        led.position.set(lx, ly + cubeSizeM / 2, lz);
        ledGroup.add(led);
      });
      blkObj.add(ledGroup);

      // Top Billboard Label (Cozmo Light Cube Name + 5cm Clearance Warning)
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
        ctx.roundRect(4, 4, 248, 56, 12);
        ctx.fill();
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.roundRect(4, 4, 248, 56, 12);
        ctx.stroke();

        ctx.font = 'bold 18px monospace';
        ctx.fillStyle = '#f87171';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${blk.label.toUpperCase()} (5cm Buffer)`, 128, 32);
      }
      const labelTex = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({ map: labelTex, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.position.set(0, 0.095, 0);
      sprite.scale.set(0.19, 0.048, 1);
      blkObj.add(sprite);

      group.add(blkObj);
    });
  }, [blocks]);

  // Update Transient Obstacles
  useEffect(() => {
    const group = obstaclesGroupRef.current;
    if (!group) return;

    while (group.children.length > 0) {
      group.remove(group.children[0]);
    }

    obstacles.forEach((obs) => {
      const wx = (obs.x || 0) / 1000;
      const wz = -(obs.y || 0) / 1000;
      const radiusM = Math.max(0.03, (obs.radius || 40) / 1000);

      const obsObj = new THREE.Group();
      obsObj.position.set(wx, 0, wz);

      const cylGeo = new THREE.CylinderGeometry(radiusM, radiusM, 0.08, 24);
      const cylMat = new THREE.MeshStandardMaterial({
        color: 0xef4444,
        emissive: 0xef4444,
        emissiveIntensity: 0.4,
        transparent: true,
        opacity: 0.35,
        roughness: 0.3,
      });
      const cyl = new THREE.Mesh(cylGeo, cylMat);
      cyl.position.y = 0.04;
      obsObj.add(cyl);

      const ringGeo = new THREE.RingGeometry(radiusM - 0.005, radiusM + 0.005, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xff3b30,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.081;
      obsObj.add(ring);

      group.add(obsObj);
    });
  }, [obstacles]);

  // Update Planned Bidirectional A* Path in 3D Scene
  useEffect(() => {
    const pathGroup = pathGroupRef.current;
    if (!pathGroup) return;

    while (pathGroup.children.length > 0) {
      pathGroup.remove(pathGroup.children[0]);
    }

    if (path && path.length > 1) {
      const pts = path.map(([wx, wy]) => new THREE.Vector3(wx / 1000, 0.006, -wy / 1000));
      const curve = new THREE.CatmullRomCurve3(pts);
      const smoothPts = curve.getPoints(pts.length * 6);

      // Glowing Neon Path Tube
      const tubeGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(smoothPts), 120, 0.0035, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: 0x00ff88,
        transparent: true,
        opacity: 0.85,
      });
      const tube = new THREE.Mesh(tubeGeo, tubeMat);
      pathGroup.add(tube);

      // Waypoint floor rings
      pts.forEach((pt) => {
        const wpRingGeo = new THREE.RingGeometry(0.010, 0.014, 16);
        const wpRingMat = new THREE.MeshBasicMaterial({
          color: 0xa855f7,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.7,
        });
        const wpRing = new THREE.Mesh(wpRingGeo, wpRingMat);
        wpRing.rotation.x = -Math.PI / 2;
        wpRing.position.set(pt.x, 0.004, pt.z);
        pathGroup.add(wpRing);
      });
    }
  }, [path]);

  // Pointer Down: Drive or Click Object / Spawn Block
  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const container = containerRef.current;
      const camera = cameraRef.current;
      const ground = groundPlaneRef.current;
      const blocksGroup = blocksGroupRef.current;
      const anchorsGroup = anchorsGroupRef.current;
      if (!container || !camera || !ground) return;

      const rect = container.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      // Check block click first
      if (blocksGroup && onBlockClick) {
        const blockIntersects = raycaster.intersectObjects(blocksGroup.children, true);
        if (blockIntersects.length > 0) {
          let topObj: THREE.Object3D | null = blockIntersects[0].object;
          while (topObj && !topObj.userData.block && topObj.parent !== blocksGroup) {
            topObj = topObj.parent;
          }
          if (topObj && topObj.userData.block) {
            onBlockClick(topObj.userData.block);
            return;
          }
        }
      }

      // Check anchor click
      if (anchorsGroup && onAnchorClick) {
        const anchorIntersects = raycaster.intersectObjects(anchorsGroup.children, true);
        if (anchorIntersects.length > 0) {
          let topObj: THREE.Object3D | null = anchorIntersects[0].object;
          while (topObj && !topObj.userData.anchor && topObj.parent !== anchorsGroup) {
            topObj = topObj.parent;
          }
          if (topObj && topObj.userData.anchor) {
            onAnchorClick(topObj.userData.anchor);
            return;
          }
        }
      }

      // Check ground click
      const groundIntersects = raycaster.intersectObject(ground);
      if (groundIntersects.length > 0) {
        const pt = groundIntersects[0].point;
        const worldX_mm = Math.round(pt.x * 1000);
        const worldY_mm = Math.round(-pt.z * 1000);

        if (isPlacingBlock && onSpawnBlock) {
          onSpawnBlock(worldX_mm, worldY_mm);
          setIsPlacingBlock(false);
          return;
        }

        if (onPointClick) {
          onPointClick(worldX_mm, worldY_mm);
        }
      }
    },
    [onPointClick, onAnchorClick, onBlockClick, isPlacingBlock, onSpawnBlock]
  );

  // Recenter Camera
  const handleRecenter = useCallback(() => {
    const controls = controlsRef.current;
    const camera = cameraRef.current;
    const cozmo = cozmoModelRef.current;
    if (!controls || !camera) return;

    const targetX = cozmo ? cozmo.position.x : 0;
    const targetZ = cozmo ? cozmo.position.z : 0;

    controls.target.set(targetX, 0.04, targetZ);
    camera.position.set(targetX + 0.6, 0.7, targetZ + 0.8);
    controls.update();
    setCameraMode('free');
  }, []);

  return (
    <div className={`relative w-full h-full min-h-[460px] overflow-hidden select-none ${className}`}>
      {/* 3D WebGL Canvas Container */}
      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        className={`w-full h-full cursor-crosshair active:cursor-grabbing ${
          isPlacingBlock ? 'cursor-copy' : ''
        }`}
      />

      {/* Loading Overlay */}
      {isLoadingModel && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md flex flex-col items-center justify-center gap-3 z-20 pointer-events-none">
          <div className="w-10 h-10 border-3 border-cyan-400/20 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-xs font-mono text-cyan-300 tracking-wider">LOADING COZMO 3D SIMULATION...</span>
        </div>
      )}

      {/* Top Left Camera Modes (Dock Style) */}
      <div className="absolute top-3 left-3 z-10 dock-nav-bar">
        <button
          onClick={() => setCameraMode('free')}
          className={`dock-btn ${cameraMode === 'free' ? 'dock-btn-active' : ''}`}
          title="Free 360 Orbit Camera"
        >
          Free Orbit
        </button>
        <button
          onClick={() => setCameraMode('follow')}
          className={`dock-btn ${cameraMode === 'follow' ? 'dock-btn-active' : ''}`}
          title="Follow Behind Cozmo"
        >
          Follow Cam
        </button>
        <button
          onClick={() => setCameraMode('top')}
          className={`dock-btn ${cameraMode === 'top' ? 'dock-btn-active' : ''}`}
          title="Top-Down Bird's Eye View"
        >
          Top-Down
        </button>
      </div>

      {/* Top Right Simulation & Controls (Dock Style) */}
      <div className="absolute top-3 right-3 z-10 dock-nav-bar">
        {/* Spawn Block Button */}
        <button
          onClick={() => setIsPlacingBlock(!isPlacingBlock)}
          className={`dock-btn ${
            isPlacingBlock
              ? 'dock-btn-active animate-pulse'
              : ''
          }`}
          title="Click to place a Cozmo Light Cube on the floor plane"
        >
          <span>{isPlacingBlock ? 'Placing...' : 'Spawn Cube'}</span>
        </button>

        {/* 2-Way A* Docking Simulation Button */}
        <button
          onClick={handleTriggerDockSimulation}
          className={`dock-btn ${
            isSimulatingDock
              ? 'dock-btn-amber dock-btn-active animate-pulse'
              : 'dock-btn-emerald'
          }`}
          title="Simulate Autonomous Docking using Two-Way (Bidirectional) A* with 5cm block clearance"
        >
          <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          <span>{isSimulatingDock ? 'Docking...' : 'Simulate Dock'}</span>
        </button>

        {/* Recenter Button */}
        <button
          onClick={handleRecenter}
          className="dock-btn"
          title="Recenter Camera on Robot"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="16" />
            <line x1="8" y1="12" x2="16" y2="12" />
          </svg>
          Recenter
        </button>
      </div>

      {/* Bottom HUD Overlay */}
      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between pointer-events-none z-10">
        <div className="bg-slate-900/85 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-white/10 text-[11px] font-mono text-slate-300 flex items-center gap-3 shadow-xl">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Pose: ({(robot.x / 10).toFixed(1)}, {(robot.y / 10).toFixed(1)})cm | {robot.theta_deg.toFixed(0)}°</span>
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-amber-300 font-semibold">5cm Block Safety Margin Active</span>
          {isSimulatingDock && (
            <>
              <span className="text-slate-500">|</span>
              <span className="text-cyan-300 animate-pulse">2-Way A* Dock Active</span>
            </>
          )}
        </div>

        <div className="bg-slate-900/85 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-[11px] font-mono text-cyan-300 shadow-xl">
          {blocks.length} Cubes Loaded (5cm Buffer)
        </div>
      </div>
    </div>
  );
};

export default Cozmo3DWorldMap;
