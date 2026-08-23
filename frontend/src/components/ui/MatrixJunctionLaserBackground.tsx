import React, { useEffect, useRef } from 'react';

/**
 * MatrixJunctionLaserBackground component.
 * Port of the ThreeUI LaserCollection (Matrix Junction / Matrix Field) raw WebGL2 shader pipeline.
 * Features:
 * - Pass 1: Multi-layer laser junction cross-beams with traveling runner pulse and ripple distortion.
 * - Pass 2: Atmospheric directional blur, ordered blue-noise dither, and drifting Voronoi star-dust wisps.
 * - Pass 3: Pointer-reactive Halftone matrix glyphs and braille lattice.
 * - Full Gold & Obsidian palette for the Royal theme.
 */

export interface MatrixJunctionProps {
  variant?: 'cross' | 'ring' | 'frame' | 'x';
  speed?: number;
  beamWidth?: number;
  dither?: number;
  glyphSize?: number;
  glyphAmount?: number;
  noiseScale?: number;
  className?: string;
}

const VERTEX_SHADER = `#version 300 es
precision highp float;

out vec2 vUv;

void main() {
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  vUv = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
`;

const COMMON_HEADER = `#version 300 es
precision highp float;
precision highp int;

const float PI = 3.14159265359;
const float TWO_PI = 6.28318530718;

in vec2 vUv;
out vec4 fragColor;

uvec2 pcg2d(uvec2 v) {
  v = v * 1664525u + 1013904223u;
  v.x += v.y * v.y * 1664525u + 1013904223u;
  v.y += v.x * v.x * 1664525u + 1013904223u;
  v ^= v >> 16;
  v.x += v.y * v.y * 1664525u + 1013904223u;
  v.y += v.x * v.x * 1664525u + 1013904223u;
  return v;
}

float randFibo(vec2 p) {
  uvec2 v = floatBitsToUint(p);
  v = pcg2d(v);
  uint r = v.x ^ v.y;
  return float(r) / float(0xffffffffu);
}

vec3 quantize(vec3 c) {
  return floor(clamp(c, 0.0, 1.0) * 255.0 + 0.5) / 255.0;
}

#define MAX_RIPPLES 4

uniform vec2 uAspect;
uniform vec2 uPointer;
uniform float uPointerAmount;
uniform float uChaosTime;
uniform vec3 uRipples[MAX_RIPPLES];

const float CHAOS_RADIUS = 0.16;
const float CHAOS_RATE = 2.0;
const float RIPPLE_SPEED = 0.62;
const float RIPPLE_WIDTH = 0.1;
const float RIPPLE_FREQ = 26.0;
const float RIPPLE_AMP = 0.05;
const float RIPPLE_DECAY = 1.15;

float pointerChaos(vec2 uv) {
  if (uPointerAmount <= 0.001) return 0.0;
  vec2 toPointer = (uv - uPointer) * uAspect;
  float dist = length(toPointer);
  return exp(-(dist * dist) / (CHAOS_RADIUS * CHAOS_RADIUS)) * uPointerAmount;
}

float chaosSeed() {
  return floor(uChaosTime * CHAOS_RATE);
}

float churnRand(vec2 id, float seed) {
  return randFibo(vec2(randFibo(id), seed));
}

vec2 rippleDisplace(vec2 uv) {
  vec2 offset = vec2(0.0);
  for (int i = 0; i < MAX_RIPPLES; i++) {
    float age = uRipples[i].z;
    if (age < 0.0) continue;
    vec2 fromCenter = (uv - uRipples[i].xy) * uAspect;
    float dist = length(fromCenter);
    float band = dist - age * RIPPLE_SPEED;
    float envelope = exp(-(band * band) / (RIPPLE_WIDTH * RIPPLE_WIDTH)) * exp(-age * RIPPLE_DECAY);
    offset += normalize(fromCenter + 1e-6) * sin(band * RIPPLE_FREQ) * envelope * RIPPLE_AMP;
  }
  return uv + offset / uAspect;
}
`;

