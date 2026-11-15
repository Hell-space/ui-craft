extends Control

var span := 210.0
var angle := 360.0

func set_probe(radius: float, degrees: float) -> void:
	span = radius
	angle = degrees
	queue_redraw()

func _draw() -> void:
	var center := size*Vector2(.5,.50)
	var extent := minf(size.x,size.y)*.40
	var line := Color("#55756d")
	var mark := Color("#ffb17b")
	var muted := Color("#81a69b")
	var radius := extent*span/210.0
	draw_rect(Rect2(Vector2.ZERO,size),Color("#0b2127"))
	for scale in [.33,.67,1.0]:
		draw_arc(center,extent*scale,0,TAU,80,Color(line,.65),1,true)
	for i in 24:
		var n := Vector2.from_angle(i*TAU/24)
		var length := 5.0 if i%3==0 else 2.0
		draw_line(center+n*(extent+2), center+n*(extent+2+length),muted,1,true)
	var start := -PI/2-deg_to_rad(angle)*.5
	var stop := -PI/2+deg_to_rad(angle)*.5
	var patch := PackedVector2Array()
	if angle<360.0: patch.append(center)
	var segments := 80
	for i in (segments if angle==360.0 else segments+1):
		patch.append(center+Vector2.from_angle(lerpf(start,stop,float(i)/segments))*radius)
	draw_colored_polygon(patch,Color(mark,.18))
	draw_arc(center,radius,start,stop,segments,mark,1.8,true)
	if angle<360.0:
		draw_line(center,center+Vector2.from_angle(start)*radius,mark,1.4,true)
		draw_line(center,center+Vector2.from_angle(stop)*radius,mark,1.4,true)
	draw_colored_polygon(PackedVector2Array([center+Vector2(0,-7),center+Vector2(4,4),center+Vector2(-4,4)]),Color("#f4f1dd"))
