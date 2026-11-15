extends Control

const Survey = preload("res://survey.gd")
const INK := Color("#152238")
const SURFACE := Color("#2a3d57")
const TEXT := Color("#f8f1e2")
const MUTED := Color("#b5c7db")
const LINE := Color("#526782")
const SIGNAL := Color("#ffac70")
const PAPER := Color("#f7f2e6")
const PAPER_INK := Color("#23334c")
const PAPER_SUB := Color("#475770")
const RED_INK := Color("#a33f28")
const PROBES := [
	{"name":"广域探头", "radius":210.0, "arc":360.0, "cost":24, "interval":1.05, "use":"环形覆盖相邻测站，适合沿岸普查。"},
	{"name":"定向探头", "radius":140.0, "arc":86.0, "cost":15, "interval":.72, "use":"沿船头方向，测量前方航段。"},
	{"name":"精测探头", "radius":84.0, "arc":360.0, "cost":8, "interval":.44, "use":"近距离反复取样，回波间隔最短。"},
]

var chart := Survey.new()
var font_ui := SystemFont.new()
var font_figure := SystemFont.new()
var overlay := ColorRect.new()
var menu_panel := PanelContainer.new()
var menu_position := MarginContainer.new()
var dock := HBoxContainer.new()
var dock_space := Control.new()
var probe_buttons: Array[Button] = []
var controls: Array[Control] = []
var return_focus: Control
var scan_button: Button
var gear_button: Button
var chart_button: Button
var back_button: Button
var motion_button: CheckButton
var stock: ProgressBar
var charge_label: Label
var count_label: Label
var probe_label: Label
var response: Label
var details: Label
var coverage_note: Label
var coverage_legend: Label
var preview_name: Label
var equipped_name: Label
var selected_name: Label
var equipped_values: Array[Label] = []
var selected_values: Array[Label] = []
var previewed := 0
var menu_body := BoxContainer.new()
var device_hint: Label
var menu_hint: Label

var equipped := 0
var energy := 100.0
var cooldown := 0.0
var reduce_motion := false
var pad := false
var using_pointer := false
var last_pad := -1
var scans := 0
var last_depth := -1
var note := ""
var note_remaining := 0.0
var held_actions: Dictionary = {}
var stick_direction := 0
var repeat_in := 0.0
var wait_for_neutral := false
var chart_contact := false

func _ready() -> void:
	_set_inputs()
	font_ui.font_names = PackedStringArray(["Noto Sans SC","Microsoft YaHei UI","PingFang SC","sans-serif"])
	font_figure.font_names = PackedStringArray(["Barlow","Bahnschrift","Segoe UI","Noto Sans SC","Microsoft YaHei UI"])
	theme = Theme.new()
	theme.default_font = font_ui
	theme.default_font_size = 16
	chart.graphic_font = font_figure
	add_child(chart)
	chart.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_build_hud()
	_build_menu()
	_refresh()
	resized.connect(_fit_menu)
	Input.joy_connection_changed.connect(_joy_connection)
	_fit_menu()
	grab_focus()

func _set_inputs() -> void:
	# Desktop projects may ship keyboard-only ui_accept/ui_cancel defaults.
	_pad_binding("ui_accept",JOY_BUTTON_A)
	_pad_binding("ui_cancel",JOY_BUTTON_B)
	_pad_binding("ui_up",JOY_BUTTON_DPAD_UP)
	_pad_binding("ui_down",JOY_BUTTON_DPAD_DOWN)
	_action("survey_scan", KEY_SPACE, JOY_BUTTON_A)
	_action("survey_gear", KEY_E, JOY_BUTTON_Y)
	_action("survey_chart", KEY_M, JOY_BUTTON_X)
	_action("survey_left", KEY_LEFT, JOY_BUTTON_DPAD_LEFT, JOY_AXIS_LEFT_X, -1)
	_action("survey_right", KEY_RIGHT, JOY_BUTTON_DPAD_RIGHT, JOY_AXIS_LEFT_X, 1)
	_action("survey_up", KEY_UP, JOY_BUTTON_DPAD_UP, JOY_AXIS_LEFT_Y, -1)
	_action("survey_down", KEY_DOWN, JOY_BUTTON_DPAD_DOWN, JOY_AXIS_LEFT_Y, 1)

