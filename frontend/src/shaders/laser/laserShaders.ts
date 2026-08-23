export const LASER_VERTEX_SHADER = `
attribute vec2 a_position;

void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

export const LASER_FRAGMENT_SHADER = `
precision highp float;

uniform vec2 u_resolution;
uniform vec2 u_pointer;
uniform float u_time;
uniform float u_variant;
uniform float u_size;
uniform float u_length;
uniform float u_density;
uniform float u_hue;
uniform float u_saturation;
uniform float u_brightness;

float hash21(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float valueNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
    mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0)), u.x),
    u.y
  );
}

float fbm(vec2 p) {
  float result = 0.0;
  float weight = 0.54;
  for (int i = 0; i < 4; i++) {
    result += valueNoise(p) * weight;
    p = mat2(1.62, 1.21, -1.21, 1.62) * p + 9.13;
    weight *= 0.48;
  }
  return result;
}

vec3 hsv2rgb(vec3 c) {
  vec3 p = abs(fract(c.xxx + vec3(0.0, 0.6666667, 0.3333333)) * 6.0 - 3.0);
  return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

// 👑 GOLD ACCENT PALETTE (Warm 24k Gold & Amber tones)
vec3 accent(float baseHue, float saturationScale) {
  float hue = fract(baseHue + u_hue / 360.0);
  return hsv2rgb(vec3(hue, clamp(u_saturation * saturationScale, 0.0, 1.0), 1.0));
}

vec2 laserProfile(float distanceToLine, float coreWidth, float glowWidth) {
  float core = exp(-pow(distanceToLine / max(coreWidth, 0.0002), 2.0));
  float glow = exp(-pow(distanceToLine / max(glowWidth, 0.001), 1.25));
  return vec2(core, glow);
}

// 1. Atmospheric Blade (Gold & Obsidian)
vec3 atmosphericBlade(vec2 p) {
  float drift = sin(u_time * 0.21) * 0.025;
  float center = u_pointer.x * 0.16 + drift;
  float tilt = u_pointer.x * 0.055 + sin(u_time * 0.13) * 0.018;
  float distanceToBeam = abs(p.x - center - p.y * tilt);
  float verticalMask = 1.0 - smoothstep(0.68 * u_length, 1.35 * u_length, abs(p.y));
  vec2 beam = laserProfile(distanceToBeam, 0.0028 * u_size, 0.052 * u_size);

  vec2 fogUv = vec2(p.x * 3.4, p.y * 2.15 - u_time * 0.075);
  fogUv.x += sin(p.y * 3.2 - u_time * 0.17) * 0.18;
  float fogNoise = fbm(fogUv + u_pointer * 0.35);
  float fogEnvelope = exp(-pow(distanceToBeam / (0.24 * u_size), 1.35));
  float fog = smoothstep(0.34, 0.78, fogNoise) * fogEnvelope * u_density * verticalMask;

  float mirageDistance = abs(abs(p.x - center + p.y * tilt * 0.35) - 0.105 * u_length);
  vec2 mirage = laserProfile(mirageDistance, 0.0011 * u_size, 0.016 * u_size);
  float mirageMask = (1.0 - smoothstep(0.08, 1.2, abs(p.y))) * (0.35 + 0.65 * fogNoise);

  vec3 tint = accent(0.12, 0.85); // 24k Gold
  vec3 color = vec3(0.006, 0.005, 0.002);
  color += tint * fog * 0.38;
  color += tint * beam.y * verticalMask * (0.52 + 0.08 * sin(u_time * 1.1));
  color += mix(tint, vec3(1.0, 0.98, 0.9), 0.88) * beam.x * verticalMask * 1.75;
  color += tint * mirage.y * mirageMask * 0.14 * u_density;
  color += vec3(1.0, 0.92, 0.65) * mirage.x * mirageMask * 0.4 * u_density;

  float contact = exp(-length(vec2((p.x - center) * 2.5, p.y + 0.77 * u_length)) * 7.0);
  color += tint * contact * 0.55;
  return color;
}

// 2. Vanishing Array (Gold & Obsidian)
vec3 vanishingArray(vec2 p) {
  vec2 origin = vec2(u_pointer.x * 0.16, 0.12 + u_pointer.y * 0.075);
  vec2 q = p - origin;
  float radius = length(q);
  float angle = atan(q.y, q.x);
  float spokeCount = floor(11.0 + u_density * 10.0);
  float angularDistance = abs(sin(angle * spokeCount));
  float spoke = exp(-angularDistance * max(radius, 0.06) / (0.0075 * u_size));
  float reach = smoothstep(0.035, 0.16, radius) * (1.0 - smoothstep(0.42 * u_length, 1.55 * u_length, radius));
  float lowerField = 1.0 - smoothstep(-0.12, 0.22, q.y);
  float upperField = smoothstep(0.02, 0.52, q.y) * 0.48;
  float fieldMask = max(lowerField, upperField);

  float carrier = 0.55 + 0.45 * sin(radius * 16.0 - u_time * 4.1 + angle * 2.0);
  carrier = pow(max(carrier, 0.0), 7.0);
  float rail = spoke * reach * fieldMask;
  float railCore = pow(rail, 2.1);

  float ringPhase = abs(sin((radius * 13.0 - u_time * 1.5) / max(u_length, 0.35)));
  float rings = exp(-ringPhase / (0.035 * u_size)) * (1.0 - smoothstep(0.1, 1.2, radius)) * lowerField;
  float horizon = exp(-abs(q.y) / (0.0035 * u_size)) * (1.0 - smoothstep(0.12, 1.15, abs(q.x)));

  vec3 gold = accent(0.12, 0.88);   // Pure Gold
  vec3 amber = accent(0.08, 0.95);  // Warm Radiant Amber
  vec3 railTint = mix(gold, amber, 0.5 + 0.5 * sin(angle * 3.0));
  vec3 color = vec3(0.006, 0.004, 0.002);
  color += railTint * rail * (0.26 + carrier * 0.76);
  color += mix(railTint, vec3(1.0, 0.98, 0.9), 0.9) * railCore * (0.56 + carrier * 0.95);
  color += gold * rings * 0.16 * u_density;
  color += vec3(1.0, 0.95, 0.8) * horizon * 0.42;
  color += gold * exp(-radius * 15.0) * 1.05;
  return color;
}

// 3. Prism Aperture (Gold & Obsidian)
vec3 prismAperture(vec2 p) {
  vec2 center = u_pointer * vec2(0.12, 0.08);
  vec2 q = p - center;
  float breathing = 0.46 * u_length + sin(u_time * 0.72) * 0.012;
  float warp = (fbm(q * 3.2 + vec2(0.0, -u_time * 0.08)) - 0.5) * 0.025 * u_density;
  float diamond = abs(q.x * 0.82) + abs(q.y) - breathing - warp;
  float innerDiamond = abs(q.x * 0.82) + abs(q.y) - breathing * 0.66 + warp * 0.45;
  vec2 outer = laserProfile(abs(diamond), 0.0024 * u_size, 0.046 * u_size);
  vec2 inner = laserProfile(abs(innerDiamond), 0.0012 * u_size, 0.018 * u_size);

  float edgeMask = 1.0 - smoothstep(0.25, 1.18, length(q));
  float perimeterPhase = sin((q.x - q.y) * 15.0 - u_time * 3.3);
  float packets = pow(max(perimeterPhase, 0.0), 10.0) * outer.y;
  float axisX = exp(-abs(q.x) / (0.002 * u_size)) * (1.0 - smoothstep(0.04, breathing, abs(q.y)));
  float axisY = exp(-abs(q.y) / (0.002 * u_size)) * (1.0 - smoothstep(0.04, breathing, abs(q.x)));

  float redFringe = exp(-pow(abs(diamond - 0.011 * u_size) / (0.011 * u_size), 1.4));
  float blueFringe = exp(-pow(abs(diamond + 0.011 * u_size) / (0.011 * u_size), 1.4));
  vec3 tint = accent(0.12, 0.85);
  vec3 color = vec3(0.006, 0.004, 0.002);
  color += tint * outer.y * edgeMask * 0.54;
  color += mix(tint, vec3(1.0, 0.98, 0.88), 0.9) * outer.x * edgeMask * 1.55;
  color += tint * inner.y * edgeMask * 0.2 * u_density;
  color += vec3(1.0, 0.95, 0.85) * inner.x * edgeMask * 0.52 * u_density;
  color += accent(0.06, 0.95) * redFringe * 0.15;   // warm amber fringe
  color += accent(0.15, 0.85) * blueFringe * 0.18;  // lime-gold fringe
  color += vec3(1.0, 0.96, 0.85) * (axisX + axisY) * 0.22;
  color += tint * packets * 0.9;
  color += tint * exp(-length(q) * 9.0) * 0.25;
  return color;
}

// 4. Halftone Relay (Gold & Obsidian)
vec3 halftoneRelay(vec2 p) {
  float center = 0.29 + u_pointer.x * 0.12;
  float bend = sin(p.y * 2.1 - u_time * 0.25) * 0.018;
  float mainDistance = abs(p.x - center - bend);
  float relayDistance = abs(p.x - center + 0.075 * u_length + bend * 0.45);
  vec2 mainBeam = laserProfile(mainDistance, 0.0022 * u_size, 0.072 * u_size);
  vec2 relayBeam = laserProfile(relayDistance, 0.0012 * u_size, 0.025 * u_size);

  vec2 fogUv = vec2(p.x * 3.0, p.y * 2.5 - u_time * 0.1);
  float fogNoise = fbm(fogUv + vec2(sin(u_time * 0.16), 0.0));
  float fog = smoothstep(0.28, 0.78, fogNoise) * exp(-mainDistance * 9.5 / u_size) * u_density;

  float dotScale = mix(9.0, 4.5, clamp((u_density - 0.25) / 2.25, 0.0, 1.0));
  vec2 dotCell = fract(gl_FragCoord.xy / dotScale) - 0.5;
  float dot = 1.0 - smoothstep(0.08, 0.34, length(dotCell));
  float dotMask = dot * smoothstep(0.08, 0.68, fog + mainBeam.y * 0.65);

  float pulse = pow(max(0.0, sin(p.y * 9.0 - u_time * 4.0)), 12.0);
  float horizontalRelay = exp(-abs(p.y + 0.34 - u_pointer.y * 0.08) / (0.0024 * u_size));
  horizontalRelay *= 1.0 - smoothstep(0.1, 1.05 * u_length, abs(p.x - center));

  vec3 tint = accent(0.12, 0.88); // 24k Gold
  vec3 color = vec3(0.005, 0.004, 0.002);
  color += tint * fog * 0.26;
  color += tint * mainBeam.y * 0.58;
  color += mix(tint, vec3(1.0, 0.98, 0.9), 0.9) * mainBeam.x * 1.55;
  color += tint * relayBeam.y * 0.22;
  color += vec3(1.0, 0.95, 0.8) * relayBeam.x * 0.55;
  color += tint * dotMask * (0.32 + pulse * 0.45);
  color += mix(tint, vec3(1.0, 0.98, 0.9), 0.8) * horizontalRelay * (0.24 + pulse * 0.62);
  return color;
}

void main() {
  vec2 p = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / min(u_resolution.x, u_resolution.y);
  vec3 color;

  if (u_variant < 0.5) {
    color = atmosphericBlade(p);
  } else if (u_variant < 1.5) {
    color = vanishingArray(p);
  } else if (u_variant < 2.5) {
    color = prismAperture(p);
  } else {
    color = halftoneRelay(p);
  }

  float vignette = 1.0 - smoothstep(0.24, 1.45, length(p * vec2(0.72, 0.88)));
  color *= 0.55 + vignette * 0.45;
  color *= u_brightness;
  color = color / (color + vec3(0.72));
  color = pow(max(color, vec3(0.0)), vec3(0.82));
  gl_FragColor = vec4(color, 1.0);
}
`;
