import React, { useEffect, useRef } from 'react';

/**
 * MatrixJunctionBackground component.
 * Exact implementation of the ThreeUI Matrix Junction (3-way pointer-reactive matrix laser junction).
 * Features:
 * - Dynamic junction focal point anchored directly to the "Start a conversation" button (#talk-button).
 * - Ultra-fine, razor-thin intersecting laser beams (dirUp, dirRight, dirDownLeft) with smooth harmonic runner pulses.
 * - Dynamic electric/lightning arcs connecting from the nearest laser beam to the mouse cursor.
 * - Refined center focal junction bloom and organic time oscillation.
 * - Tuned with pure 24k Gold & Amber laser palette over Obsidian for the Royal theme.
 */

export interface MatrixJunctionProps {
  className?: string;
  thickness?: number; // Scaling factor for line thickness (default 0.45 for elegant fine lines)
}

export const MatrixJunctionBackground: React.FC<MatrixJunctionProps> = ({
  className = '',
  thickness = 0.45,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const thicknessRef = useRef(thickness);
  thicknessRef.current = thickness;

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || typeof window === 'undefined') return;

    const gl = canvas.getContext('webgl', {
      alpha: true,
      antialias: false,
      powerPreference: 'high-performance',
    });

    if (!gl) return;

    let mouseX = -1000;
    let mouseY = -1000;
    let lastMouseMove = 0;
    let currentMouseActive = 0.0;

    let currentCenterX = 0.0;
    let currentCenterY = 0.0;
    let hasInitializedCenter = false;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = (e.clientX - rect.left) * (canvas.width / rect.width);
      mouseY = (rect.bottom - e.clientY) * (canvas.height / rect.height);
      lastMouseMove = Date.now();
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    const vsSource = `
      attribute vec4 aVertexPosition;
      void main() {
        gl_Position = aVertexPosition;
      }
    `;

    const fsSource = `
      precision highp float;
      uniform vec2 u_resolution;
      uniform float u_time;
      uniform vec2 u_mouse;
      uniform float u_mouseActive;
      uniform float u_thickness;
      uniform vec2 u_center;

      float hash(float n) { return fract(sin(n)*753.5453123); }
      float noise(float x) {
        float i = floor(x);
        float f = fract(x);
        f = f*f*(3.0-2.0*f);
        return mix(hash(i), hash(i+1.0), f);
      }

      vec2 sdLine(vec2 p, vec2 a, vec2 b) {
        vec2 pa = p - a, ba = b - a;
        float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
        return vec2(length(pa - ba * h), h);
      }

      float lightning(vec2 uv, vec2 a, vec2 b, float t) {
        vec2 ab = b - a;
        float len = length(ab);
        if(len < 0.01) return 0.0;
        vec2 dir = ab / len;
        
        vec2 pa = uv - a;
        float h = clamp(dot(pa, dir) / len, 0.0, 1.0);
        float dist = length(pa - dir * (h * len));
        
        float env = sin(h * 3.1415);
        
        float offset = (noise(h * 25.0 - t * 35.0) - 0.5) * 0.08 * env;
        offset += (noise(h * 70.0 + t * 50.0) - 0.5) * 0.02 * env;
        
        float d = abs(dist + offset);
        
        // Fine electric arc line
        return (0.00008 * u_thickness / (d + 0.00015) + 0.000004 * u_thickness / (d*d + 0.00002)) * env;
      }

      void main() {
        vec2 uv = gl_FragCoord.xy / u_resolution.xy;
        uv = uv * 2.0 - 1.0;
        uv.x *= u_resolution.x / u_resolution.y;

        vec2 mouseUV = u_mouse / u_resolution.xy;
        mouseUV = mouseUV * 2.0 - 1.0;
        mouseUV.x *= u_resolution.x / u_resolution.y;

        vec2 center = u_center;
        center.x += sin(u_time * 0.4) * 0.015;
        center.y += cos(u_time * 0.3) * 0.015;

        vec2 dirUp = normalize(vec2(0.15, 1.0));
        vec2 dirRight = normalize(vec2(1.0, 0.15));
        vec2 dirDownLeft = normalize(vec2(-0.8, -0.6));

        vec2 l1 = sdLine(uv, center, center + dirUp * 8.0);
        vec2 l2 = sdLine(uv, center, center + dirRight * 8.0);
        vec2 l3 = sdLine(uv, center, center + dirDownLeft * 8.0);

        // Crisp, slim laser line width
        float intensity = 0.0025 * u_thickness;
        float glow = intensity / (l1.x + 0.0012) +
                     intensity / (l2.x + 0.0012) +
                     (intensity * 0.4) / (l3.x + 0.0012);

        // Sleek runner pulses
        float pulse1 = smoothstep(0.1, 0.0, abs(l1.y - fract(u_time * 0.4))) * (0.012 * u_thickness) / (l1.x + 0.0012);
        float pulse2 = smoothstep(0.1, 0.0, abs(l2.y - fract(u_time * 0.5 + 0.3))) * (0.012 * u_thickness) / (l2.x + 0.0012);
        float pulse3 = smoothstep(0.1, 0.0, abs(l3.y - fract(u_time * 0.3 + 0.7))) * (0.006 * u_thickness) / (l3.x + 0.0012);
        glow += pulse1 + pulse2 + pulse3;

        vec2 p1 = center + dirUp * clamp(dot(mouseUV - center, dirUp), 0.0, 6.0);
        vec2 p2 = center + dirRight * clamp(dot(mouseUV - center, dirRight), 0.0, 6.0);
        vec2 p3 = center + dirDownLeft * clamp(dot(mouseUV - center, dirDownLeft), 0.0, 6.0);
        
        float lgt1 = lightning(uv, p1, mouseUV, u_time);
        float lgt2 = lightning(uv, p2, mouseUV, u_time + 10.0);
        float lgt3 = lightning(uv, p3, mouseUV, u_time + 20.0);
        
        float flicker = step(0.1, noise(u_time * 60.0)) * (noise(u_time * 150.0) * 0.8 + 0.2);
        
        float d1 = length(mouseUV - p1);
        float d2 = length(mouseUV - p2);
        float d3 = length(mouseUV - p3);
        
        glow += lgt1 * smoothstep(2.0, 0.0, d1) * u_mouseActive * flicker;
        glow += lgt2 * smoothstep(2.0, 0.0, d2) * u_mouseActive * flicker;
        glow += lgt3 * smoothstep(2.0, 0.0, d3) * u_mouseActive * flicker;

        float distToCenter = length(uv - center);
        glow += (0.022 * u_thickness) / (distToCenter + 0.012);

        // 👑 LUXURIOUS 24K GOLD & AMBER LASER PALETTE
        vec3 baseColor = vec3(0.98, 0.82, 0.28);
        vec3 finalColor = baseColor * glow;

        finalColor *= 0.85 + 0.15 * sin(u_time * 2.0 - distToCenter * 8.0);

        float vignette = 1.0 - smoothstep(0.5, 2.4, length(uv));
        finalColor *= vignette;

        float n = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
        finalColor += n * 0.02;

        gl_FragColor = vec4(finalColor, 1.0);
      }
    `;

    function createShader(glCtx: WebGLRenderingContext, type: number, source: string) {
      const shader = glCtx.createShader(type);
      if (!shader) return null;
      glCtx.shaderSource(shader, source);
      glCtx.compileShader(shader);
      if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
        console.error(glCtx.getShaderInfoLog(shader));
        return null;
      }
      return shader;
    }

    const vertexShader = createShader(gl, gl.VERTEX_SHADER, vsSource);
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
    if (!vertexShader || !fragmentShader) return;

    const shaderProgram = gl.createProgram();
    if (!shaderProgram) return;
    gl.attachShader(shaderProgram, vertexShader);
    gl.attachShader(shaderProgram, fragmentShader);
    gl.linkProgram(shaderProgram);

    const programInfo = {
      program: shaderProgram,
      attribLocations: { vertexPosition: gl.getAttribLocation(shaderProgram, 'aVertexPosition') },
      uniformLocations: {
        resolution: gl.getUniformLocation(shaderProgram, 'u_resolution'),
        time: gl.getUniformLocation(shaderProgram, 'u_time'),
        mouse: gl.getUniformLocation(shaderProgram, 'u_mouse'),
        mouseActive: gl.getUniformLocation(shaderProgram, 'u_mouseActive'),
        thickness: gl.getUniformLocation(shaderProgram, 'u_thickness'),
        center: gl.getUniformLocation(shaderProgram, 'u_center'),
      },
    };

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0, -1.0]),
      gl.STATIC_DRAW
    );

    const startTime = Date.now();
    let animId = 0;

    const render = () => {
      const rect = container.getBoundingClientRect();
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
      const targetW = Math.max(1, Math.round(rect.width * pixelRatio));
      const targetH = Math.max(1, Math.round(rect.height * pixelRatio));

      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
      }

      const aspect = rect.width / (rect.height || 1);
      let targetCenterX = -0.55 * aspect;
      let targetCenterY = -0.4;

      // Track the live DOM position of the "Start a conversation" button (#talk-button)
      const btn = document.getElementById('talk-button');
      if (btn) {
        const btnRect = btn.getBoundingClientRect();
        // Calculate center of button in client pixels relative to container
        const btnPxX = btnRect.left + btnRect.width * 0.5 - rect.left;
        const btnPxY = rect.height - (btnRect.top + btnRect.height * 0.5 - rect.top);

        // Convert to WebGL normalized coordinates (-1 to 1, aspect corrected)
        const normX = (btnPxX / rect.width) * 2.0 - 1.0;
        targetCenterX = normX * aspect;
        targetCenterY = (btnPxY / rect.height) * 2.0 - 1.0;
      }

      if (!hasInitializedCenter) {
        currentCenterX = targetCenterX;
        currentCenterY = targetCenterY;
        hasInitializedCenter = true;
      } else {
        currentCenterX += (targetCenterX - currentCenterX) * 0.12;
        currentCenterY += (targetCenterY - currentCenterY) * 0.12;
      }

      gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
      gl.useProgram(programInfo.program);

      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.vertexAttribPointer(programInfo.attribLocations.vertexPosition, 2, gl.FLOAT, false, 0, 0);
      gl.enableVertexAttribArray(programInfo.attribLocations.vertexPosition);

      const timeSinceMove = Date.now() - lastMouseMove;
      const targetActive = timeSinceMove < 150 ? 1.0 : Math.max(0.0, 1.0 - (timeSinceMove - 150) / 350.0);
      currentMouseActive += (targetActive - currentMouseActive) * 0.15;

      gl.uniform2f(programInfo.uniformLocations.resolution, gl.canvas.width, gl.canvas.height);
      gl.uniform1f(programInfo.uniformLocations.time, (Date.now() - startTime) * 0.001);
      gl.uniform2f(programInfo.uniformLocations.mouse, mouseX, mouseY);
      gl.uniform1f(programInfo.uniformLocations.mouseActive, currentMouseActive);
      gl.uniform1f(programInfo.uniformLocations.thickness, thicknessRef.current);
      gl.uniform2f(programInfo.uniformLocations.center, currentCenterX, currentCenterY);

      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      gl.deleteBuffer(positionBuffer);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
      gl.deleteProgram(shaderProgram);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
      style={{ background: '#030407' }}
    >
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  );
};

export default MatrixJunctionBackground;
