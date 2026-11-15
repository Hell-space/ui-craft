extends Control

const Addon = preload("res://addons/compare.gd")
const ITEMS := [
	{"name":"凿锤","force":7,"speed":3},
	{"name":"曲刃刀","force":4,"speed":8},
	{"name":"棘轮扳手","force":6,"speed":5}
]
const PACKS := [
	{"ink":"#1e2c2a","body":"#4d6451","edge":"#bad49b","paper":"#e6edc8","type":"#20392f","mark":"#eab863","metal":"#c2ddd0","timber":"#b48854"},
	{"ink":"#2c2442","body":"#635681","edge":"#d5b4df","paper":"#f5e2e9","type":"#392d4b","mark":"#ffab76","metal":"#c6c8e3","timber":"#bb8c90"}
]
var equipped := 0
var selected := 1
var pack := 0
var gui_zoom := 1.0
var compare
var slots: Array[Button] = []
var inventory: PanelContainer
var caption: Label
var pack_button: Button
var zoom_button: Button

func paint(role: String) -> Color:
	return Color(PACKS[pack][role])

func frame(solid: String, edge: String, width := 2) -> StyleBoxFlat:
	var skin := StyleBoxFlat.new()
	skin.bg_color = paint(solid)
	skin.border_color = paint(edge)
	skin.set_border_width_all(width)
	skin.content_margin_left = 9
	skin.content_margin_right = 9
	skin.content_margin_top = 6
	skin.content_margin_bottom = 6
	return skin

func apply_button(b: Button, chosen := false) -> void:
	b.add_theme_stylebox_override("normal",frame("body","mark" if chosen else "ink"))
	b.add_theme_stylebox_override("hover",frame("body","edge"))
	b.add_theme_stylebox_override("pressed",frame("ink","edge"))
	var focus_skin := frame("body","paper",2)
	focus_skin.draw_center = false
	b.add_theme_stylebox_override("focus",focus_skin)
	b.add_theme_color_override("font_color",paint("paper"))
	b.add_theme_font_size_override("font_size",15)

func icon(which: int) -> Texture2D:
	var img := Image.create_empty(16,16,false,Image.FORMAT_RGBA8)
	var rows: Array = [
		["............XX..",".........XXMMM..",".......XMMMMMM..","......XMMMMMMM..","......MMMMMMMM..","......MMMMXX....","......XXWX......",".......WW.......","......WW........",".....WW.........","....WW..........","...WW...........","..WW............"],
		[".............M..","............MM..","...........MM...",".........MMMM...","........MMMM....",".......MMM......","......MMM.......","..X..MMM........","...XXXM.........","....XXX.........","...WW.XX........","..WW............",".WW............."],
		["..........XX..X.",".........MMX..M.",".........MM...M.",".........MMMMMM.","..........MMM...",".........MM.....","........MM......",".......MM.......","......MM........",".....MM.........","....MMM.........","...M..M.........","...MMMM.........","....MM.........."]
	][which]
	for y in rows.size():
		var row: String = rows[y]
		for x in row.length():
			var ch := row.substr(x,1)
			if ch != ".":
				img.set_pixel(x,y,paint("metal" if ch=="M" else ("ink" if ch=="X" else "timber")))
	return ImageTexture.create_from_image(img)

func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	inventory=PanelContainer.new()
	add_child(inventory)
	var box := VBoxContainer.new()
	inventory.add_child(box)
	caption=Label.new()
	box.add_child(caption)
	var list := HBoxContainer.new()
	list.add_theme_constant_override("separation",6)
	box.add_child(list)
	for i in ITEMS.size():
		var b:=Button.new()
		b.custom_minimum_size=Vector2(86,44)
		b.focus_mode=Control.FOCUS_ALL
		b.expand_icon=false
		b.pressed.connect(select.bind(i))
		list.add_child(b)
		slots.append(b)
	var settings:=HBoxContainer.new()
	box.add_child(settings)
	pack_button=Button.new();zoom_button=Button.new()
	settings.add_child(pack_button);settings.add_child(zoom_button)
	pack_button.pressed.connect(change_pack);zoom_button.pressed.connect(change_scale)
	pack_button.text="更换资源包";zoom_button.text="界面放大"
	compare=Addon.new()
	add_child(compare)
	compare.attach(self)
	resized.connect(refresh)
	refresh()
	slots[selected].grab_focus()

