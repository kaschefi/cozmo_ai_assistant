import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * ObsidianGoldVeinsBackground component.
 * Renders a procedural WebGL GLSL shader on a full-screen canvas featuring:
 * - Deep glassy obsidian stone base with emerald undertones.
 * - Multi-octave domain-warped procedural marble gold veins.
 * - Dynamic metallic specular light reflection that glints and shines as the mouse moves.
 * - Subtle organic shimmer and morphing motion over time.
 */
export const ObsidianGoldVeinsBackground: React.FC<{ opacity?: number }> = ({ opacity = 1.0 }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    
    const renderer = new THREE.WebGLRenderer({
      powerPreference: 'high-performance',
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.domElement.style.position = 'absolute';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.pointerEvents = 'none';
    container.appendChild(renderer.domElement);

    // 2. Custom GLSL Vertex & Fragment Shaders
    const vertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position, 1.0);
      }
    `;

    const fragmentShader = `
      uniform vec2 u_resolution;
      uniform vec2 u_mouse;
      uniform float u_time;
      uniform float u_opacity;
      varying vec2 vUv;

      // 2D Hash function
      vec2 hash2(vec2 p) {
        p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
        return fract(sin(p) * 43758.5453123);
      }

      // 2D Simplex / Perlin noise
      float noise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(
          mix(dot(hash2(i + vec2(0.0, 0.0)) * 2.0 - 1.0, f - vec2(0.0, 0.0)),
              dot(hash2(i + vec2(1.0, 0.0)) * 2.0 - 1.0, f - vec2(1.0, 0.0)), u.x),
          mix(dot(hash2(i + vec2(0.0, 1.0)) * 2.0 - 1.0, f - vec2(0.0, 1.0)),
              dot(hash2(i + vec2(1.0, 1.0)) * 2.0 - 1.0, f - vec2(1.0, 1.0)), u.x), u.y);
      }

      // Fractional Brownian Motion (fBm) with 5 octaves
      float fbm(vec2 p) {
        float value = 0.0;
        float amp = 0.5;
        float freq = 1.0;
        mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5));
        for (int i = 0; i < 5; i++) {
          value += amp * noise(p * freq);
          p = rot * p * 2.02 + vec2(0.3, 0.2);
          amp *= 0.5;
        }
        return value;
      }

      // Domain-warped marble turbulence
      float marbleVein(vec2 p, out vec2 normalVec) {
        vec2 q = vec2(
          fbm(p + vec2(0.0, 0.0) + u_time * 0.015),
          fbm(p + vec2(5.2, 1.3) + u_time * 0.012)
        );

        vec2 r = vec2(
          fbm(p + 4.0 * q + vec2(1.7, 9.2) + u_time * 0.02),
          fbm(p + 4.0 * q + vec2(8.3, 2.8) - u_time * 0.018)
        );

        float f = fbm(p + 4.0 * r);
        
        // Calculate finite differences to generate vein surface normal for metallic specular lighting
        float eps = 0.015;
        float f_dx = fbm(p + 4.0 * r + vec2(eps, 0.0)) - f;
        float f_dy = fbm(p + 4.0 * r + vec2(0.0, eps)) - f;
        normalVec = normalize(vec2(-f_dx, -f_dy));

        // Sharp Kintsugi crack profile
        float vein1 = 1.0 - smoothstep(0.0, 0.07, abs(f - 0.05));
        float vein2 = 1.0 - smoothstep(0.0, 0.035, abs(f + 0.25));
        float vein3 = 1.0 - smoothstep(0.0, 0.02, abs(f - 0.35));

        return clamp(vein1 * 1.0 + vein2 * 0.75 + vein3 * 0.5, 0.0, 1.0);
      }

      void main() {
        vec2 st = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / min(u_resolution.x, u_resolution.y);
        
        // Aspect ratio correction & base scaling
        vec2 uv = st * 1.8;

        // Calculate gold vein density & normal vectors
        vec2 veinNormal;
        float vein = marbleVein(uv, veinNormal);

        // 1. Obsidian Glass Base Color
        vec3 obsidianDeep = vec3(0.012, 0.022, 0.016);    // Deep emerald-undertone obsidian
        vec3 obsidianSurface = vec3(0.03, 0.055, 0.038);  // Rich polished surface
        float bgNoise = fbm(uv * 0.8 + 10.0);
        vec3 obsidianColor = mix(obsidianDeep, obsidianSurface, clamp(bgNoise * 0.5 + 0.5, 0.0, 1.0));

        // 2. Mouse Light Dynamics & Specular Gold Glint
        vec2 mousePos = (u_mouse * 2.0 - 1.0);
        mousePos.y = -mousePos.y; // invert Y for screen coords
        vec2 lightDir = normalize(st - mousePos * 1.5 + vec2(0.1, 0.1));
        float lightDist = length(st - mousePos * 1.5);
        float mouseGlow = exp(-lightDist * 0.85);

        // Specular Shimmer on the gold veins
        vec3 surfaceNorm = normalize(vec3(veinNormal * 1.8, 1.0));
        vec3 lightVec = normalize(vec3(-lightDir, 0.8));
        vec3 viewVec = vec3(0.0, 0.0, 1.0);
        vec3 halfVec = normalize(lightVec + viewVec);

        float NdotL = max(dot(surfaceNorm, lightVec), 0.0);
        float NdotH = max(dot(surfaceNorm, halfVec), 0.0);
        float specular = pow(NdotH, 24.0) * (0.8 + 0.6 * mouseGlow);

        // 3. Luxurious Gold Palette
        vec3 goldBase = vec3(0.83, 0.68, 0.22);   // Classic 24k Gold
        vec3 goldHighlight = vec3(1.0, 0.95, 0.75); // Bright lustrous gold highlight
        vec3 goldDeep = vec3(0.48, 0.35, 0.08);   // Warm amber shadow

        // Dynamic gold color mixing
        vec3 goldColor = mix(goldDeep, goldBase, clamp(NdotL + 0.2, 0.0, 1.0));
        goldColor += goldHighlight * specular * 1.4;
        goldColor += vec3(0.1, 0.08, 0.02) * (sin(u_time * 2.0 + uv.x * 4.0) * 0.5 + 0.5); // micro-shimmer

        // 4. Vein Ambient Aura / Blooming Glow
        vec3 goldAura = vec3(0.85, 0.65, 0.18) * pow(vein, 0.7) * 0.45;
        vec3 emeraldAura = vec3(0.04, 0.22, 0.12) * pow(vein, 0.5) * 0.35;

        // Composite layers
        vec3 finalColor = mix(obsidianColor, goldColor, vein);
        finalColor += goldAura * 0.6;
        finalColor += emeraldAura;

        // Subtle Vignette
        float vignette = 1.0 - smoothstep(0.7, 1.8, length(st));
        finalColor *= vignette;

        gl_FragColor = vec4(finalColor, u_opacity);
      }
    `;

    // 3. Material & Mesh
    const uniforms = {
      u_resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      u_mouse: { value: new THREE.Vector2(0.5, 0.5) },
      u_time: { value: 0 },
      u_opacity: { value: opacity },
    };

    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      transparent: true,
      depthWrite: false,
    });

    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // 4. Mouse Tracking
    const handleMouseMove = (e: MouseEvent) => {
      uniforms.u_mouse.value.x = e.clientX / window.innerWidth;
      uniforms.u_mouse.value.y = e.clientY / window.innerHeight;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // 5. Resize Handling
    const handleResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      uniforms.u_resolution.value.set(w, h);
    };
    window.addEventListener('resize', handleResize);

    // 6. Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      uniforms.u_time.value = clock.getElapsedTime();
      renderer.render(scene, camera);
    };
    animate();

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [opacity]);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden"
    />
  );
};

export default ObsidianGoldVeinsBackground;