const BEAM_FRAGMENT_SHADER = `${COMMON_HEADER}
uniform vec3 uThickness;
uniform float uTime;
uniform int uShape;

#define SHAPE_CROSS 0
#define SHAPE_RING 1
#define SHAPE_FRAME 2
#define SHAPE_X 3

// 👑 GOLD LASER BEAMS
const vec3 BEAM_A = vec3(0.55, 0.38, 0.10);  // Deep gold amber ambient wash
const vec3 BEAM_B = vec3(0.85, 0.68, 0.22);  // Rich 24k gold core
const vec3 BEAM_C = vec3(1.00, 0.92, 0.60);  // Brilliant lustrous gold traveling highlight

vec3 tonemapTanh(vec3 x) {
  x = clamp(x, -40.0, 40.0);
  return (exp(x) - exp(-x)) / (exp(x) + exp(-x));
}

float drawLine(vec2 uv, vec2 center, float scale, float angle, float thickness, float phaseOffset, float time) {
  float radAngle = -angle * TWO_PI;
  float phase = fract(time * 0.01 + phaseOffset) * (3.0 * max(1.0, scale)) - (1.5 * max(1.0, scale));
  vec2 direction = vec2(cos(radAngle), sin(radAngle));
  vec2 centerToPoint = uv - center;
  float projection = dot(centerToPoint, direction);
  float distToLine = length(centerToPoint - projection * direction);
  float lineRadius = thickness * 0.25;
  float brightness = lineRadius / max(0.0001, 1.0 - smoothstep(0.4, 0.0, distToLine + 0.02));
  float glow = smoothstep(scale, 0.0, abs(projection - phase));
  return brightness * (1.0 - distToLine) * (1.0 - distToLine) * glow;
}

vec2 squareSpace(vec2 uv, vec2 center) {
  return (uv - center) * uAspect / min(uAspect.x, 1.0);
}

float beamFalloff(float dist) {
  float edge = max(0.0, 1.0 - dist);
  return edge * edge;
}

float beamCore(float dist, float thickness, float spread) {
  return (thickness * 0.25) / max(0.0001, 1.0 - smoothstep(spread, 0.0, dist + 0.02));
}

float drawLineSquare(vec2 uv, vec2 center, float scale, float angle, float thickness, float spread, float phaseOffset, float time) {
  float radAngle = -angle * TWO_PI;
  float phase = fract(time * 0.01 + phaseOffset) * (3.0 * max(1.0, scale)) - (1.5 * max(1.0, scale));
  vec2 direction = vec2(cos(radAngle), sin(radAngle));
  vec2 centerToPoint = squareSpace(uv, center);
  float projection = dot(centerToPoint, direction);
  float distToLine = length(centerToPoint - projection * direction);
  float glow = smoothstep(scale, 0.0, abs(projection - phase));
  return beamCore(distToLine, thickness, spread) * beamFalloff(distToLine) * glow;
}

float drawRing(vec2 uv, vec2 center, float radius, float arc, float thickness, float spread, float phaseOffset, float time) {
  vec2 toPoint = squareSpace(uv, center);
  float distToRing = abs(length(toPoint) - radius);
  float around = atan(toPoint.y, toPoint.x) / TWO_PI;
  float phase = fract(time * 0.01 + phaseOffset);
  float delta = abs(fract(around - phase + 0.5) - 0.5);
  float glow = smoothstep(arc, 0.0, delta);
  return beamCore(distToRing, thickness, spread) * beamFalloff(distToRing) * glow;
}

float framePerimeter(vec2 p, vec2 bounds) {
  float total = 4.0 * (bounds.x + bounds.y);
  bool onSide = abs(p.x) * bounds.y > abs(p.y) * bounds.x;
  float travelled;
  if (!onSide && p.y >= 0.0) {
    travelled = p.x + bounds.x;
  } else if (onSide && p.x >= 0.0) {
    travelled = 2.0 * bounds.x + (bounds.y - p.y);
  } else if (!onSide) {
    travelled = 2.0 * bounds.x + 2.0 * bounds.y + (bounds.x - p.x);
  } else {
    travelled = 4.0 * bounds.x + 2.0 * bounds.y + (p.y + bounds.y);
  }
  return travelled / total;
}

float drawFrame(vec2 uv, vec2 bounds, float arc, float thickness, float spread, float phaseOffset, float time) {
  vec2 p = squareSpace(uv, vec2(0.5));
  vec2 q = abs(p) - bounds;
  float distToEdge = abs(length(max(q, 0.0)) + min(max(q.x, q.y), 0.0));
  float phase = fract(time * 0.01 + phaseOffset);
  float delta = abs(fract(framePerimeter(p, bounds) - phase + 0.5) - 0.5);
  float glow = smoothstep(arc, 0.0, delta);
  return beamCore(distToEdge, thickness, spread) * beamFalloff(distToEdge) * glow;
}

vec2 frameBounds() {
  return max(vec2(0.05), uAspect * 0.5 / min(uAspect.x, 1.0) - vec2(0.035));
}

const vec2 X_CENTER = vec2(0.5, 0.5);
const float X_WASH_ANGLE = 0.1251;
const float X_CORE_ANGLE = 0.3751;

void shapeLayers(vec2 uv, float time, out float wash, out float core, out float runner) {
  if (uShape == SHAPE_RING) {
    wash = drawRing(uv, vec2(0.5, 0.5), 0.29, 0.80, uThickness.x * 0.45, 0.36, 0.62, 0.0);
    core = drawRing(uv, vec2(0.5, 0.5), 0.27, 0.66, uThickness.y * 0.80, 0.33, 0.40, 0.0);
    runner = drawRing(uv, vec2(0.5, 0.5), 0.27, 0.15, uThickness.z, 0.33, 0.53, time);
    return;
  }
  if (uShape == SHAPE_FRAME) {
    vec2 bounds = frameBounds();
    wash = drawFrame(uv, bounds, 0.85, uThickness.x * 0.40, 0.36, 0.66, 0.0);
    core = drawFrame(uv, bounds, 0.70, uThickness.y * 0.75, 0.32, 0.42, 0.0);
    runner = drawFrame(uv, bounds, 0.12, uThickness.z, 0.32, 0.53, time);
    return;
  }
  if (uShape == SHAPE_X) {
    wash = drawLineSquare(uv, X_CENTER, 0.62, X_WASH_ANGLE, uThickness.x * 0.60, 0.34, 0.5, 0.0)
         + drawLineSquare(uv, X_CENTER, 0.62, X_CORE_ANGLE, uThickness.x * 0.60, 0.34, 0.5, 0.0);
    core = drawLineSquare(uv, X_CENTER, 0.82, X_WASH_ANGLE, uThickness.y * 0.60, 0.30, 0.5, 0.0)
         + drawLineSquare(uv, X_CENTER, 0.82, X_CORE_ANGLE, uThickness.y * 0.60, 0.30, 0.5, 0.0);
    runner = drawLineSquare(uv, X_CENTER, 0.90, X_WASH_ANGLE, uThickness.z * 0.85, 0.32, 0.53, time)
           + drawLineSquare(uv, X_CENTER, 0.90, X_CORE_ANGLE, uThickness.z * 0.85, 0.32, 0.03, time);
    return;
  }

  // Cross variant (Matrix Junction)
  wash = drawLine(uv, vec2(0.5, 0.35), 0.53, 0.0, uThickness.x, 0.5, 0.0);
  core = drawLine(uv, vec2(0.5, 0.15), 1.0, 0.2511, uThickness.y, 0.53, 0.0);
  runner = drawLine(uv, vec2(0.5, 0.15), 1.0, 0.2511, uThickness.z, 0.53, time);
}

void main() {
  vec2 uv = rippleDisplace(vUv);
  float dither = (randFibo(gl_FragCoord.xy) - 0.5) / 255.0;
  vec3 col = vec3(0.0);

  float wash, core, runner;
  shapeLayers(uv, uTime, wash, core, runner);

  col = quantize(col + 0.77 * tonemapTanh(BEAM_A * wash) + dither);
  col = quantize(col + 0.75 * tonemapTanh(BEAM_B * core) + dither);
  col = quantize(col + 0.75 * tonemapTanh(BEAM_C * runner) + dither);

  fragColor = vec4(col, 1.0);
}
`;