func select(i: int) -> void:
	selected=posmod(i,ITEMS.size())
	slots[selected].grab_focus()
	refresh()

func change_pack() -> void:
	pack=1-pack
	refresh()

func change_scale() -> void:
	gui_zoom=1.25 if gui_zoom==1.0 else 1.0
	zoom_button.text="原始尺寸" if gui_zoom>1.0 else "界面放大"
	refresh()

func refresh() -> void:
	if not is_instance_valid(compare):return
	var k: float=minf(gui_zoom,(size.x-20.0)/350.0)
	inventory.add_theme_stylebox_override("panel",frame("body","ink",3))
	caption.text="工具箱"
	caption.add_theme_color_override("font_color",paint("paper"))
	caption.add_theme_font_size_override("font_size",16)
	for i in slots.size():
		var b:=slots[i]
		b.text=ITEMS[i].name
		b.icon=icon(i)
		b.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
		apply_button(b,i==equipped)
	for b in [pack_button,zoom_button]:apply_button(b)
	inventory.reset_size()
	inventory.scale=Vector2.ONE*k
	inventory.position=Vector2(12,size.y-inventory.size.y*k-12).round()
	compare.refresh(k,inventory.position)
	queue_redraw()

func _navigation_active() -> bool:
	var owner:=get_viewport().gui_get_focus_owner()
	return owner==null or slots.has(owner)

func _input(event: InputEvent) -> void:
	if slots.is_empty():return
	var delta:=0
	var commit:=false
	var close_tip:=false
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_LEFT:delta=-1
			KEY_RIGHT:delta=1
			KEY_ENTER,KEY_SPACE:commit=slots.has(get_viewport().gui_get_focus_owner())
			KEY_ESCAPE:close_tip=true
			KEY_P:change_pack()
			KEY_Z:change_scale()
	elif event is InputEventJoypadButton and event.pressed:
		match event.button_index:
			JOY_BUTTON_DPAD_LEFT:delta=-1
			JOY_BUTTON_DPAD_RIGHT:delta=1
			JOY_BUTTON_A:commit=_navigation_active()
			JOY_BUTTON_B:close_tip=true
	if delta and _navigation_active():
		compare.visible=true
		select(selected+delta)
	elif commit:
		equipped=selected
		compare.visible=true
		refresh()
	elif close_tip:
		compare.hide();slots[selected].grab_focus()
	else:return
	get_viewport().set_input_as_handled()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO,size),paint("ink"))
	var tile:=16
	var cols:=ceili(size.x/tile)+1
	var rows:=ceili(size.y/tile)+1
	for y in rows:
		for x in cols:
			var n:=posmod(x*7+y*17+x*y*3,11)
			var col:=paint("body").darkened(.24+float(n%4)*.04)
			draw_rect(Rect2(x*tile,y*tile,tile,tile),col)
			if n==1:draw_rect(Rect2(x*tile+4,y*tile+8,5,2),paint("edge").darkened(.58))
	# A wall of three workbench alcoves keeps the workshop legible behind the native tooltip.
	for i in range(-1,ceili(size.x/170)+1):
		var x:=i*170+40
		draw_rect(Rect2(x,25,126,74),paint("ink"))
		draw_rect(Rect2(x+4,29,118,65),paint("body").lightened(.04))
		for j in 5:
			draw_rect(Rect2(x+11+23*j,37,4,34+posmod(j*i,3)*4),paint("timber"))
			draw_rect(Rect2(x+8+23*j,37,13,8),paint("metal").darkened(.22))
		draw_rect(Rect2(x-5,94,137,9),paint("timber"))
		draw_rect(Rect2(x+4,102,10,32),paint("ink"));draw_rect(Rect2(x+112,102,10,32),paint("ink"))

