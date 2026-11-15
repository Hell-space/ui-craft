extends Node2D

const WALK_SPEED := 80.0
const PLAYER_RADIUS := 3.5
const WINCH_REACH := 31.0
const CABLE_RATE := 1.36
const INK := Color("#2e4644")
const EDGE := Color("#decba0")

var layout: Dictionary
var deck_left: PackedVector2Array
var deck_right: PackedVector2Array
var hinge: Vector2
var winch: Vector2
var bridge_length: float
var bridge_front: float
var raised_angle: float
var feet: Vector2
var lowered := false
var travel := 0.0
var evening := false
var gear_visible := true
var facing := 1
var stride := 0.0
var walking := false
var tide_clock := 0.0
var backdrops: Array[Texture2D] = []
var equipment: Array[Texture2D] = []
var hint_font: SystemFont
@onready var canvas: Node2D = $Screen/Pixels/Artwork


func _ready() -> void:
	layout = JSON.parse_string(FileAccess.get_file_as_string("res://layout.json"))
	deck_left = points(layout.left_quay)
	deck_right = points(layout.right_quay)
	var bridge: Dictionary = layout.bridge
	hinge = Vector2(bridge.hinge_x, bridge.back_y)
	bridge_length = bridge.length
	bridge_front = bridge.front_y
	raised_angle = deg_to_rad(bridge.raised_angle)
	winch = pair(layout.winch)
	feet = pair(layout.spawn)
	# Embedded PNGs also run directly from a fresh source folder with godot --path.
	for file in ["harbor.png", "harbor_evening.png"]:
		backdrops.append(read_art(file))
	for file in ["gear.png", "gear_evening.png"]:
		equipment.append(read_art(file))
	setup_controls()
	hint_font = SystemFont.new()
	hint_font.font_names = PackedStringArray(["Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei"])
	canvas.draw.connect(paint_yard)
	canvas.queue_redraw()


func pair(value: Array) -> Vector2:
	return Vector2(value[0], value[1])


func points(raw: Array) -> PackedVector2Array:
	var output := PackedVector2Array()
	for p in raw:
		output.append(pair(p))
	return output


func read_art(filename: String) -> Texture2D:
	# Godot's exporter remaps imported textures, while a fresh CLI checkout has no import cache.
	var path := "res://art/" + filename
	if ResourceLoader.exists(path) and FileAccess.file_exists(path + ".import"):
		var asset := ResourceLoader.load(path) as Texture2D
		if asset != null:
			return asset
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("无法打开场景图层 " + path)
		return null
	var pixels := Image.new()
	var status := pixels.load_png_from_buffer(file.get_buffer(file.get_length()))
	if status != OK:
		push_error("无法读取 PNG " + path)
		return null
	return ImageTexture.create_from_image(pixels)


func setup_controls() -> void:
	var bindings := {
		"yard_left": [KEY_A, KEY_LEFT], "yard_right": [KEY_D, KEY_RIGHT],
		"yard_up": [KEY_W, KEY_UP], "yard_down": [KEY_S, KEY_DOWN],
		"yard_winch": [KEY_E, KEY_SPACE], "yard_gear": [KEY_F2], "yard_light": [KEY_F3]
	}
	for action: String in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			for code: Key in bindings[action]:
				var key := InputEventKey.new()
				key.physical_keycode = code
				InputMap.action_add_event(action, key)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("yard_winch"):
		if in_reach() and (is_zero_approx(travel) or is_equal_approx(travel, 1.0)):
			lowered = not lowered
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("yard_gear"):
		gear_visible = not gear_visible
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("yard_light"):
		evening = not evening
		get_viewport().set_input_as_handled()


func in_reach() -> bool:
	return feet.distance_to(winch) <= WINCH_REACH


func bridge_walkable() -> bool:
	return lowered and is_equal_approx(travel, 1.0)


func has_plank(p: Vector2) -> bool:
	if Geometry2D.is_point_in_polygon(p, deck_left) or Geometry2D.is_point_in_polygon(p, deck_right):
		return true
	return bridge_walkable() and p.x >= hinge.x - bridge_length and p.x <= hinge.x and p.y >= hinge.y and p.y <= bridge_front