const ATMOSPHERE_FRAGMENT_SHADER = `${COMMON_HEADER}
uniform sampler2D uScene;
uniform sampler2D uBlueNoise;
uniform vec2 uResolution;
uniform float uTime;
uniform float uNoiseScale;
uniform float uDitherStep;

const float MAX_ITERATIONS = 24.0;
const float WISP_SCALE = 4.56;
const float CHAOS_DITHER_COARSEN = 3.4;
const float CHAOS_DITHER_SCRAMBLE = 0.9;
const float CHAOS_WISP_SCATTER = 0.012;
const float CHAOS_WISP_GAIN = 0.9;

float blueNoise(vec2 st) {
  ivec2 texSize = textureSize(uBlueNoise, 0);
  vec2 scaled = st * (uResolution / uNoiseScale) / vec2(texSize) * vec2(float(texSize.x) / float(texSize.y), 1.0);
  vec4 n = texelFetch(uBlueNoise, ivec2(fract(scaled) * vec2(texSize)) % texSize, 0);
  return mod((n.r - 0.5) * TWO_PI, TWO_PI) / TWO_PI - 0.005;
}

vec2 hash(vec2 p) {
  p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float voronoiAdditive(vec2 st, float radius) {
  vec2 i_st = floor(st);
  float total = 0.0;
  for (int y = -2; y <= 2; y++) {
    for (int x = -2; x <= 2; x++) {
      vec2 cellId = i_st + vec2(float(x), float(y));
      vec2 h = hash(cellId);
      vec2 point = 0.5 + 0.5 * sin(5.0 + 6.2831 * h);
      float dist = length((cellId + point) - st);
      float contribution = radius / max(dist, radius * 0.1);
      float shimmerPhase = dot(point, vec2(1.0)) * 10.0 + h.x * 5.0 + uTime * 0.5;
      contribution *= mix(1.0, sin(shimmerPhase) + 1.0, 0.44);
      total += mix(contribution * contribution, contribution * 2.0, 0.25);
    }
  }
  return total;
}

void main() {
  vec2 uv = vUv;
  float aspectRatio = uResolution.x / uResolution.y;
  vec2 aspect = vec2(aspectRatio, 1.0);

  float falloff = max(0.0, 1.0 - distance(uv * aspect, vec2(0.5) * aspect) * 4.0 * (1.0 - 0.65));
  float amount = 0.18 * 2.0 * falloff;
  vec3 col;
  if (amount <= 0.001) {
    col = texture(uScene, uv).rgb;
  } else {
    vec3 result = vec3(0.0);
    float threshold = max(1.0 - 0.04, 2.0 / MAX_ITERATIONS);
    vec2 dir = vec2(0.2 / aspectRatio, 1.0 - 0.2) * amount * 0.4;
    float iterations = 0.0;
    for (float i = 1.0; i <= MAX_ITERATIONS; i++) {
      float th = i * (1.0 / MAX_ITERATIONS);
      if (th > threshold) break;
      float r1 = randFibo(uv + th);
      float r2 = randFibo(uv + th * 2.0);
      float r3 = randFibo(uv + th * 3.0);
      vec2 ranPoint = vec2(r1 * 2.0 - 1.0, r2 * 2.0 - 1.0) * mix(1.0, r3, 0.8);
      result += texture(uScene, uv + ranPoint * dir).rgb;
      iterations += 1.0;
    }
    col = result / max(1.0, iterations);
  }
  col = quantize(col);

  float chaos = pointerChaos(uv);
  float seed = chaosSeed();

  float levels = 1.0 / mix(uDitherStep, uDitherStep * CHAOS_DITHER_COARSEN, chaos);
  float threshold = blueNoise(uv);
  threshold = mix(threshold, churnRand(gl_FragCoord.xy, seed), chaos * CHAOS_DITHER_SCRAMBLE);
  col = quantize(mix(col, floor(col * levels + threshold) / levels, 0.5));

  vec2 wispUv = rippleDisplace(uv);
  if (chaos > 0.001) {
    vec2 jitter = vec2(
      churnRand(floor(uv * uResolution), seed),
      churnRand(floor(uv * uResolution), seed + 37.0)
    ) - 0.5;
    wispUv += jitter * chaos * CHAOS_WISP_SCATTER;
  }
  vec2 p = (wispUv - 0.5) * aspect;
  p = -p;
  p *= 40.0 * WISP_SCALE;
  p *= vec2(1.0, 0.03);
  p /= aspect;
  p += vec2(0.0, uTime * 0.35 * -0.05);
  float radius = 0.5 * 0.54;
  float wisps = voronoiAdditive(p * aspect, radius) * 0.02
              + voronoiAdditive(p * aspect + vec2(10.0), radius) * 0.04;
  wisps *= 1.0 + chaos * CHAOS_WISP_GAIN;
  vec3 dust = clamp(vec3(wisps) * mix(1.0, col.r, 1.15), 0.0, 1.0);

  fragColor = vec4(clamp(col + dust, 0.0, 1.0), 1.0);
}
`;

