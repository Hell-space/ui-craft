extends SceneTree
## Standalone, deterministic replay of physical keyboard events. Optional argument is a capture directory.
## godot --headless --path . --script res://verify.gd
## godot --path . --script res://verify.gd -- C:/proof

var yard
var output := ""
var framing_only := false
var checks: Array[Dictionary] = []
var screenshots: Dictionary = {}
var masks: Dictionary = {}
var success := true


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	for argument in args:
		if argument == "--framing-only":
			framing_only = true
		else:
			output = argument
	if not output.is_empty():
		DirAccess.make_dir_recursive_absolute(output)
	call_deferred("run")


func key(code: Key, down: bool, echo := false) -> void:
	var event := InputEventKey.new()
	event.keycode = code
	event.physical_keycode = code
	event.pressed = down
	event.echo = echo
	Input.parse_input_event(event)
	Input.flush_buffered_events()


func frames(count: int) -> void:
	for i in range(count):
		await physics_frame


func tap(code: Key) -> void:
	key(code,true)
	await frames(1)
	key(code,false)
	await frames(1)


func walk(code: Key, count: int) -> void:
	key(code,true)
	await frames(count)
	key(code,false)
	await frames(1)


func confirm(label: String, passed: bool, extra: Variant = "") -> void:
	checks.append({"check":label,"passed":passed,"observed":extra})
	if not passed:
		success = false
		push_error("REPLAY FAILED — " + label + " " + str(extra))


func footprint_hash() -> String:
	var mask := PackedByteArray()
	for y in range(199, 256):
		for x in range(640):
			mask.append(1 if yard.can_stand(Vector2(x,y)) else 0)
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(mask)
	return context.finish().hex_encode()


func capture(stem: String) -> void:
	if output.is_empty() or DisplayServer.get_name() == "headless":
		return
	yard.canvas.queue_redraw()
	await process_frame
	await RenderingServer.frame_post_draw
	var frame := root.get_texture().get_image()
	var destination := output.path_join(stem + ".png")
	var status := frame.save_png(destination)
	confirm(stem+" capture", status == OK and not frame.is_empty(), str(frame.get_size()))
	screenshots[stem] = [frame.get_width(),frame.get_height()]
	var pixels: Image = yard.canvas.get_viewport().get_texture().get_image()
	status = pixels.save_png(output.path_join(stem+"_native.png"))
	confirm(stem+" native art frame",status==OK and pixels.get_size()==Vector2i(640,360),str(pixels.get_size()))


func effect_variants(key_name: String, baseline: String) -> void:
	# All four combinations are reached by keyboard. Enumerate every integer foot position each time.
	for code in [KEY_F2, KEY_F3, KEY_F2, KEY_F3]:
		await tap(code)
		var tested := footprint_hash()
		var label := "%s gear=%s evening=%s" % [key_name,yard.gear_visible,yard.evening]
		masks[label] = tested
		confirm(label+" collision matches",tested==baseline)


func run() -> void:
	yard = load(ProjectSettings.get_setting("application/run/main_scene")).instantiate()
	root.add_child(yard)
	current_scene = yard
	await frames(3)
	confirm("actual main scene loaded",yard.name=="Tideyard" and yard.backdrops.size()==2 and yard.equipment.size()==2)
	confirm("initial bank and bridge",not yard.lowered and not yard.bridge_walkable() and not yard.in_reach(),str(yard.feet))
	await capture("wide_day")
	await tap(KEY_F3)
	confirm("F3 selects evening",yard.evening)
	await capture("wide_evening")
	await tap(KEY_F3)
	confirm("F3 returns to daylight",not yard.evening)
	if framing_only:
		await finish()
		return
	confirm("initial spawn stands on left quay",yard.can_stand(yard.feet))
	confirm("mid-channel is water",not yard.can_stand(Vector2(366,231)))
	var raised := footprint_hash()
	masks["raised reference"] = raised
	await effect_variants("raised",raised)
	await walk(KEY_D,125)
	confirm("closed bridge stops rightward walking",yard.feet.x>314 and yard.feet.x<334,str(yard.feet))
	confirm("winch is out of reach at the splinters",not yard.in_reach())
	await tap(KEY_E)
	confirm("remote activation ignored",not yard.lowered)
	await walk(KEY_A,33)
	confirm("worker can reach orange handle",yard.in_reach(),str(yard.feet))
	await capture("near_handle")
	key(KEY_E,true)
	await frames(5)
	confirm("lowering animation began",yard.lowered and yard.travel>0 and yard.travel<1,yard.travel)
	key(KEY_E,true,true)
	await frames(2)
	key(KEY_E,false)
	await frames(1)
	await tap(KEY_E)
	confirm("repeat press cannot reverse mid-lift",yard.lowered and not yard.bridge_walkable(),yard.travel)
	await frames(54)
	confirm("fully lowered deck takes weight",yard.bridge_walkable() and yard.can_stand(Vector2(366,231)),yard.travel)
	var down := footprint_hash()
	masks["lowered reference"] = down
	confirm("bridge changes the walkable mask",raised != down)
	await effect_variants("lowered",down)
	await walk(KEY_RIGHT,65)
	confirm("walked onto bridge using arrow",yard.feet.x>350 and yard.feet.x<389,str(yard.feet))
	await walk(KEY_W,43)
	confirm("rear deck edge stops worker over open water",yard.feet.y>=221 and yard.feet.y<224,str(yard.feet))
	await walk(KEY_S,8)
	confirm("back on middle boards",yard.feet.y>229 and yard.feet.y<237,str(yard.feet))
	await capture("bridge_down")
	await tap(KEY_F2)
	await tap(KEY_F3)
	await walk(KEY_D,92)
	confirm("crossed to right bank with gear off at dusk",yard.feet.x>470 and yard.evening and not yard.gear_visible,str(yard.feet))
	await tap(KEY_E)
	confirm("leaving range hides affordance and follows reach rule",not yard.in_reach() and yard.bridge_walkable(),str(yard.feet))
	await walk(KEY_LEFT,157)
	confirm("reentered winch range from opposite bank",yard.in_reach(),str(yard.feet))
	await tap(KEY_SPACE)
	confirm("Space raises bridge",not yard.lowered and not yard.bridge_walkable())
	await frames(54)
	confirm("raised route restored in dusk",yard.travel==0.0 and footprint_hash()==raised)
	await walk(KEY_D,105)
	confirm("returned raised bridge blocks a second crossing",yard.feet.x<334 and yard.feet.x>314,str(yard.feet))
	await finish()


func finish() -> void:
	var native_size := DisplayServer.window_get_size()
	var logical_size := root.get_visible_rect().size
	var stretch := root.get_final_transform()
	var status := {"success":success, "engine":Engine.get_version_info().string,
		"display_driver":DisplayServer.get_name(), "native_window":[native_size.x,native_size.y],
		"logical_view":[logical_size.x,logical_size.y],"canvas_transform":str(stretch),
		"observations":checks,"walk_mask_sha256":masks,"renderer_frames":screenshots}
	var report := JSON.stringify(status,"\t")
	if not output.is_empty():
		var file := FileAccess.open(output.path_join("replay.json"),FileAccess.WRITE)
		if file:
			file.store_string(report+"\n")
	print("TIDEYARD_REPLAY ",JSON.stringify(status))
	quit(0 if success else 1)