func _action(action: StringName, key: Key, button: JoyButton, axis := -1, direction := 0) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action, .25)
	var k := InputEventKey.new()
	k.keycode = key
	InputMap.action_add_event(action,k)
	_pad_binding(action,button)
	if axis >= 0:
		var motion := InputEventJoypadMotion.new()
		motion.axis = axis as JoyAxis
		motion.axis_value = direction
		InputMap.action_add_event(action,motion)

func _pad_binding(action: StringName, button: JoyButton) -> void:
	var b := InputEventJoypadButton.new()
	b.button_index = button
	if not InputMap.action_has_event(action,b):
		InputMap.action_add_event(action,b)

func _box(color: Color, border: Color, edge := 1, corner := 6, px := 14, py := 9) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = color
	box.border_color = border
	box.set_border_width_all(edge)
	box.set_corner_radius_all(corner)
	box.content_margin_left = px
	box.content_margin_right = px
	box.content_margin_top = py
	box.content_margin_bottom = py
	return box

func _label(parent: Control, value: String, px: int, color := TEXT) -> Label:
	var label := Label.new()
	label.text = value
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_size_override("font_size",px)
	label.add_theme_color_override("font_color",color)
	parent.add_child(label)
	return label

func _button(parent: Control, title: String, callback: Callable) -> Button:
	var button := Button.new()
	button.text = title
	button.custom_minimum_size.y = 44
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.add_theme_stylebox_override("normal",_box(INK,LINE))
	button.add_theme_stylebox_override("hover",_box(SURFACE,MUTED))
	button.add_theme_stylebox_override("pressed",_box(SURFACE,SIGNAL,2))
	var focus := _box(Color.TRANSPARENT,SIGNAL,2)
	focus.draw_center = false
	button.add_theme_stylebox_override("focus",focus)
	for key in ["font_color","font_hover_color","font_pressed_color","font_focus_color"]:
		button.add_theme_color_override(key,TEXT)
	button.pressed.connect(callback)
	parent.add_child(button)
	return button

func _column(panel: PanelContainer) -> VBoxContainer:
	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation",2)
	panel.add_child(column)
	return column

func _plate(parent: Control, minimum_width: int) -> PanelContainer:
	var plate := PanelContainer.new()
	plate.custom_minimum_size.x = minimum_width
	plate.mouse_filter = Control.MOUSE_FILTER_IGNORE
	plate.add_theme_stylebox_override("panel",_box(INK,LINE,0,0,14,9))
	parent.add_child(plate)
	return plate

func _spacer(parent: Control, horizontal: bool) -> void:
	var spacer := Control.new()
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if horizontal: spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	else: spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	parent.add_child(spacer)

func _build_hud() -> void:
	var safe := MarginContainer.new()
	add_child(safe)
	safe.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	safe.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["margin_left","margin_right"]: safe.add_theme_constant_override(side,30)
	for side in ["margin_top","margin_bottom"]: safe.add_theme_constant_override(side,23)
	var body := VBoxContainer.new()
	body.mouse_filter = Control.MOUSE_FILTER_IGNORE
	safe.add_child(body)
	var top := HBoxContainer.new()
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	body.add_child(top)
	var location := _column(_plate(top,160))
	_label(location,"东岬水道",25)
	count_label = _label(location,"",15,MUTED)
	_spacer(top,true)
	var charge := _column(_plate(top,126))
	charge_label = _label(charge,"",16)
	stock = ProgressBar.new()
	stock.show_percentage = false
	stock.custom_minimum_size = Vector2(112,5)
	stock.mouse_filter = Control.MOUSE_FILTER_IGNORE
	stock.add_theme_stylebox_override("background",_box(LINE,Color.TRANSPARENT,0,0,0,0))
	stock.add_theme_stylebox_override("fill",_box(MUTED,MUTED,0,0,0,0))
	charge.add_child(stock)
	_spacer(body,false)
	var bottom := HBoxContainer.new()
	bottom.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bottom.alignment = BoxContainer.ALIGNMENT_END
	bottom.add_theme_constant_override("separation",8)
	body.add_child(bottom)
	var readout := _column(_plate(bottom,215))
	probe_label = _label(readout,"",15,MUTED)
	response = _label(readout,"",22,TEXT)
	device_hint = _label(readout,"",14,MUTED)
	_spacer(bottom,true)
	scan_button = _button(bottom,"",_scan)
	scan_button.custom_minimum_size.x = 116
	gear_button = _button(bottom,"",_open_menu)
	chart_button = _button(bottom,"",_toggle_chart)
	for button in [scan_button,gear_button,chart_button]:
		button.size_flags_vertical = Control.SIZE_SHRINK_END
		button.focus_mode = Control.FOCUS_CLICK

