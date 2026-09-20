import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useTheme } from '../../context/ThemeContext';

interface CozmoModelPreviewProps {
  className?: string;
}

export const CozmoModelPreview: React.FC<CozmoModelPreviewProps> = ({
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const controlsRef = useRef<OrbitControls | null>(null);
  const { theme } = useTheme();

  // Accent colors per theme
  const getThemeAccentHex = () => {
    switch (theme) {
      case 'royal':
        return 0xf59e0b; // Gold/Amber
      case 'it':
        return 0x12a574; // Phthalo Green
      case 'black-ice':
      default:
        return 0x00f0ff; // Glacial Cyan
    }
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene & Renderer setup
    const scene = new THREE.Scene();
    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.01, 100);
    camera.position.set(0.18, 0.15, 0.22);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.appendChild(renderer.domElement);

    // 2. Controls (Rotation only - no auto-rotation, no zoom)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.autoRotate = false;
    controls.enableZoom = false;
    controls.enableRotate = true;
    controls.enablePan = false;
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controlsRef.current = controls;

    // 3. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    keyLight.position.set(1.5, 2.5, 1.5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 1024;
    keyLight.shadow.mapSize.height = 1024;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x94a3b8, 1.2);
    fillLight.position.set(-1.5, 1.0, -1.0);
    scene.add(fillLight);

    const accentHex = getThemeAccentHex();
    const rimLight = new THREE.PointLight(accentHex, 3.2, 5.0);
    rimLight.position.set(-0.8, 0.6, -0.8);
    scene.add(rimLight);

    // 4. Ground Shadow / Soft Radial Floor Glow
    const groundShadowCanvas = document.createElement('canvas');
    groundShadowCanvas.width = 128;
    groundShadowCanvas.height = 128;
    const gCtx = groundShadowCanvas.getContext('2d');
    if (gCtx) {
      const grad = gCtx.createRadialGradient(64, 64, 8, 64, 64, 64);
      const hexStr = `#${accentHex.toString(16).padStart(6, '0')}`;
      grad.addColorStop(0, 'rgba(0, 0, 0, 0.7)');
      grad.addColorStop(0.35, `${hexStr}44`);
      grad.addColorStop(0.7, 'rgba(0, 0, 0, 0.25)');
      grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      gCtx.fillStyle = grad;
      gCtx.fillRect(0, 0, 128, 128);
    }
    const groundTex = new THREE.CanvasTexture(groundShadowCanvas);
    const groundGeo = new THREE.PlaneGeometry(1, 1);
    const groundMat = new THREE.MeshBasicMaterial({
      map: groundTex,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });
    const groundMesh = new THREE.Mesh(groundGeo, groundMat);
    groundMesh.rotation.x = -Math.PI / 2;
    groundMesh.position.y = 0.001;
    scene.add(groundMesh);

    // 5. Load Cozmo GLB Model
    let cozmoPivot: THREE.Group | null = null;
    let floatAmplitude = 0.005;

    const gltfLoader = new GLTFLoader();
    gltfLoader.load(
      '/models/cozmo/sample_2026-09-19T141859.988.glb',
      (gltf) => {
        const object = gltf.scene;
        object.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            if (child.material) {
              const mats = Array.isArray(child.material) ? child.material : [child.material];
              mats.forEach((m) => {
                m.side = THREE.DoubleSide;
              });
            }
          }
        });

        // Compute exact bounding box to center the model perfectly
        const bbox = new THREE.Box3().setFromObject(object);
        const center = bbox.getCenter(new THREE.Vector3());
        const size = bbox.getSize(new THREE.Vector3());

        // Center geometry inside a dedicated pivot with base at y = 0
        object.position.set(-center.x, -bbox.min.y, -center.z);

        const pivot = new THREE.Group();
        pivot.add(object);
        scene.add(pivot);
        cozmoPivot = pivot;

        const maxDim = Math.max(size.x, size.y, size.z);
        floatAmplitude = Math.max(size.y, 0.5) * 0.015;

        // Scale ground shadow mesh according to model footprint
        const groundScale = Math.max(size.x, size.z) * 2.2;
        groundMesh.scale.set(groundScale, groundScale, 1);

        // Position lights relative to model scale
        keyLight.position.set(maxDim * 1.5, maxDim * 2.5, maxDim * 1.5);
        fillLight.position.set(-maxDim * 1.5, maxDim * 1.0, -maxDim * 1.0);
        rimLight.position.set(-maxDim * 0.7, maxDim * 0.5, -maxDim * 0.7);
        rimLight.distance = maxDim * 5.0;

        // Target camera to the optical center of the model
        const centerY = size.y * 0.45;
        controls.target.set(0, centerY, 0);

        const dist = maxDim * 2.1;
        camera.position.set(dist * 0.85, dist * 0.65, dist * 0.95);
        camera.lookAt(0, centerY, 0);
        controls.update();

        setIsLoading(false);
      },
      undefined,
      (err) => {
        console.error('Failed to load Cozmo GLB:', err);
        setIsLoading(false);
      }
    );

    // 6. Animation loop
    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      if (controlsRef.current) {
        controlsRef.current.update();
      }

      // Subtle organic idling floating effect
      if (cozmoPivot) {
        cozmoPivot.position.y = Math.sin(elapsedTime * 1.8) * floatAmplitude;
      }

      renderer.render(scene, camera);
    };
    animate();

    // 7. Handle Resize
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newW, height: newH } = entry.contentRect;
        if (newW > 0 && newH > 0) {
          camera.aspect = newW / newH;
          camera.updateProjectionMatrix();
          renderer.setSize(newW, newH);
        }
      }
    });
    resizeObserver.observe(container);

    // 8. Cleanup
    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      scene.clear();
    };
  }, [theme]);

  return (
    <div
      className={`relative w-full h-[360px] sm:h-[400px] md:h-[450px] bg-transparent overflow-visible group cursor-grab active:cursor-grabbing ${className}`}
    >
      {/* Transparent 3D WebGL Canvas Container */}
      <div ref={containerRef} className="w-full h-full" />

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[var(--brand-light)] border-t-transparent animate-spin" />
        </div>
      )}
    </div>
  );
};

export default CozmoModelPreview;
