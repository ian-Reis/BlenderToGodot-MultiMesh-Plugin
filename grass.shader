shader_type spatial;
// Grama para Godot 3.6 - vento + alpha scissor + fade por distancia (dither)
// Pipeline OPACO: rapido, sem problemas de ordenacao com milhares de tufos.

render_mode cull_disabled;

uniform sampler2D texture_albedo : hint_albedo;
uniform vec4 tint : hint_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float alpha_scissor : hint_range(0.0, 1.0) = 0.5;

// --- Vento ---
uniform vec2  wind_direction = vec2(1.0, 0.3);
uniform float wind_speed     = 1.5;
uniform float wind_strength  = 0.15;
uniform float wind_scale     = 0.25;
uniform float wind_height    = 1.0;   // altura aprox. da grama (mascara base->topo)

// --- Fade por distancia ---
uniform float fade_start = 40.0;
uniform float fade_end   = 70.0;

void vertex() {
	float mask = clamp(VERTEX.y / max(wind_height, 0.001), 0.0, 1.0);
	vec3 world = (WORLD_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float phase = dot(world.xz, wind_direction) * wind_scale + TIME * wind_speed;
	float sway = sin(phase) * wind_strength * mask;
	vec2 dir = normalize(wind_direction);
	VERTEX.x += sway * dir.x;
	VERTEX.z += sway * dir.y;
}

void fragment() {
	vec4 tex = texture(texture_albedo, UV);
	ALBEDO = tex.rgb * tint.rgb;
	ROUGHNESS = 1.0;
	SPECULAR = 0.1;

	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}

	float dist = length(VERTEX);
	float fade = clamp((fade_end - dist) / max(fade_end - fade_start, 0.001), 0.0, 1.0);
	float d = fract(sin(dot(FRAGCOORD.xy, vec2(12.9898, 78.233))) * 43758.5453);

	if (tex.a < alpha_scissor || d > fade) {
		discard;
	}
	ALPHA = 1.0;
}