func _build_menu() -> void:
	add_child(overlay)
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.color = Color(.035,.065,.115,.23)
	overlay.mouse_filter = Control.MOUSE_FILTER_STOP
	overlay.hide()
	overlay.add_child(menu_position)
	menu_position.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu_position.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["margin_left","margin_right","margin_top","margin_bottom"]:
		menu_position.add_theme_constant_override(side,22)
	menu_position.add_child(dock)
	dock.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dock.add_child(dock_space)
	dock_space.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dock_space.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dock.add_child(menu_panel)
	menu_panel.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	menu_panel.add_theme_stylebox_override("panel",_box(PAPER,INK,1,0,20,16))
	var column := _column(menu_panel)
	column.add_theme_constant_override("separation",14)
	var header := HBoxContainer.new()
	column.add_child(header)
	_label(header,"探头仓",32,PAPER_INK)
	_spacer(header,true)
	menu_hint = _label(header,"",15,PAPER_SUB)
	column.add_child(menu_body)
	menu_body.add_theme_constant_override("separation",17)
	var choices := VBoxContainer.new()
	choices.custom_minimum_size.x = 138
	choices.add_theme_constant_override("separation",6)
	menu_body.add_child(choices)
	_label(choices,"选择探头",15,PAPER_SUB)
	for i in PROBES.size():
		var button := _button(choices,"",_equip.bind(i))
		button.custom_minimum_size.y = 52
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.add_theme_font_size_override("font_size",17)
		var neutral := _box(PAPER,Color("#c8c4b9"),0,0,11,7)
		neutral.border_width_bottom = 1
		button.add_theme_stylebox_override("normal",neutral)
		button.add_theme_stylebox_override("hover",_box(Color("#efe2cd"),PAPER_SUB,1,0,11,7))
		button.add_theme_stylebox_override("pressed",_box(Color("#ebd6bd"),RED_INK,1,0,11,7))
		var focus := _box(Color.TRANSPARENT,RED_INK,2,0,11,7)
		focus.draw_center = false
		button.add_theme_stylebox_override("focus",focus)
		for key in ["font_color","font_hover_color","font_pressed_color","font_focus_color"]:
			button.add_theme_color_override(key,PAPER_INK)
		button.focus_entered.connect(_preview.bind(i))
		button.mouse_entered.connect(_hover_probe.bind(i))
		probe_buttons.append(button)
		controls.append(button)
	var info := VBoxContainer.new()
	info.custom_minimum_size.x = 207
	menu_body.add_child(info)
	preview_name = _label(info,"",24,PAPER_INK)
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation",12)
	grid.add_theme_constant_override("v_separation",8)
	info.add_child(grid)
	_label(grid,"参数",14,PAPER_SUB)
	equipped_name = _label(grid,"已装备",14,PAPER_SUB)
	equipped_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	selected_name = _label(grid,"预览",14,RED_INK)
	selected_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	for field in ["半径 m","开角 °","耗能 %","间隔 s"]:
		_label(grid,field,15,PAPER_SUB)
		var fitted := _label(grid,"",18,PAPER_INK)
		fitted.add_theme_font_override("font",font_figure)
		fitted.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		equipped_values.append(fitted)
		var selected := _label(grid,"",18,RED_INK)
		selected.add_theme_font_override("font",font_figure)
		selected.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		selected_values.append(selected)
	var separation := Control.new()
	separation.custom_minimum_size.y = 8
	info.add_child(separation)
	details = _label(info,"",16,PAPER_SUB)
	details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	coverage_note = _label(info,"",15,RED_INK)
	coverage_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	coverage_legend = _label(column,"海图实线 · 预览　　虚线 · 已装备",15,PAPER_SUB)
	var footer := HBoxContainer.new()
	column.add_child(footer)
	motion_button = CheckButton.new()
	motion_button.text = "减少动态效果"
	motion_button.custom_minimum_size.y = 40
	for key in ["font_color","font_hover_color","font_pressed_color","font_focus_color"]:
		motion_button.add_theme_color_override(key,PAPER_INK)
	motion_button.add_theme_stylebox_override("focus",probe_buttons[0].get_theme_stylebox("focus"))
	motion_button.toggled.connect(_reduce)
	footer.add_child(motion_button)
	controls.append(motion_button)
	_spacer(footer,true)
	back_button = _button(footer,"",_close_menu)
	controls.append(back_button)
	for i in controls.size():
		var button := controls[i]
		button.focus_entered.connect(_update_menu_hint)
		var previous := button.get_path_to(controls[posmod(i-1,controls.size())])
		var next := button.get_path_to(controls[(i+1)%controls.size()])
		button.focus_neighbor_top = previous
		button.focus_previous = previous
		button.focus_neighbor_bottom = next
		button.focus_next = next
		button.focus_neighbor_left = NodePath(".")
		button.focus_neighbor_right = NodePath(".")

