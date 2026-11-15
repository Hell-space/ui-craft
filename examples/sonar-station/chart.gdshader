shader_type canvas_item;
render_mode unshaded;

uniform bool paper = false;
uniform vec2 chart_size = vec2(1120.0, 680.0);

// Normalized survey coordinates are shared with the depth readout.
float hill(vec2 p, vec2 c, vec2 rad) {
  vec2 d = (p-c)/rad;
  return exp(-dot(d,d));
}
float depth_m(vec2 p) {
  float v = 73.0 - 61.0*hill(p,vec2(.16,.30),vec2(.24,.19))
    - 50.0*hill(p,vec2(.24,.58),vec2(.19,.16))
    + 49.0*hill(p,vec2(.65,.50),vec2(.27,.25))
    - 73.0*hill(p,vec2(.89,.77),vec2(.26,.22));
  return v + 7.0*sin(p.x*19.0 + sin(p.y*17.0)) + 4.5*cos(p.y*23.0 + 3.0*p.x);
}
float contour(float v) {
  float distance_to_line = abs(fract(v+.5)-.5);
  float scale = max(fwidth(v),.001);
  return 1.0-smoothstep(scale*.15,scale*1.05,distance_to_line);
}
void fragment() {
  float depth = depth_m(UV);
  float shade = smoothstep(0.0,119.0,depth);
  vec3 base = paper ? mix(vec3(.94,.90,.81),vec3(.66,.75,.84),shade)
                    : mix(vec3(.21,.29,.42),vec3(.055,.088,.16),shade);
  base += (fract(depth/12.0)-.5) * (paper ? .020 : .028);
  vec3 ink = paper ? vec3(.29,.35,.43) : vec3(.51,.62,.77);
  float thin = contour(depth/3.0), heavy = contour(depth/12.0);
  base = mix(base, ink, .15*thin+.42*heavy);
  vec2 grid = UV*vec2(12.0,8.0);
  float mesh = max(contour(grid.x),contour(grid.y));
  base = mix(base,ink,mesh*.17);
  float grit = fract(sin(dot(floor(UV*chart_size),vec2(12.9898,78.233)))*43758.5453);
  COLOR=vec4(base+(grit-.5)*.022,1.0);
}
