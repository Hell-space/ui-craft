extends SceneTree

# Run with godot --headless --path <sample folder> --script res://verify.gd
var station
var failures: Array[String] = []
var checks := 0

func _initialize() -> void:
	check_navigation.call_deferred()

func expect(condition: bool, label: String) -> void:
	checks += 1
	if not condition:
		failures.append(label)

func press_pad(button: JoyButton) -> void:
	for down in [true,false]:
		var event := InputEventJoypadButton.new()
		event.device = 0
		event.button_index = button
		event.pressed = down
		Input.parse_input_event(event)
		await process_frame
		await process_frame

func send_key(code: Key, down: bool, echo := false) -> void:
	var event := InputEventKey.new()
	event.keycode = code
	event.pressed = down
	event.echo = echo
	Input.parse_input_event(event)
	await process_frame
	await process_frame

func click_at(point: Vector2) -> void:
	for down in [true,false]:
		var event := InputEventMouseButton.new()
		event.button_index = MOUSE_BUTTON_LEFT
		event.position = point
		event.global_position = point
		event.pressed = down
		root.push_input(event, true)
		await process_frame
		await process_frame

func check_range() -> void:
	var chart = station.chart
	var scale_now: float = station._range_scale()
	var radius := 140 * scale_now
	for test in [[radius-2,0.0,true],[radius+2,0.0,false],[radius*.8,42.0,true],[radius*.8,44.0,false]]:
		var target: Vector2 = chart.STATIONS[1]
		var offset := Vector2.RIGHT.rotated(deg_to_rad(test[1])) * float(test[0])
		var origin: Vector2 = target-offset/chart.size
		chart.move_to(origin-Vector2(8,0)/chart.size)
		chart.move_to(origin)
		chart.surveyed.clear()
		station.energy = 100
		station.cooldown = 0
		await press_pad(JOY_BUTTON_Y)
		expect(is_equal_approx(chart.preview_radius,radius) and is_equal_approx(chart.preview_arc,deg_to_rad(86)), "world preview uses candidate radius and angle")
		expect(chart.covered_ids(chart.preview_radius,chart.preview_arc).has("B2") == bool(test[2]),"candidate lists B2 on the same side as the survey rule")
		expect(not station.menu_panel.get_global_rect().has_point(chart.cursor*chart.size),"preview leaves the boat visible")
		await press_pad(JOY_BUTTON_B)
		var measured_at: Vector2 = chart.cursor
		await press_pad(JOY_BUTTON_A)
		expect(chart.surveyed.has(1) == bool(test[2]),"world hit at distance %s and angle %s" % [test[0],test[1]])
		expect(is_equal_approx(chart.scan_radius,radius) and chart.scan_heading.is_equal_approx(Vector2.RIGHT),"real pulse uses the preview scale and boat heading")
		expect(chart.last_sounding == chart.water_depth(measured_at) and chart.scan_origin.is_equal_approx(measured_at),"depth anchored at the sampled point")
		var anchor: Vector2 = chart.scan_origin
		chart.move_to(origin+Vector2(30,10)/chart.size)
		expect(chart.scan_origin == anchor,"moving the boat preserves the last sounding position")

func check_navigation() -> void:
	station = load("res://station.tscn").instantiate()
	root.add_child(station)
	await process_frame
	if not station.has_method("_scan"):
		quit(1)
		return
	station.grab_focus()
	var initial_heading: Vector2 = station.chart.heading
	await press_pad(JOY_BUTTON_Y)
	expect(station.overlay.visible,"open with Y")
	await press_pad(JOY_BUTTON_DPAD_DOWN)
	expect(root.gui_get_focus_owner()==station.probe_buttons[1] and station.equipped==0,"preview preserves equipped probe")
	expect(station.selected_values[1].text == "86" and station.equipped_values[1].text == "360","compared values use distinct records")
	expect(station.charge_label.text == "储能 100%  ·  预览可测 6 次","100 energy at cost 15")
	expect(station.charge_label.text.contains("可测 6 次") and station.energy == 100,"projected casts preserve energy")
	expect(not station.menu_panel.get_global_rect().has_point(station.chart.cursor*station.chart.size),"clear preview origin")
	await press_pad(JOY_BUTTON_B)
	expect(not station.overlay.visible and station.equipped==0 and root.gui_get_focus_owner()==station,"cancel and restore focus")
	expect(station.chart.preview_radius == 0 and station.charge_label.text.contains("可测 4 次"),"cancel restores the active range and capacity")
	await press_pad(JOY_BUTTON_Y)
	await press_pad(JOY_BUTTON_DPAD_DOWN)
	var scans: int = station.scans
	await press_pad(JOY_BUTTON_A)
	expect(station.equipped==1 and not station.overlay.visible and station.scans==scans,"confirm once without world input")
	await press_pad(JOY_BUTTON_A)
	expect(station.scans==scans+1,"next press reaches the world")
	await check_range()
	expect(not station.chart.scan_heading.is_equal_approx(initial_heading),"reoriented pulse uses the new bow heading")
	await send_key(KEY_E,true)
	await send_key(KEY_E,true,true)
	await send_key(KEY_E,false)
	expect(station.overlay.visible and not station.pad,"held keyboard open and input prompts")
	station.motion_button.grab_focus()
	expect(station.menu_hint.text.contains("切换"),"focus hint follows the setting")
	station.back_button.grab_focus()
	expect(station.menu_hint.text.contains("返回"),"focus hint follows return")
	await send_key(KEY_ESCAPE,true)
	await send_key(KEY_ESCAPE,false)
	var current_probe: int = station.equipped
	station.energy = 1
	station.cooldown = 0
	scans = station.scans
	await send_key(KEY_SPACE,true)
	await send_key(KEY_SPACE,false)
	expect(station.scans == scans and station.response.text.contains("储能不足"),"unaffordable scan leaves survey untouched")
	await click_at(station.gear_button.get_global_rect().get_center())
	expect(station.overlay.visible,"pointer opens the cabinet")
	await click_at(station.probe_buttons[2].get_global_rect().get_center())
	expect(not station.overlay.visible and station.equipped == 2 and current_probe == 1,"pointer commits the focused candidate")
	station.energy = 100
	station.cooldown = 0
	station._reduce(true)
	await press_pad(JOY_BUTTON_A)
	expect(station.chart.scan_phase < 0 and station.chart.last_sounding >= 0,"reduced motion keeps a static sounding")
	var remaining: float = station.cooldown
	scans = station.scans
	await press_pad(JOY_BUTTON_A)
	expect(station.scans == scans and station.cooldown < remaining,"cooldown decreases and rejects another immediate cast")
	if failures.is_empty():
		print("PASS: ",checks," checks across survey, preview, focus, inputs, range edges and reduced motion")
		quit(0)
	else:
		for failure in failures: push_error(failure)
		quit(1)
