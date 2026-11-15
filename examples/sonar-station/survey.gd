extends ColorRect

const CHART = preload("res://chart.gdshader")
const STATIONS = [Vector2(.30,.29), Vector2(.69,.35), Vector2(.47,.73)]
const NAMES = ["A1", "B2", "C3"]
var cursor := Vector2(.52,.49)
var scan_origin := Vector2.ZERO
var scan_radius := 0.0
var heading := Vector2.UP
var scan_heading := Vector2.UP
var aperture := TAU
var scan_phase := -1.0
var surveyed: Dictionary = {}
var last_sounding := -1
var preview_radius := 0.0
var preview_arc := 0.0
var fitted_radius := 0.0
var fitted_arc := 0.0
var paper := false
var graphic_font: Font
var symbols := Control.new()

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var surface := ShaderMaterial.new()
	surface.shader = CHART
	material = surface
	add_child(symbols)
	symbols.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	symbols.mouse_filter = Control.MOUSE_FILTER_IGNORE
	symbols.draw.connect(draw_symbols.bind(symbols))
	resized.connect(_resize_surface)
	_resize_surface()

func _resize_surface() -> void:
	material.set_shader_parameter("chart_size", size)
	symbols.queue_redraw()

func set_light_chart(value: bool) -> void:
	paper = value
	material.set_shader_parameter("paper", value)
	symbols.queue_redraw()

func water_depth(p: Vector2) -> int:
	var v := 73.0 - 61.0 * _hill(p, Vector2(.16,.30),Vector2(.24,.19))
	v -= 50.0 * _hill(p,Vector2(.24,.58),Vector2(.19,.16))
	v += 49.0 * _hill(p,Vector2(.65,.50),Vector2(.27,.25))
	v -= 73.0 * _hill(p,Vector2(.89,.77),Vector2(.26,.22))
	return roundi(maxf(.5, v + 7.0*sin(p.x*19.0+sin(p.y*17.0)) + 4.5*cos(p.y*23.0 + 3.0*p.x)))

func _hill(p: Vector2, centre: Vector2, radius: Vector2) -> float:
	return exp(-((p-centre)/radius).length_squared())

func move_to(p: Vector2) -> void:
	var next := p.clamp(Vector2(.035,.065),Vector2(.965,.925))
	var displacement := (next-cursor)*size
	if displacement.length_squared() > .001:
		heading = displacement.normalized()
	cursor = next
	symbols.queue_redraw()

func set_probe_preview(candidate: Dictionary, fitted: Dictionary, pixels_per_metre: float) -> void:
	preview_radius = candidate.radius * pixels_per_metre
	preview_arc = deg_to_rad(candidate.arc)
	fitted_radius = fitted.radius * pixels_per_metre
	fitted_arc = deg_to_rad(fitted.arc)
	symbols.queue_redraw()

func clear_probe_preview() -> void:
	preview_radius = 0
	symbols.queue_redraw()

func _draw_coverage(layer: Control, center: Vector2, radius: float, arc: float, col: Color, dashed: bool) -> void:
	var start := heading.angle() - arc*.5
	var end := start + arc
	var points := PackedVector2Array()
	for i in 97:
		points.append(center + Vector2.from_angle(lerpf(start,end,i/96.0)) * radius)
	if dashed:
		for i in 96:
			if i % 4 < 2: layer.draw_line(points[i],points[i+1],col,2.0,true)
		if arc < TAU-.001:
			layer.draw_dashed_line(center,points[0],col,1.5,6)
			layer.draw_dashed_line(center,points[-1],col,1.5,6)
	else:
		var fill := points.duplicate()
		if arc < TAU-.001: fill.append(center)
		layer.draw_colored_polygon(fill,Color(col,.13))
		layer.draw_polyline(points,col,2.2,true)
		if arc < TAU-.001:
			layer.draw_line(center,points[0],col,2,true)
			layer.draw_line(center,points[-1],col,2,true)

func covers_station(i: int, radius: float, arc: float) -> bool:
	var offset: Vector2 = (STATIONS[i] - cursor) * size
	return offset.length() <= radius and (offset.length_squared() < .001 or absf(heading.angle_to(offset)) <= arc*.5)

func covered_ids(radius: float, arc: float) -> PackedStringArray:
	var ids := PackedStringArray()
	for i in STATIONS.size():
		if covers_station(i,radius,arc): ids.append(NAMES[i])
	return ids

func record_scan(radius: float, degrees: float, reduced: bool) -> int:
	scan_origin = cursor
	last_sounding = water_depth(scan_origin)
	scan_heading = heading
	aperture = deg_to_rad(degrees)
	scan_radius = radius
	scan_phase = -1.0 if reduced else 0.0
	var previous := surveyed.size()
	for i in STATIONS.size():
		if covers_station(i,radius,aperture):
			surveyed[i] = true
	symbols.queue_redraw()
	return surveyed.size() - previous

