extends SceneTree
var host
var failures: Array[String]=[]
func expect(ok: bool, label: String) -> void:
	if not ok:failures.append(label)
func pad(code: JoyButton) -> void:
	for active in [true,false]:
		var e:=InputEventJoypadButton.new()
		e.device=0;e.button_index=code;e.pressed=active
		Input.parse_input_event(e)
		await process_frame
		await process_frame
func press(button: Button) -> void:
	for active in [true,false]:
		var e:=InputEventMouseButton.new()
		e.button_index=MOUSE_BUTTON_LEFT;e.position=button.get_global_rect().get_center();e.global_position=e.position;e.pressed=active
		root.push_input(e,true)
		await process_frame
func proof(name: String) -> void:
	var folder:=OS.get_environment("UI_CRAFT_PROOF_DIR")
	if folder.is_empty() or DisplayServer.get_name()=="headless":return
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(folder.path_join(name+".png"))
func _initialize() -> void:run.call_deferred()
func run() -> void:
	host=load("res://workshop.tscn").instantiate()
	root.add_child(host)
	await process_frame
	await process_frame
	expect(host.equipped==0 and host.selected==1 and "−3" in host.compare.values.text,"initial reference and delta")
	await proof("pixel-initial")
	await pad(JOY_BUTTON_DPAD_RIGHT)
	expect(host.selected==2 and host.equipped==0 and "+2" in host.compare.values.text,"preview uses fixed equipped item")
	await pad(JOY_BUTTON_B)
	expect(not host.compare.visible and root.gui_get_focus_owner()==host.slots[2],"cancel retains slot focus")
	await pad(JOY_BUTTON_DPAD_LEFT)
	await pad(JOY_BUTTON_A)
	expect(host.equipped==1 and "力度 0" in host.compare.values.text,"commit once")
	await press(host.pack_button)
	expect(host.pack==1 and host.compare.heading.get_theme_color("font_color")==host.paint("type"),"add-on follows host skin")
	await press(host.zoom_button)
	expect(host.gui_zoom==1.25 and is_equal_approx(host.compare.scale.x,host.inventory.scale.x),"add-on follows host GUI scale")
	var clip: Rect2=root.get_visible_rect()
	expect(clip.encloses(host.compare.get_global_rect()) and clip.encloses(host.inventory.get_global_rect()),"comparison and slots stay in viewport")
	await proof("pixel-violet")
	if failures.is_empty():print("PASS pixel add-on: preview, equipped baseline, cancel/focus, confirm, runtime skin, GUI scale, bounds")
	else:
		for e in failures:push_error(e)
	quit(0 if failures.is_empty() else 1)