func can_stand(p: Vector2) -> bool:
	# Feet, not the sprite's cap, define the footprint. Test the union across the hinge seam.
	if p.x < 4 or p.x > 635:
		return false
	for probe in [Vector2.ZERO, Vector2.RIGHT, Vector2.LEFT, Vector2.UP, Vector2.DOWN,
			Vector2(0.707,0.707), Vector2(-0.707,0.707), Vector2(0.707,-0.707), Vector2(-0.707,-0.707)]:
		if not has_plank(p + probe * PLAYER_RADIUS):
			return false
	return true


func _physics_process(delta: float) -> void:
	tide_clock += delta
	travel = move_toward(travel, 1.0 if lowered else 0.0, delta * CABLE_RATE)
	var aim := Input.get_vector("yard_left", "yard_right", "yard_up", "yard_down")
	if absf(aim.x) > 0.05:
		facing = 1 if aim.x > 0 else -1
	var old := feet
	var motion := aim * WALK_SPEED * delta
	if can_stand(feet + Vector2(motion.x, 0)):
		feet.x += motion.x
	if can_stand(feet + Vector2(0, motion.y)):
		feet.y += motion.y
	walking = feet.distance_squared_to(old) > 0.0001
	if walking:
		stride = fmod(stride + delta * 8.2, TAU)
	canvas.queue_redraw()


func rect(x: float, y: float, w: float, h: float, fill: Color) -> void:
	canvas.draw_rect(Rect2(roundf(x), roundf(y), w, h), fill)


func segment(a: Vector2, b: Vector2, color: Color, width := 1.0) -> void:
	canvas.draw_line(a.round(), b.round(), color, width, false)


func shape(vertices: Array, color: Color) -> void:
	var pts := PackedVector2Array()
	for vertex: Vector2 in vertices:
		pts.append(vertex.round())
	canvas.draw_colored_polygon(pts, color)


func ellipse(center: Vector2, rx: float, ry: float, color: Color) -> void:
	for y in range(-roundi(ry), roundi(ry) + 1):
		var dx := roundi(rx * sqrt(maxf(0, 1.0 - (y*y)/(ry*ry))))
		rect(center.x-dx, center.y+y, 2*dx+1, 1, color)


func lit(day: Color, low: Color) -> Color:
	return low if evening else day


func paint_yard() -> void:
	if backdrops.is_empty():
		return
	var index := 1 if evening else 0
	canvas.draw_texture(backdrops[index], Vector2.ZERO)
	draw_water()
	if gear_visible:
		canvas.draw_texture(equipment[index], Vector2.ZERO)
	draw_bridge()
	draw_winch()
	draw_worker()
	if in_reach() and (is_zero_approx(travel) or is_equal_approx(travel, 1.0)):
		draw_hint()


func draw_water() -> void:
	# Short gleams wander parallel to the water. Keep the open bridge channel legible.
	for i in range(53):
		var row := 121 + (i * 37) % 205
		var x := fposmod(i * 83 + sin(i * 9.2 + tide_clock * 0.56) * (1 + row * 0.022), 640)
		if row >= 168 and row < 252:
			if x < 339 or x > 395:
				continue
		if row < 166 and (x < 175 or x > 505):
			continue
		var phase := sin(i * 34.12 + tide_clock * 1.18)
		if phase > 0.0:
			var ink := lit(Color("#bfd0b4"), Color("#8ca7a1"))
			ink.a = 0.14 + 0.22 * phase
			rect(x, row, 2 + roundf((0.4+phase) * (row-107)/44.0), 1, ink)


func bridge_point(distance: float, depth: float) -> Vector2:
	var eased := smoothstep(0.0, 1.0, travel)
	var angle := raised_angle * (1.0 - eased)
	return hinge + Vector2(-distance*cos(angle), depth-distance*sin(angle)*0.74)