const GLYPH_FRAGMENT_SHADER = `${COMMON_HEADER}
uniform sampler2D uScene;
uniform vec2 uResolution;
uniform float uGridSize;
uniform float uGlyphAmount;

const float GLYPH_STEPS = 9.0;
const float GLYPH_RADIUS_STEP = 0.041;
const vec2 BRAILLE_BLOCK = vec2(2.0, 3.0);
const float BRAILLE_ACTIVE = 0.62;
const float CHAOS_LIT_LEVEL = 7.0;
const float CHAOS_DIM = 0.3;
const float CHAOS_INK_LIFT = 0.9;
const float CHAOS_CELL_JITTER = 0.05;
const float CHAOS_SIZE_SPREAD = 0.5;
const float CHAOS_FADE_MIN = 0.28;

void main() {
  vec2 uv = vUv;
  vec2 dotUv = rippleDisplace(uv);
  vec2 pos = vec2(0.5);
  float aspectRatio = uResolution.x / uResolution.y;

  vec2 cellSize = vec2(uGridSize / aspectRatio, uGridSize);
  vec2 cellUv = (dotUv - pos) / cellSize;
  vec2 cellId = floor(cellUv);
  vec2 pixelatedCoord = (cellId + 0.5) * cellSize + pos;
  vec4 bg = texture(uScene, uv);
  vec4 color = texture(uScene, pixelatedCoord);
  float luminance = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
  float gamma = pow(mix(0.2, 2.2, 0.8), 2.2);

  float level = clamp(floor(luminance * GLYPH_STEPS * gamma), 0.0, GLYPH_STEPS - 1.0);

  float chaos = pointerChaos(uv);
  vec2 dotCentre = vec2(0.5);
  float lit = 0.0;
  float shade = 1.0;
  if (chaos > 0.001) {
    vec2 block = floor(cellId / BRAILLE_BLOCK);
    vec2 slot = cellId - block * BRAILLE_BLOCK;
    float seed = floor(uChaosTime * CHAOS_RATE + churnRand(block, 7.0));
    float glyphBits = floor(churnRand(block, seed) * 64.0);
    float bit = mod(floor(glyphBits / exp2(slot.x * 3.0 + slot.y)), 2.0);
    float blockOn = step(1.0 - chaos * BRAILLE_ACTIVE, churnRand(block, seed + 5.0));

    lit = blockOn * bit * chaos;
    shade = churnRand(cellId, seed + 31.0);
    float litLevel = mix(CHAOS_LIT_LEVEL * CHAOS_SIZE_SPREAD, CHAOS_LIT_LEVEL, shade);
    level = mix(level, mix(level * CHAOS_DIM, litLevel, lit), chaos);
    dotCentre += (vec2(churnRand(cellId, seed + 11.0), churnRand(cellId, seed + 23.0)) - 0.5)
      * chaos * CHAOS_CELL_JITTER;
  }

  float radius = level * GLYPH_RADIUS_STEP;
  float dist = length(fract(cellUv) - dotCentre);
  float aa = 0.7 / max(1.0, uGridSize * uResolution.y);
  float alpha = smoothstep(0.0, 1.0, 1.0 - smoothstep(radius - aa, radius + aa, dist));

  // 👑 GOLD TINTED INK FOR GLYPH MATRIX
  vec3 ink = mix(vec3(0.72, 0.55, 0.20), vec3(1.0, 0.95, 0.75), lit * CHAOS_INK_LIFT * shade);
  vec3 glyph = ink * alpha * mix(1.0, mix(CHAOS_FADE_MIN, 1.0, shade), lit);
  
  // Mix into deep obsidian background
  vec3 baseObsidian = vec3(0.015, 0.025, 0.018);
  vec3 composited = mix(baseObsidian + bg.rgb, glyph + bg.rgb, uGlyphAmount);
  fragColor = vec4(composited, 1.0);
}
`;