func _fit_menu() -> void:
	menu_body.vertical = size.x < 760
	menu_panel.custom_minimum_size.x = minf(410, size.x-44)
	var compact := get_viewport().get_visible_rect().size.y * get_viewport().get_stretch_transform().get_scale().y < 580
	coverage_note.add_theme_font_size_override("font_size",18 if compact else 15)
	coverage_legend.add_theme_font_size_override("font_size",18 if compact else 15)
	details.add_theme_font_size_override("font_size",18 if compact else 16)
	equipped_name.add_theme_font_size_override("font_size",17 if compact else 14)
	selected_name.add_theme_font_size_override("font_size",17 if compact else 14)
	# A moving focus does not move the panel. Choose the free side when opening or resizing.
	dock.move_child(dock_space,0 if chart.cursor.x < .5 else 1)
	if overlay.visible:
		chart.set_probe_preview(PROBES[previewed],PROBES[equipped],_range_scale())
		_update_coverage_note()
	_position_menu.call_deferred()

func _position_menu() -> void:
	if not overlay.visible: return
	var origin := chart.cursor * size
	var furthest := maxf(chart.preview_radius,chart.fitted_radius)
	var left_space := origin.x - furthest
	var right_space := size.x - origin.x - furthest
	var top_space := origin.y - furthest
	var bottom_space := size.y - origin.y - furthest
	var side_fits := maxf(left_space,right_space) >= menu_panel.size.x + 24
	dock.move_child(dock_space,0 if right_space > left_space else 1)
	menu_panel.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	if not side_fits and maxf(top_space,bottom_space) >= menu_panel.size.y + 24:
		menu_panel.size_flags_vertical = Control.SIZE_SHRINK_BEGIN if top_space > bottom_space else Control.SIZE_SHRINK_END

func _hover_probe(i: int) -> void:
	if using_pointer and overlay.visible:
		probe_buttons[i].grab_focus()

func _preview(i: int) -> void:
	previewed = i
	var probe: Dictionary = PROBES[i]
	var fitted: Dictionary = PROBES[equipped]
	preview_name.text = probe.name
	equipped_name.text = "已装·" + str(fitted.name).trim_suffix("探头")
	selected_name.text = "预览·" + str(probe.name).trim_suffix("探头")
	details.text = probe.use
	var before := _figures(fitted)
	var after := _figures(probe)
	for j in before.size():
		equipped_values[j].text = before[j]
		selected_values[j].text = after[j]
	chart.set_probe_preview(probe,fitted,_range_scale())
	_update_coverage_note()
	_refresh()