func draw_bridge() -> void:
	var width := bridge_front - hinge.y
	var a := bridge_point(0, 0)
	var b := bridge_point(bridge_length, 0)
	var c := bridge_point(bridge_length, width)
	var d := bridge_point(0, width)
	var tip := bridge_point(bridge_length, 0)
	var high_anchor := Vector2(428,158)
	var on_edge := Vector2(-1, 1)
	var shadow := lit(Color("#344f4a"), Color("#263e44"))
	var iron := lit(Color("#506358"), Color("#455f62"))
	var timber := lit(Color("#ab9873"), Color("#697e78"))
	var grain := lit(Color("#877d60"), Color("#556e6b"))
	var lip := lit(Color("#e2d0a3"), Color("#acb39b"))
	# Cable bends over the roller on the bank; the free end is attached to the leading corner.
	segment(Vector2(421,211), high_anchor, iron, 3)
	segment(Vector2(435,211), high_anchor + Vector2(2,2), iron, 3)
	segment(Vector2(422,204), high_anchor + Vector2(-1,2), lip)
	segment(Vector2(421,190), Vector2(430,178), iron, 2)
	canvas.draw_circle(high_anchor.round(), 3.0, shadow)
	rect(427,156,2,2,lip)
	segment(high_anchor, tip, shadow)
	segment(high_anchor+on_edge, tip+on_edge, lit(Color("#a39e7f"), Color("#82938b")))
	# The cable returns above the rear edge of the left apron, never crossing the walk lane.
	draw_hanging_line(Vector2(winch.x+7,winch.y-8), high_anchor, 13.0, iron)
	shape([a,b,c,d], timber)
	for i in range(11):
		var start := i * bridge_length / 11.0
		var end := (i+1) * bridge_length / 11.0
		var tone := grain.lerp(timber, [0.85, 0.54, 0.97, 0.73, 0.65][i%5])
		shape([bridge_point(start,0),bridge_point(end,0),bridge_point(end,width),bridge_point(start,width)], tone)
		segment(bridge_point(start,0), bridge_point(start,width), grain)
		if travel > 0.56:
			segment(bridge_point(start+1,1), bridge_point(start+1,width-2), timber.lightened(0.08))
		for mark in [3.0, width-4]:
			var nail := bridge_point(start+3,mark)
			rect(nail.x,nail.y,1,1,iron)
	segment(d,c,shadow,4)
	segment(b,c,lip,2)
	segment(a,b,lip,2)
	segment(d,c,lip,1)
	if travel < 0.85:
		segment(bridge_point(1,3),bridge_point(bridge_length-3,width-4),iron,2)
	rect(411,hinge.y-2,8,4,iron)
	rect(411,bridge_front-2,8,4,iron)
	rect(412,hinge.y-2,6,1,lip)
	rect(412,bridge_front-2,6,1,lip)


func draw_hanging_line(start: Vector2, finish: Vector2, sag: float, color: Color) -> void:
	var nodes := PackedVector2Array()
	for i in range(25):
		var t := float(i)/24.0
		var p := start.lerp(finish,t)
		p.y += sin(PI*t)*sag
		nodes.append(p.round())
	canvas.draw_polyline(nodes,color,1.0,false)


func draw_winch() -> void:
	var x := winch.x
	var y := winch.y
	var cast_iron := lit(Color("#425a51"), Color("#405758"))
	var steel := lit(Color("#86937b"), Color("#769189"))
	var rope := lit(Color("#ae9972"), Color("#8b937b"))
	var orange := lit(Color("#df7846"), Color("#ef9661"))
	var bright := lit(Color("#ffd09a"), Color("#ffd3a3"))
	var foot := Vector2(x,y)
	ellipse(foot+Vector2(0,-1),18,4,lit(Color("#77765b"),Color("#506c67")))
	shape([foot+Vector2(-17,-1),foot+Vector2(-12,-5),foot+Vector2(13,-5),foot+Vector2(16,0),foot+Vector2(11,2),foot+Vector2(-15,2)],cast_iron)
	rect(x-14,y-1,26,2,steel)
	rect(x-10,y-16,17,12,cast_iron)
	rect(x-7,y-15,13,9,rope)
	for j in range(5):
		segment(Vector2(x-6+j*2,y-14),Vector2(x-5+j*2,y-7),lit(Color("#746f56"),Color("#5b7069")))
	ellipse(foot+Vector2(-9,-11),4,7,cast_iron)
	ellipse(foot+Vector2(-9,-11),2,5,steel)
	segment(foot+Vector2(-13,-1),foot+Vector2(-9,-11),cast_iron,4)
	segment(foot+Vector2(6,0),foot+Vector2(8,-12),cast_iron,4)
	var axle := foot+Vector2(8,-13)
	canvas.draw_circle(axle,7,cast_iron)
	canvas.draw_arc(axle,6,0,TAU,26,steel,1.0,false)
	var rotation := -2.2 + travel*TAU*1.6
	for j in range(4):
		var spoke := Vector2.from_angle(rotation+0.5*PI*j)*5
		segment(axle,axle+spoke,steel)
	var end := axle + Vector2.from_angle(rotation)*14
	segment(axle,end,INK,4)
	segment(axle,end,orange,2)
	shape([end+Vector2(-4,-1),end+Vector2(-2,-3),end+Vector2(4,-3),end+Vector2(5,0),end+Vector2(2,2),end+Vector2(-4,2)],orange)
	rect(end.x-2,end.y-3,5,1,bright)
	rect(axle.x-1,axle.y-1,3,2,bright)