func advance_scan(delta: float) -> void:
	if scan_phase < 0.0:
		return
	scan_phase += delta / .70
	if scan_phase >= 1.0:
		scan_phase = -1.0
	symbols.queue_redraw()

func draw_symbols(layer: Control) -> void:
	var line := Color("#e1e8f1") if not paper else Color("#253751")
	var accent := Color("#ffad72") if not paper else Color("#913c25")
	var stroke := Color("#18243a") if not paper else Color("#f1ebdc")
	var here := cursor * size
	if preview_radius > 0:
		_draw_coverage(layer,here,preview_radius,preview_arc,accent,false)
		_draw_coverage(layer,here,fitted_radius,fitted_arc,Color(line,.85),true)
	for i in STATIONS.size():
		var at: Vector2 = STATIONS[i] * size
		var label_at := at
		if here.distance_to(at) < 53:
			label_at += Vector2(-44, -34)
			layer.draw_line(at+Vector2(-12,-10),label_at,line,1.0,true)
		if surveyed.has(i):
			layer.draw_circle(label_at, 6, line, true, -1, true)
			layer.draw_polyline(PackedVector2Array([label_at+Vector2(-3,0),label_at+Vector2(-1,2),label_at+Vector2(3,-3)]), stroke, 1.4, true)
		else:
			layer.draw_rect(Rect2(label_at-Vector2(5,5),Vector2(10,10)),stroke)
			layer.draw_rect(Rect2(label_at-Vector2(4,4),Vector2(8,8)), line, false, 1.5, true)
		if preview_radius > 0:
			if covers_station(i,preview_radius,preview_arc):
				layer.draw_arc(label_at,10,0,TAU,36,accent,2.5,true)
			elif covers_station(i,fitted_radius,fitted_arc):
				for k in 4:
					layer.draw_arc(label_at,10,k*PI*.5,k*PI*.5+PI*.27,10,line,2.0,true)
		layer.draw_string_outline(graphic_font,label_at+Vector2(13,5),NAMES[i],HORIZONTAL_ALIGNMENT_LEFT,-1,15,3,stroke)
		layer.draw_string(graphic_font,label_at+Vector2(13,5),NAMES[i],HORIZONTAL_ALIGNMENT_LEFT,-1,15,line)
	if scan_phase >= 0.0:
		var r := lerpf(8.0,scan_radius,1.0-pow(1.0-scan_phase,1.5))
		layer.draw_arc(scan_origin*size,r,scan_heading.angle()-aperture*.5,scan_heading.angle()+aperture*.5,128,Color(accent,.85*(1-scan_phase)),2,true)
	layer.draw_arc(here, 29, 0, TAU, 72, Color(line,.62), 1.4, true)
	for angle in [0.0,PI*.5,PI,PI*1.5]:
		var n := Vector2.from_angle(angle)
		layer.draw_line(here+n*23,here+n*35,line,1.6,true)
	var side := Vector2(-heading.y,heading.x)
	var hull := PackedVector2Array([here+heading*13, here-heading*11+side*9, here-heading*6, here-heading*11-side*9])
	layer.draw_colored_polygon(hull,accent)
	layer.draw_polyline(PackedVector2Array([hull[0],hull[1],hull[2],hull[3],hull[0]]),stroke,1.4,true)
	if last_sounding >= 0:
		var origin := scan_origin * size
		var label_pos := origin + Vector2(45, -24)
		if label_pos.x > size.x - 88: label_pos.x = origin.x - 85
		if label_pos.y < 44: label_pos.y = origin.y + 49
		var side_x := 1.0 if label_pos.x > origin.x else -1.0
		layer.draw_line(origin+Vector2(18*side_x,-7),label_pos+Vector2(0,4),accent,1.1,true)
		var reading := "%d m" % last_sounding
		layer.draw_string_outline(graphic_font,label_pos,reading,HORIZONTAL_ALIGNMENT_LEFT,-1,23,4,stroke)
		layer.draw_string(graphic_font,label_pos,reading,HORIZONTAL_ALIGNMENT_LEFT,-1,23,accent)
	# Chart soundings carry real chart values and stay behind the HUD.
	for p in [Vector2(.16,.47),Vector2(.43,.23),Vector2(.77,.61),Vector2(.58,.80),Vector2(.83,.28)]:
		if ((p - cursor)*size).length() > 54 and (last_sounding < 0 or ((p - scan_origin)*size).length() > 85):
			layer.draw_string(graphic_font,p*size,str(water_depth(p)),HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color(line,.75))