func _update_coverage_note() -> void:
	var reference: PackedStringArray = chart.covered_ids(chart.fitted_radius,chart.fitted_arc)
	var candidate: PackedStringArray = chart.covered_ids(chart.preview_radius,chart.preview_arc)
	if reference == candidate:
		coverage_note.text = "两者可测  " + ("、".join(candidate) if not candidate.is_empty() else "无站位")
	else:
		coverage_note.text = "已装可测  %s\n预览可测  %s" % ["、".join(reference) if not reference.is_empty() else "无站位", "、".join(candidate) if not candidate.is_empty() else "无站位"]

func _figures(probe: Dictionary) -> PackedStringArray:
	return PackedStringArray([str(int(probe.radius)),str(int(probe.arc)),str(probe.cost),"%.2f" % probe.interval])

func _update_menu_hint() -> void:
	var focus := get_viewport().gui_get_focus_owner()
	var verb := "装备"
	if focus == motion_button: verb = "切换"
	elif focus == back_button: verb = "返回"
	menu_hint.text = verb if using_pointer and not pad else ("A  " if pad else "Enter  ") + verb

func _reduce(on: bool) -> void:
	reduce_motion = on
	if on:
		chart.scan_phase = -1.0
		chart.symbols.queue_redraw()

func _open_menu() -> void:
	if overlay.visible: return
	return_focus = get_viewport().gui_get_focus_owner()
	chart_contact = false
	_fit_menu()
	overlay.show()
	scan_button.get_parent().hide()
	_refresh()
	probe_buttons[equipped].grab_focus()
	_preview(equipped)
	_position_menu.call_deferred()

func _close_menu() -> void:
	if not overlay.visible: return
	overlay.hide()
	chart.clear_probe_preview()
	scan_button.get_parent().show()
	stick_direction = 0
	wait_for_neutral = _movement().length_squared() > .01
	if is_instance_valid(return_focus) and return_focus.is_visible_in_tree():
		return_focus.grab_focus()
	else: grab_focus()
	_refresh()

func _equip(i: int) -> void:
	if not overlay.visible: return
	equipped = i
	_note("已装备%s" % PROBES[i].name)
	_close_menu()

func _toggle_chart() -> void:
	if not overlay.visible:
		chart.set_light_chart(not chart.paper)
		_refresh()

func _note(message: String) -> void:
	note = message
	note_remaining = 1.8

func _scan() -> void:
	if overlay.visible or cooldown > 0:
		return
	var probe: Dictionary = PROBES[equipped]
	if energy < float(probe.cost):
		_note("储能不足，本次测深需要 %d%%" % probe.cost)
		_refresh()
		return
	energy -= float(probe.cost)
	cooldown = float(probe.interval)
	scans += 1
	last_depth = chart.water_depth(chart.cursor)
	var found := chart.record_scan(float(probe.radius)*_range_scale(),probe.arc,reduce_motion)
	_note("水深 %d m%s" % [last_depth, "  ·  新测站 +%d" % found if found else ""])
	_refresh()

func _range_scale() -> float:
	return minf(size.x/1120.0,size.y/680.0)

func _refresh() -> void:
	var active_probe: Dictionary = PROBES[previewed if overlay.visible else equipped]
	charge_label.text = "储能 %d%%  ·  %s可测 %d 次" % [floori(energy),"预览" if overlay.visible else "",floori(energy/float(active_probe.cost))]
	stock.value = energy
	count_label.text = "测站   %d / %d" % [chart.surveyed.size(),chart.STATIONS.size()]
	probe_label.text = PROBES[equipped].name
	if note_remaining > 0:
		response.text = note
	else:
		response.text = "上次水深  %d m" % last_depth if last_depth >= 0 else "等待首次回波"
	device_hint.text = "左摇杆 / 方向键移动" if pad else "方向键移动 · 点海图定位"
	scan_button.text = ("回波 %.1f s" % cooldown) if cooldown > 0 else ("测深  A" if pad else "测深  空格")
	gear_button.text = "探头  Y" if pad else "探头  E"
	chart_button.text = "海图明暗  X" if pad else "海图明暗  M"
	back_button.text = "返回  B" if pad else "返回  Esc"
	_update_menu_hint()
	for i in probe_buttons.size():
		probe_buttons[i].text = ("%s  · 已装" % PROBES[i].name) if i == equipped else str(PROBES[i].name)

