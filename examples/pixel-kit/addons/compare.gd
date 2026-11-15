extends PanelContainer
# Only the comparison belongs to the add-on. The host owns slots, item state, skin and GUI scaling.
var host
var heading: Label
var basis: Label
var values: Label
var identity: TextureRect

func attach(world) -> void:
	host=world
	mouse_filter=Control.MOUSE_FILTER_IGNORE
	var row:=HBoxContainer.new()
	row.add_theme_constant_override("separation",10)
	add_child(row)
	identity=TextureRect.new()
	identity.custom_minimum_size=Vector2(43,43)
	identity.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
	identity.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	identity.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
	row.add_child(identity)
	var content:=VBoxContainer.new()
	content.add_theme_constant_override("separation",1)
	row.add_child(content)
	heading=Label.new();basis=Label.new();values=Label.new()
	for label in [heading,basis,values]:content.add_child(label)

func delta(value: int) -> String:
	return ("+"+str(value)) if value>0 else ("−"+str(-value) if value<0 else "0")

func refresh(k: float,slot_origin: Vector2) -> void:
	var candidate: Dictionary=host.ITEMS[host.selected]
	var worn: Dictionary=host.ITEMS[host.equipped]
	add_theme_stylebox_override("panel",host.frame("paper","ink",3))
	identity.texture=host.icon(host.selected)
	heading.text=candidate.name
	basis.text="已装备 · "+worn.name
	values.text="力度 "+delta(candidate.force-worn.force)+"     速度 "+delta(candidate.speed-worn.speed)
	for label in [heading,basis,values]:label.add_theme_color_override("font_color",host.paint("type"))
	heading.add_theme_font_size_override("font_size",18)
	basis.add_theme_font_size_override("font_size",13)
	values.add_theme_font_size_override("font_size",15)
	scale=Vector2.ONE*k
	reset_size()
	position=Vector2(clampf(slot_origin.x+host.selected*28*k,8,host.size.x-size.x*k-8),slot_origin.y-size.y*k-7).round()

