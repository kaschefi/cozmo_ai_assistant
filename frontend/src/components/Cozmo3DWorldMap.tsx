import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { RobotPose, VisualAnchorData, ObstacleData } from './SemanticGridMap';

export interface Cozmo3DWorldMapProps {
  robot: RobotPose;
  anchors: VisualAnchorData[];
  obstacles: ObstacleData[];
  path?: number[][];
  onPointClick?: (worldX: number, worldY: number) => void;
  onAnchorClick?: (anchor: VisualAnchorData) => void;
  className?: string;
}

export const Cozmo3DWorldMap: React.FC<Cozmo3DWorldMapProps> = ({
  robot,
  anchors,
  obstacles,
  path = [],
  onPointClick,
  onAnchorClick,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [cameraMode, setCameraMode] = useState<'free' | 'follow' | 'top' | 'iso'>('free');
  const [isLoadingModel, setIsLoadingModel] = useState<boolean>(true);
  const [isDemoDriving, setIsDemoDriving] = useState<boolean>(false);
  const [demoDistance, setDemoDistance] = useState<number>(0);

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
  const pathLineRef = useRef<THREE.Line | null>(null);
  const trailLineRef = useRef<THREE.Line | null>(null);
  const headlightRef = useRef<THREE.SpotLight | null>(null);
  const headlightTargetRef = useRef<THREE.Object3D | null>(null);
  const groundPlaneRef = useRef<THREE.Mesh | null>(null);

  const robotTargetPos = useRef({ x: 0, z: 0, rotY: 0 });
  const robotCurrentPos = useRef({ x: 0, z: 0, rotY: 0 });
  const cameraModeRef = useRef<'free' | 'follow' | 'top' | 'iso'>('free');
  const trailPointsRef = useRef<THREE.Vector3[]>([]);

  // Demo Drive Simulation state ref
  const demoDriveRef = useRef<{
    active: boolean;
    startX: number;
    startZ: number;
    startHeading: number;
    distanceDriven: number;
    targetDistance: number;
    speed: number;
  }>({
    active: false,
    startX: 0,
    startZ: 0,
    startHeading: 0,
    distanceDriven: 0,
    targetDistance: 10.0,
    speed: 0.9,
  });

  // Update camera mode ref
  useEffect(() => {
    cameraModeRef.current = cameraMode;
    const controls = controlsRef.current;
    const camera = cameraRef.current;
    const cozmo = cozmoModelRef.current;
    if (!controls || !camera) return;

    if (cameraMode === 'top') {
      const targetX = cozmo ? cozmo.position.x : 0;
      const targetZ = cozmo ? cozmo.position.z : 0;
      camera.position.set(targetX, 3.0, targetZ + 0.001);
      controls.target.set(targetX, 0, targetZ);
      controls.update();
    } else if (cameraMode === 'iso') {
      const targetX = cozmo ? cozmo.position.x : 0;
      const targetZ = cozmo ? cozmo.position.z : 0;
      camera.position.set(targetX + 1.2, 1.4, targetZ + 1.2);
      controls.target.set(targetX, 0, targetZ);
      controls.update();
    }
  }, [cameraMode]);

  // Convert telemetry mm to 3D world meters (unless demo simulation is overriding)
  useEffect(() => {
    if (demoDriveRef.current.active) return;

    const xMeters = (robot.x || 0) / 1000;
    const zMeters = -(robot.y || 0) / 1000;
    const thetaRad = THREE.MathUtils.degToRad(robot.theta_deg || 0);

    robotTargetPos.current = {
      x: xMeters,
      z: zMeters,
      rotY: thetaRad,
    };
  }, [robot]);

  // Start / Stop 10 Meter Demo Drive
  const handleToggleDemoDrive = useCallback(() => {
    if (demoDriveRef.current.active) {
      demoDriveRef.current.active = false;
      setIsDemoDriving(false);
    } else {
      const current = robotCurrentPos.current;
      demoDriveRef.current = {
        active: true,
        startX: current.x,
        startZ: current.z,
        startHeading: current.rotY,
        distanceDriven: 0,
        targetDistance: 10.0,
        speed: 0.9,
      };
      setIsDemoDriving(true);
      setDemoDistance(0);
    }
  }, []);

  // Initialize Three.js Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060913);
    scene.fog = new THREE.FogExp2(0x060913, 0.28);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.01,
      100
    );
    camera.position.set(0.65, 0.75, 0.95);
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
    const ambientLight = new THREE.AmbientLight(0xd6e8ff, 1.4);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
    keyLight.position.set(2.5, 4.0, 3.0);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.1;
    keyLight.shadow.camera.far = 15;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x00f0ff, 0.9);
    fillLight.position.set(-3.0, 2.0, -2.0);
    scene.add(fillLight);

    const rimLight = new THREE.PointLight(0xa855f7, 1.8, 8);
    rimLight.position.set(0, 1.8, -2.0);
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

    // Planned Path line
    const pathMat = new THREE.LineBasicMaterial({
      color: 0xa855f7,
      linewidth: 3,
      transparent: true,
      opacity: 0.8,
    });
    const pathGeo = new THREE.BufferGeometry();
    const pathLine = new THREE.Line(pathGeo, pathMat);
    scene.add(pathLine);
    pathLineRef.current = pathLine;

    const anchorsGroup = new THREE.Group();
    scene.add(anchorsGroup);
    anchorsGroupRef.current = anchorsGroup;

    const obstaclesGroup = new THREE.Group();
    scene.add(obstaclesGroup);
    obstaclesGroupRef.current = obstaclesGroup;

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

            // Rotate Cozmo model 180 degrees (object.rotation.y = Math.PI / 2)
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

            // Cozmo Headlight Beam (facing forward with Cozmo's rotated front)
            const headlight = new THREE.SpotLight(0xaae8ff, 3.5, 2.5, Math.PI / 4.5, 0.4, 1.2);
            headlight.position.set(-0.04, 0.045, 0);
            headlight.castShadow = true;
            headlight.shadow.bias = -0.001;

            const headlightTarget = new THREE.Object3D();
            headlightTarget.position.set(-1.2, 0.0, 0);
            cozmoContainer.add(headlightTarget);
            headlight.target = headlightTarget;
            cozmoContainer.add(headlight);
            headlightRef.current = headlight;
            headlightTargetRef.current = headlightTarget;

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

    // 8. Animation & Render Loop with Procedural Physics
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = Math.min(0.05, clock.getDelta());
      const time = clock.getElapsedTime();

      // Demo 10m Drive Step
      const demo = demoDriveRef.current;
      if (demo.active) {
        // Drive forward in the direction of heading
        const stepDist = demo.speed * delta;
        demo.distanceDriven += stepDist;
        setDemoDistance(demo.distanceDriven);

        // Turn slightly along a curved 10m path for realistic visual interest
        const turnRate = Math.sin(demo.distanceDriven * 0.8) * 0.25;
        demo.startHeading += turnRate * delta;

        // Move target along heading
        const forwardX = Math.sin(demo.startHeading);
        const forwardZ = Math.cos(demo.startHeading);
        robotTargetPos.current.x += forwardX * stepDist;
        robotTargetPos.current.z += forwardZ * stepDist;
        robotTargetPos.current.rotY = demo.startHeading;

        // Breadcrumbs during demo
        const p = new THREE.Vector3(robotTargetPos.current.x, 0.005, robotTargetPos.current.z);
        const last = trailPointsRef.current[trailPointsRef.current.length - 1];
        if (!last || last.distanceTo(p) > 0.03) {
          trailPointsRef.current.push(p);
          if (trailPointsRef.current.length > 300) trailPointsRef.current.shift();
          if (trailLineRef.current) trailLineRef.current.geometry.setFromPoints(trailPointsRef.current);
        }

        if (demo.distanceDriven >= demo.targetDistance) {
          demo.active = false;
          setIsDemoDriving(false);
        }
      }

      // Smooth lerp robot position & rotation
      const cozmo = cozmoModelRef.current;
      const cozmoBody = cozmoBodyMeshRef.current;
      if (cozmo) {
        const target = robotTargetPos.current;
        const cur = robotCurrentPos.current;

        const prevX = cur.x;
        const prevZ = cur.z;

        cur.x += (target.x - cur.x) * Math.min(1, delta * 14);
        cur.z += (target.z - cur.z) * Math.min(1, delta * 14);

        // Shortest angle rotation lerp
        let diffRot = target.rotY - cur.rotY;
        while (diffRot < -Math.PI) diffRot += Math.PI * 2;
        while (diffRot > Math.PI) diffRot -= Math.PI * 2;
        cur.rotY += diffRot * Math.min(1, delta * 12);

        cozmo.position.set(cur.x, 0, cur.z);
        cozmo.rotation.y = cur.rotY;

        // ==========================================
        // PROCEDURAL VEHICLE MOTION & MICRO-PHYSICS
        // ==========================================
        if (cozmoBody) {
          const moveDelta = Math.hypot(cur.x - prevX, cur.z - prevZ);
          const currentSpeed = delta > 0 ? moveDelta / delta : 0;
          const isMoving = currentSpeed > 0.015 || Math.abs(diffRot) > 0.03;

          if (isMoving) {
            // 1. Traction Tread Vibration: High-frequency chassis vibration
            const treadFreq = 42;
            const vibrationY = Math.sin(time * treadFreq) * 0.00065;
            const vibrationRoll = Math.sin(time * (treadFreq * 0.7)) * 0.008;

            // 2. Acceleration / Inertia Pitch: Front tilts forward on speed
            const pitch = -Math.min(0.045, currentSpeed * 0.06);

            // 3. Banking Roll into turns
            const turnRoll = Math.max(-0.06, Math.min(0.06, diffRot * 0.35));

            cozmoBody.position.y = vibrationY;
            cozmoBody.rotation.x = pitch;
            cozmoBody.rotation.z = turnRoll + vibrationRoll;

            // Pulse headlight intensity with driving power
            if (headlightRef.current) {
              headlightRef.current.intensity = 3.5 + Math.sin(time * 20) * 0.4;
            }
          } else {
            // Idle breathing micro-hover
            const idleHover = Math.sin(time * 2.2) * 0.0003;
            cozmoBody.position.y = idleHover;
            cozmoBody.rotation.x = THREE.MathUtils.lerp(cozmoBody.rotation.x, 0, delta * 8);
            cozmoBody.rotation.z = THREE.MathUtils.lerp(cozmoBody.rotation.z, 0, delta * 8);

            if (headlightRef.current) {
              headlightRef.current.intensity = 3.2;
            }
          }
        }

        // Camera Follow Mode logic
        if (cameraModeRef.current === 'follow' && controlsRef.current && cameraRef.current) {
          const followDist = 0.65;
          const followHeight = 0.40;
          const camX = cur.x - Math.sin(cur.rotY) * followDist;
          const camZ = cur.z - Math.cos(cur.rotY) * followDist;

          cameraRef.current.position.lerp(new THREE.Vector3(camX, followHeight, camZ), 0.09);
          controlsRef.current.target.lerp(new THREE.Vector3(cur.x, 0.05, cur.z), 0.09);
        }
      }

      // Pulse effects on anchors
      if (anchorsGroupRef.current) {
        anchorsGroupRef.current.children.forEach((anchorObj) => {
          const halo = anchorObj.getObjectByName('halo');
          if (halo) {
            const scale = 1 + Math.sin(time * 3) * 0.12;
            halo.scale.set(scale, scale, scale);
          }
          const diamond = anchorObj.getObjectByName('diamond');
          if (diamond) {
            diamond.rotation.y = time * 1.5;
            diamond.position.y = 0.08 + Math.sin(time * 2.5) * 0.015;
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

  // Update Visual Anchors in 3D Scene
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
        // ==========================================
        // DEDICATED 3D CHARGER OBJ MODEL
        // ==========================================
        if (chargerModelTemplateRef.current) {
          const chargerMesh = chargerModelTemplateRef.current.clone(true);
          // Rotate charger 180 degrees (chargerMesh.rotation.y = Math.PI / 2)
          chargerMesh.rotation.y = Math.PI / 2;
          chargerMesh.position.set(0, 0, 0);
          anchorObj.add(chargerMesh);
        } else {
          // Procedural fallback dock cradle while OBJ loads
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

          dockGroup.rotation.y = Math.PI;
          anchorObj.add(dockGroup);
        }

        // Docking Guidance Halo Ring
        const ringGeo = new THREE.RingGeometry(0.048, 0.058, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0x10b981,
          transparent: true,
          opacity: 0.85,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.003;
        ring.name = 'halo';
        anchorObj.add(ring);
      } else {
        // ==========================================
        // FLOATING SEMANTIC OBJECT DIAMOND LANDMARK
        // ==========================================
        // 1. Floating Diamond
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

        // 2. Light beam pedestal
        const stemGeo = new THREE.CylinderGeometry(0.002, 0.002, 0.08, 8);
        const stemMat = new THREE.MeshBasicMaterial({
          color: baseColor,
          transparent: true,
          opacity: 0.5,
        });
        const stem = new THREE.Mesh(stemGeo, stemMat);
        stem.position.y = 0.04;
        anchorObj.add(stem);

        // 3. Ground Halo Ring
        const ringGeo = new THREE.RingGeometry(0.035, 0.045, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: baseColor,
          transparent: true,
          opacity: 0.7,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.004;
        ring.name = 'halo';
        anchorObj.add(ring);
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
        ctx.strokeStyle = isCharger ? '#10b981' : '#00d4ff';
        ctx.lineWidth = 3;
        ctx.roundRect(4, 4, 248, 56, 12);
        ctx.stroke();

        ctx.font = 'bold 20px monospace';
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const displayLabel = isCharger ? '⚡ CHARGER' : anchor.label.toUpperCase();
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

  // Update Obstacles in 3D Scene
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

  // Update Planned Path in 3D Scene
  useEffect(() => {
    const pathLine = pathLineRef.current;
    if (!pathLine) return;

    if (path && path.length > 1) {
      const points = path.map((pt) => new THREE.Vector3(pt[0] / 1000, 0.008, -pt[1] / 1000));
      pathLine.geometry.setFromPoints(points);
      pathLine.computeLineDistances();
      pathLine.visible = true;
    } else {
      pathLine.visible = false;
    }
  }, [path]);

  // Mouse Interaction: Click to Drive or Click Anchor
  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const container = containerRef.current;
      const camera = cameraRef.current;
      const ground = groundPlaneRef.current;
      const anchorsGroup = anchorsGroupRef.current;
      if (!container || !camera || !ground) return;

      const rect = container.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      // Check anchor click first
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

      // Check ground click for drive command
      if (onPointClick) {
        const groundIntersects = raycaster.intersectObject(ground);
        if (groundIntersects.length > 0) {
          const pt = groundIntersects[0].point;
          const worldX_mm = Math.round(pt.x * 1000);
          const worldY_mm = Math.round(-pt.z * 1000);
          onPointClick(worldX_mm, worldY_mm);
        }
      }
    },
    [onPointClick, onAnchorClick]
  );

  // Recenter Camera on Cozmo
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
        className="w-full h-full cursor-crosshair active:cursor-grabbing"
      />

      {/* Loading Overlay */}
      {isLoadingModel && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md flex flex-col items-center justify-center gap-3 z-20 pointer-events-none">
          <div className="w-10 h-10 border-3 border-cyan-400/20 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-xs font-mono text-cyan-300 tracking-wider">LOADING REPAIRED COZMO 3D MODEL...</span>
        </div>
      )}
      <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md p-1.5 rounded-xl border border-white/10 shadow-2xl z-10">
        <button
          onClick={() => setCameraMode('free')}
          className={`px-2.5 py-1 text-[11px] font-mono font-medium rounded-lg transition-all ${
            cameraMode === 'free'
              ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
          title="Free 360 Orbit Camera"
        >
          Free Orbit
        </button>
        <button
          onClick={() => setCameraMode('follow')}
          className={`px-2.5 py-1 text-[11px] font-mono font-medium rounded-lg transition-all ${
            cameraMode === 'follow'
              ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
          title="Follow Behind Cozmo"
        >
          Follow Cam
        </button>
        <button
          onClick={() => setCameraMode('iso')}
          className={`px-2.5 py-1 text-[11px] font-mono font-medium rounded-lg transition-all ${
            cameraMode === 'iso'
              ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
          title="Isometric View"
        >
          Isometric
        </button>
        <button
          onClick={() => setCameraMode('top')}
          className={`px-2.5 py-1 text-[11px] font-mono font-medium rounded-lg transition-all ${
            cameraMode === 'top'
              ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
          title="Top-Down Bird's Eye View"
        >
          Top-Down
        </button>
      </div>

      {/* Top Right Controls: 10m Drive Demo & Recenter */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        {/* 10m Drive Simulation Button */}
        <button
          onClick={handleToggleDemoDrive}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-mono font-bold shadow-xl transition-all hover:scale-105 active:scale-95 backdrop-blur-md ${
            isDemoDriving
              ? 'bg-amber-500/30 text-amber-300 border-amber-400/50 shadow-[0_0_15px_rgba(245,158,11,0.35)] animate-pulse'
              : 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30 hover:bg-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.25)]'
          }`}
          title="Test Driving Micro-Physics over 10 meters"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          {isDemoDriving ? `Driving: ${demoDistance.toFixed(1)}m / 10.0m [Stop]` : 'Drive 10m Demo'}
        </button>

        {/* Recenter Button */}
        <button
          onClick={handleRecenter}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800/90 border border-white/10 text-xs font-mono text-cyan-400 shadow-xl transition-all hover:scale-105 active:scale-95 backdrop-blur-md"
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
        <div className="bg-slate-900/85 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-[11px] font-mono text-slate-300 flex items-center gap-3 shadow-xl">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            3D Holographic World
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-cyan-300">Procedural Vehicle Dynamics Active</span>
        </div>

        <div className="bg-slate-900/85 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-[11px] font-mono text-cyan-300 shadow-xl">
          Grid: 100mm / 1000mm
        </div>
      </div>
    </div>
  );
};

export default Cozmo3DWorldMap;