func _movement() -> Vector2:
	return Input.get_vector("survey_left","survey_right","survey_up","survey_down")

func _process(delta: float) -> void:
	if overlay.visible:
		if stick_direction:
			repeat_in -= delta
			if repeat_in <= 0:
				_step_menu(stick_direction)
				repeat_in = .14
		return
	var direction := _movement()
	if wait_for_neutral:
		wait_for_neutral = direction.length_squared() > .01
	elif direction.length_squared() > .001:
		chart.move_to(chart.cursor + direction*delta*205.0/size)
	chart.advance_scan(delta)
	var previous_energy := floori(energy)
	var previous_time := ceili(cooldown*10)
	var had_note := note_remaining > 0
	energy = minf(100.0,energy+delta*2.0)
	cooldown = maxf(0.0,cooldown-delta)
	note_remaining = maxf(0.0,note_remaining-delta)
	if previous_energy!=floori(energy) or previous_time!=ceili(cooldown*10) or (had_note and note_remaining==0):
		_refresh()

func _step_menu(direction: int) -> void:
	var i := controls.find(get_viewport().gui_get_focus_owner())
	controls[posmod(i+direction,controls.size())].grab_focus()

func _input(event: InputEvent) -> void:
	if not is_node_ready(): return
	var is_pad: bool = event is InputEventJoypadButton and event.pressed
	if event is InputEventJoypadMotion and absf(event.axis_value) >= .56: is_pad = true
	var is_kbm: bool = (event is InputEventKey and event.pressed) or (event is InputEventMouseButton and event.pressed)
	if event is InputEventMouseMotion and event.relative.length_squared() >= 4: is_kbm = true
	if is_pad or is_kbm:
		using_pointer = event is InputEventMouseButton or event is InputEventMouseMotion
	if is_pad: last_pad = event.device
	if (is_pad and not pad) or (is_kbm and pad):
		pad = is_pad
		_refresh()
	if overlay.visible and event is InputEventJoypadMotion:
		# Native D-pad/keyboard use the focus graph; the stick has a separate neutral band.
		if event.axis == JOY_AXIS_LEFT_Y:
			var value: float = event.axis_value
			if absf(value) <= .30: stick_direction = 0
			elif absf(value) >= .56 and signf(value) != stick_direction:
				stick_direction = 1 if value > 0 else -1
				_step_menu(stick_direction)
				repeat_in = .34
		if event.axis in [JOY_AXIS_LEFT_X,JOY_AXIS_LEFT_Y]:
			get_viewport().set_input_as_handled()
			return
	if not (event is InputEventKey or event is InputEventJoypadButton): return
	var token: String
	if event is InputEventKey: token = "k%d" % event.keycode
	else: token = "p%d:%d" % [event.device,event.button_index]
	if held_actions.has(token):
		if not event.is_pressed(): held_actions.erase(token)
		get_viewport().set_input_as_handled()
		return
	if not event.is_pressed() or event.is_echo(): return
	if event.is_action_pressed("survey_gear"):
		if overlay.visible: _close_menu()
		else: _open_menu()
	elif overlay.visible:
		if not event.is_action_pressed("ui_cancel"): return
		_close_menu()
	elif event.is_action_pressed("survey_scan"): _scan()
	elif event.is_action_pressed("survey_chart"): _toggle_chart()
	else: return
	held_actions[token] = true
	get_viewport().set_input_as_handled()

func _gui_input(event: InputEvent) -> void:
	if overlay.visible: return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed: chart_contact = true
		elif chart_contact:
			chart_contact = false
			chart.move_to(event.position/size)
			grab_focus()

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		held_actions.clear()
		stick_direction = 0
		chart_contact = false
		wait_for_neutral = true

func _joy_connection(device: int, connected: bool) -> void:
	if not connected and device == last_pad:
		pad = false
		last_pad = -1
		stick_direction = 0
		for key in held_actions.keys():
			if str(key).begins_with("p%d:" % device): held_actions.erase(key)
		_refresh()