const SHAPE_MAP = {
  cross: 0,
  ring: 1,
  frame: 2,
  x: 3,
};

const BASE_THICKNESS = [0.28, 0.16, 0.16];
const MAX_RIPPLES_COUNT = 4;
const RIPPLE_LIFETIME_SEC = 2.6;
const PROXIMITY_PX = 120;
const BEAM_SPEED_MULT = 0.25 * 60;
const ATMOSPHERE_SPEED_MULT = 0.56 * 60;

function createShader(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) throw new Error('Unable to create WebGL shader');
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Matrix Junction shader compilation failed: ${info}`);
  }
  return shader;
}

function createProgram(gl: WebGL2RenderingContext, fragmentSource: string): WebGLProgram {
  const program = gl.createProgram();
  if (!program) throw new Error('Unable to create WebGL program');
  const vs = createShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fs = createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(`Matrix Junction program link failed: ${info}`);
  }
  return program;
}

function createRenderTarget(gl: WebGL2RenderingContext, width: number, height: number) {
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

  const framebuffer = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);

  return { texture, framebuffer };
}

export const MatrixJunctionLaserBackground: React.FC<MatrixJunctionProps> = ({
  variant = 'cross',
  speed = 1.0,
  beamWidth = 1.1,
  dither = 0.11,
  glyphSize = 4.0,
  glyphAmount = 0.52,
  noiseScale = 1.0,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas || typeof window === 'undefined') return;

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: false,
    });

    if (!gl) {
      console.warn('WebGL2 not supported for MatrixJunctionLaserBackground');
      return;
    }

    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let renderTargets: { texture: WebGLTexture | null; framebuffer: WebGLFramebuffer | null }[] = [];
    let noiseTexture: WebGLTexture | null = null;
    let vao: WebGLVertexArrayObject | null = null;
    let animFrameId = 0;

    let width = 0;
    let height = 0;

    const pointer = {
      targetX: 0.5,
      targetY: 0.5,
      x: 0.5,
      y: 0.5,
      targetAmount: 0,
      amount: 0,
    };

    const ripples: { x: number; y: number; bornMs: number }[] = [];
    const rippleBuffer = new Float32Array(MAX_RIPPLES_COUNT * 3);
    for (let i = 0; i < MAX_RIPPLES_COUNT; i++) rippleBuffer[i * 3 + 2] = -1;

    let programs: { beam: WebGLProgram; atmosphere: WebGLProgram; glyph: WebGLProgram };
    try {
      programs = {
        beam: createProgram(gl, BEAM_FRAGMENT_SHADER),
        atmosphere: createProgram(gl, ATMOSPHERE_FRAGMENT_SHADER),
        glyph: createProgram(gl, GLYPH_FRAGMENT_SHADER),
      };
    } catch (err) {
      console.error(err);
      return;
    }

    const uniforms = {
      beam: {
        thickness: gl.getUniformLocation(programs.beam, 'uThickness'),
        time: gl.getUniformLocation(programs.beam, 'uTime'),
        shape: gl.getUniformLocation(programs.beam, 'uShape'),
      },
      atmosphere: {
        scene: gl.getUniformLocation(programs.atmosphere, 'uScene'),
        blueNoise: gl.getUniformLocation(programs.atmosphere, 'uBlueNoise'),
        resolution: gl.getUniformLocation(programs.atmosphere, 'uResolution'),
        time: gl.getUniformLocation(programs.atmosphere, 'uTime'),
        noiseScale: gl.getUniformLocation(programs.atmosphere, 'uNoiseScale'),
        ditherStep: gl.getUniformLocation(programs.atmosphere, 'uDitherStep'),
      },
      glyph: {
        scene: gl.getUniformLocation(programs.glyph, 'uScene'),
        resolution: gl.getUniformLocation(programs.glyph, 'uResolution'),
        gridSize: gl.getUniformLocation(programs.glyph, 'uGridSize'),
        glyphAmount: gl.getUniformLocation(programs.glyph, 'uGlyphAmount'),
      },
    };

    const commonUniforms = Object.fromEntries(
      Object.entries(programs).map(([name, prog]) => [
        name,
        {
          aspect: gl.getUniformLocation(prog, 'uAspect'),
          pointer: gl.getUniformLocation(prog, 'uPointer'),
          pointerAmount: gl.getUniformLocation(prog, 'uPointerAmount'),
          chaosTime: gl.getUniformLocation(prog, 'uChaosTime'),
          ripples: gl.getUniformLocation(prog, 'uRipples[0]'),
        },
      ])
    );

    vao = gl.createVertexArray();
    gl.disable(gl.BLEND);
    gl.disable(gl.DEPTH_TEST);

    // Procedural 128x128 Blue-noise replacement
    noiseTexture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, noiseTexture);
    const noiseData = new Uint8Array(128 * 128 * 4);
    for (let i = 0; i < 128 * 128 * 4; i += 4) {
      const v = Math.floor(Math.random() * 256);
      noiseData[i] = v;
      noiseData[i + 1] = v;
      noiseData[i + 2] = v;
      noiseData[i + 3] = 255;
    }
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 128, 128, 0, gl.RGBA, gl.UNSIGNED_BYTE, noiseData);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const newW = Math.max(1, Math.round(rect.width * dpr));
      const newH = Math.max(1, Math.round(rect.height * dpr));
      if (newW === width && newH === height) return;

      width = newW;
      height = newH;
      canvas.width = width;
      canvas.height = height;

      renderTargets.forEach((rt) => {
        if (rt.texture) gl.deleteTexture(rt.texture);
        if (rt.framebuffer) gl.deleteFramebuffer(rt.framebuffer);
      });
      renderTargets = [createRenderTarget(gl, width, height), createRenderTarget(gl, width, height)];
    };

    resize();

    const setCommonUniforms = (pass: 'beam' | 'atmosphere' | 'glyph', chaosTime: number) => {
      const u = commonUniforms[pass];
      if (u.aspect) gl.uniform2f(u.aspect, width / height, 1.0);
      if (u.pointer) gl.uniform2f(u.pointer, pointer.x, pointer.y);
      if (u.pointerAmount) gl.uniform1f(u.pointerAmount, pointer.amount);
      if (u.chaosTime) gl.uniform1f(u.chaosTime, chaosTime);
      if (u.ripples) gl.uniform3fv(u.ripples, rippleBuffer);
    };

    let startTime = performance.now();
    let lastTime = startTime;

    const render = (now: number) => {
      animFrameId = requestAnimationFrame(render);
      const dt = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      // Smooth pointer interpolation
      const lerpFactor = 1 - Math.exp(-9 * dt);
      pointer.x += (pointer.targetX - pointer.x) * lerpFactor;
      pointer.y += (pointer.targetY - pointer.y) * lerpFactor;
      pointer.amount += (pointer.targetAmount - pointer.amount) * (1 - Math.exp(-5 * dt));

      // Clean old ripples
      for (let i = ripples.length - 1; i >= 0; i--) {
        if ((now - ripples[i].bornMs) / 1000 > RIPPLE_LIFETIME_SEC) {
          ripples.splice(i, 1);
        }
      }
      rippleBuffer.fill(0);
      for (let i = 0; i < MAX_RIPPLES_COUNT; i++) {
        const r = ripples[i];
        rippleBuffer[i * 3] = r ? r.x : 0;
        rippleBuffer[i * 3 + 1] = r ? r.y : 0;
        rippleBuffer[i * 3 + 2] = r ? (now - r.bornMs) / 1000 : -1;
      }

      if (!renderTargets.length || !renderTargets[0].framebuffer) return;

      const elapsed = (now - startTime) / 1000;
      const chaosTime = elapsed * speed;

      gl.bindVertexArray(vao);
      gl.viewport(0, 0, width, height);

      // PASS 1: BEAM
      gl.useProgram(programs.beam);
      setCommonUniforms('beam', chaosTime);
      gl.uniform3f(
        uniforms.beam.thickness,
        BASE_THICKNESS[0] * beamWidth,
        BASE_THICKNESS[1] * beamWidth,
        BASE_THICKNESS[2] * beamWidth
      );
      gl.uniform1f(uniforms.beam.time, elapsed * BEAM_SPEED_MULT * speed);
      gl.uniform1i(uniforms.beam.shape, SHAPE_MAP[variant] ?? 0);
      gl.bindFramebuffer(gl.FRAMEBUFFER, renderTargets[0].framebuffer);
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      // PASS 2: ATMOSPHERE
      gl.useProgram(programs.atmosphere);
      setCommonUniforms('atmosphere', chaosTime);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, renderTargets[0].texture);
      gl.uniform1i(uniforms.atmosphere.scene, 0);
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, noiseTexture);
      gl.uniform1i(uniforms.atmosphere.blueNoise, 1);
      gl.uniform2f(uniforms.atmosphere.resolution, width, height);
      gl.uniform1f(uniforms.atmosphere.time, elapsed * ATMOSPHERE_SPEED_MULT * speed);
      gl.uniform1f(uniforms.atmosphere.noiseScale, noiseScale * dpr);
      gl.uniform1f(uniforms.atmosphere.ditherStep, dither);
      gl.bindFramebuffer(gl.FRAMEBUFFER, renderTargets[1].framebuffer);
      gl.drawArrays(gl.TRIANGLES, 0, 3);

      // PASS 3: GLYPH MATRIX
      gl.useProgram(programs.glyph);
      setCommonUniforms('glyph', chaosTime);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, renderTargets[1].texture);
      gl.uniform1i(uniforms.glyph.scene, 0);
      gl.uniform2f(uniforms.glyph.resolution, width, height);
      gl.uniform1f(uniforms.glyph.gridSize, (glyphSize * dpr) / height);
      gl.uniform1f(uniforms.glyph.glyphAmount, glyphAmount);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    animFrameId = requestAnimationFrame(render);

    // Pointer handlers
    const handlePointerMove = (e: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const x = (e.clientX - rect.left) / rect.width;
      const y = 1 - (e.clientY - rect.top) / rect.height;
      const near =
        e.clientX >= rect.left - PROXIMITY_PX &&
        e.clientX <= rect.right + PROXIMITY_PX &&
        e.clientY >= rect.top - PROXIMITY_PX &&
        e.clientY <= rect.bottom + PROXIMITY_PX;

      pointer.targetX = x;
      pointer.targetY = y;
      pointer.targetAmount = near ? 1.0 : 0.0;
    };

    const handlePointerDown = (e: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const x = (e.clientX - rect.left) / rect.width;
      const y = 1 - (e.clientY - rect.top) / rect.height;
      pointer.targetX = x;
      pointer.targetY = y;
      ripples.push({ x, y, bornMs: performance.now() });
      if (ripples.length > MAX_RIPPLES_COUNT) ripples.shift();
    };

    const handlePointerLeave = () => {
      pointer.targetAmount = 0.0;
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    window.addEventListener('pointerdown', handlePointerDown, { passive: true });
    document.addEventListener('pointerleave', handlePointerLeave);
    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(animFrameId);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('pointerleave', handlePointerLeave);
      window.removeEventListener('resize', resize);
      renderTargets.forEach((rt) => {
        if (rt.texture) gl.deleteTexture(rt.texture);
        if (rt.framebuffer) gl.deleteFramebuffer(rt.framebuffer);
      });
      if (noiseTexture) gl.deleteTexture(noiseTexture);
      if (vao) gl.deleteVertexArray(vao);
      Object.values(programs).forEach((p) => gl.deleteProgram(p));
    };
  }, [variant, speed, beamWidth, dither, glyphSize, glyphAmount, noiseScale]);

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden ${className}`}
    >
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  );
};

export default MatrixJunctionLaserBackground;