func draw_worker() -> void:
	var x := roundf(feet.x)
	var y := roundf(feet.y)
	var bob := -1.0 if walking and sin(stride*2)>0.2 else 0.0
	var sw := roundf(sin(stride)*2) if walking else 0.0
	var shadow := lit(Color("#77745a"),Color("#526963"))
	ellipse(Vector2(x,y),6,2,shadow)
	var outline := lit(Color("#304b49"),Color("#293f43"))
	var jacket := lit(Color("#497a76"),Color("#5d837e"))
	var coat_light := lit(Color("#88a596"),Color("#92ada1"))
	var skin := lit(Color("#c39a73"),Color("#b1977b"))
	var cap := lit(Color("#e0c998"),Color("#d1c39f"))
	canvas.draw_set_transform(Vector2(x,y+bob),0,Vector2(facing,1))
	rect(-4,-8,3,6+sw,outline)
	rect(1,-8,3,6-sw,outline)
	rect(-4,-3+sw,4,2,lit(Color("#655d4a"),Color("#59665e")))
	rect(1,-3-sw,4,2,lit(Color("#655d4a"),Color("#59665e")))
	shape([Vector2(-4,-18),Vector2(1,-20),Vector2(4,-17),Vector2(5,-10),Vector2(3,-8),Vector2(-4,-8),Vector2(-6,-11)],outline)
	shape([Vector2(-3,-18),Vector2(1,-19),Vector2(3,-17),Vector2(3,-9),Vector2(-4,-10)],jacket)
	rect(-4,-16,2,5,coat_light)
	rect(2,-17,2,6,jacket.lightened(.1))
	rect(3,-13,2,3,skin)
	rect(-3,-10,6,1,lit(Color("#9f926f"), Color("#869582")))
	rect(-1,-20,5,3,lit(Color("#c5ac7d"),Color("#baa98c")))
	shape([Vector2(-3,-25),Vector2(3,-25),Vector2(4,-23),Vector2(5,-22),Vector2(4,-21),
		Vector2(4,-20),Vector2(2,-19),Vector2(-2,-20),Vector2(-4,-22)], skin)
	rect(-3,-23,2,4,outline)
	rect(2,-23,1,1,outline)
	rect(-4,-27,6,2,outline)
	rect(-5,-25,10,2,outline)
	rect(-4,-27,6,2,cap)
	rect(-5,-25,10,1,cap.lightened(.04))
	rect(-4,-24,7,1,lit(Color("#977f5c"),Color("#9c967c")))
	canvas.draw_set_transform(Vector2.ZERO,0,Vector2.ONE)


func draw_hint() -> void:
	var label := "收桥" if lowered else "放桥"
	var box := Rect2(258,153,48,18)
	canvas.draw_rect(box,lit(Color("#354b48"),Color("#283e42")))
	rect(box.position.x+2,box.position.y+3,12,12,lit(Color("#ddc99b"),Color("#c7bea0")))
	canvas.draw_string(ThemeDB.fallback_font,Vector2(262,166),"E",HORIZONTAL_ALIGNMENT_LEFT,-1,10,INK)
	canvas.draw_string(hint_font,Vector2(275,166),label,HORIZONTAL_ALIGNMENT_LEFT,-1,11,Color("#f2e3ba"))
	shape([Vector2(279,171),Vector2(285,171),Vector2(282,174)],lit(Color("#354b48"),Color("#283e42")))
