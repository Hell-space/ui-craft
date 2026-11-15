"""Repaint the bundled 640 × 360 scene layers with Pillow. The game uses the PNGs directly."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art"
LAYOUT = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
SIZE = (640, 360)
HORIZON = 114


def rgb(value):
    return tuple(bytes.fromhex(value))


def mix(first, second, amount):
    if isinstance(first, str):
        first = rgb(first)
    if isinstance(second, str):
        second = rgb(second)
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))


class Ink:
    def __init__(self, size=SIZE):
        self.im = Image.new("RGBA", size)
        self.pen = ImageDraw.Draw(self.im)

    @staticmethod
    def color(value):
        return "#" + value if isinstance(value, str) else value

    def poly(self, pts, color):
        self.pen.polygon([(round(x), round(y)) for x, y in pts], self.color(color))

    def line(self, pts, color, w=1):
        self.pen.line([(round(x), round(y)) for x, y in pts], self.color(color), width=w)

    def box(self, x, y, w, h, color):
        if w > 0 and h > 0:
            self.pen.rectangle((x, y, x+w-1, y+h-1), fill=self.color(color))

    def oval(self, x, y, rx, ry, color):
        self.pen.ellipse((x-rx, y-ry, x+rx, y+ry), fill=self.color(color))

    def curve(self, a, b, c, color, w=1):
        pts = []
        for index in range(33):
            t = index / 32
            u = 1-t
            pts.append((a[0]*u*u+2*b[0]*u*t+c[0]*t*t, a[1]*u*u+2*b[1]*u*t+c[1]*t*t))
        self.line(pts, color, w)

    def save(self, name):
        self.im.save(OUT / name, optimize=True)


def add_clip(base, drawing, points):
    mask = Image.new("L", SIZE)
    ImageDraw.Draw(mask).polygon(points, 255)
    base.im.paste(drawing.im, mask=mask)


def distant_mill(s, x, y, size, color, light):
    points = [(0,0),(1,-12),(6,-12),(6,-17),(13,-17),(13,-12),(17,-12),(17,-3),
              (20,-3),(20,-14),(22,-15),(25,-14),(25,-7),(35,-7),(36,-12),(43,-18),
              (50,-12),(50,-5),(56,-5),(57,-25),(60,-25),(61,-5),(68,-5),(68,0)]
    s.poly([(x+px*size, y+py*size) for px,py in points], color)
    for offset in (8, 11, 41, 45):
        s.box(round(x+offset*size), round(y-10*size), 1, 2, light)


def crane(s, x, y, scale, dark, light):
    def path(pts, color, w=1):
        s.line([(x+px*scale, y+py*scale) for px,py in pts], color, w)
    path([(-6,0),(-3,-29),(2,-38),(7,0)], dark, 2)
    path([(-4,-18),(4,-26),(-2,-27),(3,-34),(-2,-35)], light)
    path([(-11,-28),(1,-40),(41,-59),(42,-57),(5,-35),(-9,-23)], dark)
    path([(15,-46),(16,-43),(25,-51),(26,-48),(36,-56),(36,-54)], dark)
    path([(39,-57),(39,-27),(37,-25)], light)
    path([(-6,-1),(0,-12),(6,-4)], light)


def landscape():
    s = Ink()
    rng = random.Random(734)
    sky = ["86acaf", "aac3bd", "d3d7bf", "e4d9ba", "dfd6b9"]
    for y in range(HORIZON+1):
        p = y/HORIZON*(len(sky)-1)
        i = min(len(sky)-2, int(p))
        s.box(0, y, 640, 1, mix(sky[i], sky[i+1], p-i))
    # The pale disk is occluded by two ribbons of cloud and the far ridge.
    s.oval(467, 64, 19, 19, "e9e2c3")
    s.oval(467, 64, 16, 16, "f2e6c6")
    for x, y, w in [(166,23,83),(281,37,47),(486,29,73),(409,65,76),(529,51,67),
                    (209,55,53),(90,45,57),(22,21,78),(331,12,40)]:
        for j in range(rng.randrange(3,6)):
            dx = rng.randrange(0,14)
            line_color = mix(s.im.getpixel((min(639,x),y))[:3], "eee1be", rng.uniform(.18,.4))
            s.line([(x+dx, y+j), (x+w//2+dx, y+j), (x+w-rng.randrange(2,18),y+j)], line_color)
    for baseline, amp, color, phase in [(94,9,"b4c5b4",1.1),(104,7,"a6bcb1",4.8)]:
        outline = []
        for x in range(-4,648,4):
            yy = baseline+math.sin(x*.021+phase)*amp+math.cos(x*.043+phase)*3+math.sin(x*.011)*4
            outline.append((x, yy))
        s.poly(outline+[(645,118),(-5,118)], color)
    distant_mill(s, 82, 113, .79, "9bb2a8", "afc1b3")
    distant_mill(s, 193, 113, .64, "97b0a6", "b4c3b0")
    distant_mill(s, 395, 114, .96, "92aaa3", "b7c4ae")
    distant_mill(s, 475, 114, .66, "8fa9a2", "afbdac")
    crane(s, 312, 114, .57, "94aca4", "a7bab0")
    crane(s, 383, 115, .74, "8fa9a3", "a3b7aa")
    s.line([(0,115),(114,114),(170,116),(270,114),(360,115),(440,113),(640,115)], "98b0a4", 2)
    # Distance resolves into long, cool brush marks. Nearer water deepens under the piers.
    for y in range(116,360):
        t = (y-116)/243
        if t < .36:
            c = mix("a7beb0","548989",t/.36)
        else:
            c = mix("548989","284e55",(t-.36)/.64)
        s.box(0,y,640,1,c)
    for i in range(4300):
        y = rng.randrange(117,360)
        x = rng.randrange(-12,640)
        t = (y-117)/243
        w = max(1,int((rng.random()**2)*(7+13*t)))
        c = s.im.getpixel((max(0,x),y))[:3]
        tint = "cee0c6" if rng.random()<.48 else "215e68"
        s.box(x,y,w,1,mix(c,tint,rng.uniform(.07,.29)))
    for y in range(117,208,2):
        t=(y-117)/100
        for j in range(rng.randrange(2,6)):
            x=round(467+rng.gauss(0,4+42*t))
            w=rng.randrange(2,13)
            s.box(x,y,w,1,mix(s.im.getpixel((min(639,max(0,x)),y))[:3],"ecdfb9",rng.uniform(.2,.68)*(1-t*.45)))
    # A low fishing cutter behind the yard.
    x, y = 328, 140
    s.oval(x,y+2,20,1,"80a39c")
    s.poly([(x-20,y-2),(x-10,y-1),(x+13,y-1),(x+22,y-5),(x+18,y),(x+11,y+2),(x-14,y+2)],"688f8c")
    s.poly([(x-12,y-7),(x-3,y-7),(x-2,y-2),(x-13,y-2)],"88a39a")
    s.box(x-9,y-8,8,1,"b3beaa")
    s.box(x-8,y-6,2,2,"71938d")
    s.line([(x+2,y-2),(x+2,y-25)],"849f96")
    s.line([(x+2,y-23),(x+17,y-2)],"97afa2")
    for bx,by in [(243,64),(251,62),(344,78),(349,76)]:
        s.line([(bx-2,by-1),(bx,by),(bx+2,by-2)], "8ca7a2")
    return s


def repaired_hull(s):
    """The crooked bow, ribs, cradle and open shed occupy the back edge of the playable apron."""
    legs = [(14,175,22,205),(68,181,77,205),(126,180,134,205),(159,172,167,205)]
    for x,y,x2,y2 in legs:
        s.poly([(x,y),(x+7,y),(x2+5,y2),(x2,y2)],"544f45")
        s.line([(x+1,y),(x2,y2)],"9d8666",2)
    edge=[(-10,143),(18,147),(43,151),(78,150),(111,146),(147,140),(167,134),(175,128),
          (170,144),(160,156),(143,167),(115,175),(82,181),(49,182),(18,177),(-8,165)]
    s.poly([(x+1,y+1) for x,y in edge],"263f40")
    s.poly(edge,"6c6553")
    s.poly([(-5,148),(35,155),(77,154),(111,149),(149,143),(169,137),(164,146),(137,156),(90,164),
            (50,167),(12,159),(-5,156)],"a8916d")
    s.poly([(-6,156),(41,165),(83,164),(130,157),(163,145),(159,152),(144,161),(110,169),
            (75,174),(42,174),(11,168),(-6,163)],"82745b")
    s.poly([(-6,163),(31,174),(74,177),(116,171),(143,163),(135,169),(112,176),
            (80,182),(53,183),(23,179),(-6,169)],"555b4f")
    s.curve((-6,162),(74,188),(159,151),"615d50")
    s.curve((-4,152),(66,172),(164,140),"ceb48b",2)
    s.curve((-8,157),(72,179),(161,147),"5c6050")
    s.curve((-5,164),(66,185),(148,158),"9a8868")
    s.curve((-6,146),(55,164),(163,137),"3a4c48",3)
    s.curve((-4,143),(58,159),(161,136),"c7ae83",2)
    s.line([(156,143),(167,130),(173,124),(177,125),(171,141),(164,150)],"444f47",3)
    s.line([(164,138),(173,126),(175,126)],"c3a778",2)
    for x in range(7,155,13):
        middle=1-((x-75)/87)**2
        y=round(145+9*middle-0.036*x)
        s.line([(x,y),(x+1,y+2)],"514f42")
        s.box(x-1,y+6,2,1,"6a6450")
    s.poly([(19,149),(20,132),(32,128),(62,128),(68,150)],"59695d")
    s.poly([(16,132),(30,124),(63,124),(68,129),(34,130),(18,135)],"9c9576")
    for x in (25,34,43,53):
        s.box(x,132,6,7,"89998a"); s.box(x+1,133,4,4,"4e6866")
    s.box(20,140,43,2,"bc9e75")
    s.line([(76,149),(79,97),(81,97),(80,149)],"635e4f",2)
    s.line([(79,104),(101,147)],"8d8c71")
    # Timber cradle and wedges prevent the boat from reading as another walking platform.
    for x,y in [(33,181),(107,178)]:
        s.line([(x-13,204),(x+3,y-1),(x+17,204)],"3e514a",4)
        s.line([(x-12,203),(x+2,y),(x+4,y)],"ad9673",2)
        s.box(x-16,202,37,3,"655f4f")
    s.line([(5,199),(129,199)],"655e4e",3)


def gantry(s):
    # Heat-darkened lifting frame. Portions of ropes disappear behind the hanging sail.
    s.poly([(2,204),(9,37),(17,34),(17,204)],"354e4c")
    s.poly([(9,37),(13,36),(11,204),(5,204)],"726e56")
    s.poly([(147,200),(151,48),(159,45),(157,203)],"40544c")
    s.line([(153,59),(150,196)],"a08e68",2)
    s.poly([(8,81),(12,79),(53,47),(65,44),(13,94),(8,97)],"566153")
    s.line([(15,86),(55,49)],"a08f6d",2)
    s.poly([(115,51),(122,50),(152,78),(151,86)],"546052")
    s.poly([(-9,28),(13,26),(69,35),(114,37),(164,42),(163,49),(113,45),(66,43),(2,35),(-9,36)],"4a5550")
    s.line([(-9,28),(15,27),(65,34),(109,36),(163,41)],"aba17e",2)
    s.line([(0,35),(67,44),(114,46),(162,49)],"344e4d",2)
    for x in (11,16,146,155):
        y=round(31+x*.09)
        s.box(x,y,2,6,"7d826a")
    for x,y in [(24,39),(116,47)]:
        s.line([(x,y),(x-1,y+43)],"646c56",2)
        s.oval(x-1,y+43,3,5,"435750")
        s.line([(x-1,y+41),(x-2,y+46)],"a49c75")
        s.line([(x-2,y+48),(x-2,y+62),(x+2,y+65),(x+4,y+61)],"56685d")
    s.box(148,79,10,5,"374f49")
    s.box(148,119,9,4,"4c5c50")
    s.box(5,136,10,5,"384e49")


def lighthouse_shed(s):
    # Corrugated tin roof, tarred sidings and a lamp above the boatyard door.
    outer=[(509,204),(509,124),(548,99),(618,100),(644,118),(648,204)]
    s.poly(outer,"3c5654")
    s.poly([(511,125),(548,101),(548,203),(511,203)],"6d8175")
    s.poly([(550,114),(640,116),(640,205),(550,204)],"526c65")
    rng = random.Random(130)
    for x in range(514,548,4):
        y=round(124-(x-510)*.62)
        s.line([(x,y),(x,201)],mix("6d8175","384f4d",rng.uniform(.25,.66)))
        s.line([(x+1,y),(x+1,196)],mix("6d8175","c7b89a",rng.uniform(.08,.33)))
    for x in range(551,644,5):
        s.line([(x,119),(x,203)],"445f5a")
        s.line([(x+1,119),(x+1,201)],mix("59736b","b9b198",rng.uniform(0,.39)))
    s.poly([(500,126),(542,97),(613,93),(647,108),(649,116),(548,118),(506,132)],"3a5351")
    s.poly([(503,124),(541,96),(614,92),(646,106),(646,111),(548,113),(507,128)],"858c76")
    s.poly([(509,124),(545,99),(616,95),(644,109),(549,111)],"a49c7c")
    for i in range(0,73,5):
        x=545+i
        s.line([(x, round(98-i*.05)),(x+20,round(111-i*.036))],"797f69")
        s.line([(x+1,round(98-i*.05)),(x+21,round(111-i*.036))],"b8ab87")
    s.line([(505,128),(547,114),(642,112)],"c3b28b",2)
    s.line([(549,117),(641,116)],"344f4d",3)
    s.poly([(560,203),(560,137),(595,135),(595,203)],"334e4c")
    s.poly([(564,201),(564,141),(591,140),(591,201)],"263f40")
    s.box(566,145,4,56,"485b4e"); s.box(574,154,3,41,"374b43")
    s.box(558,136,38,3,"a29777"); s.box(558,139,3,64,"91896b")
    s.box(606,137,25,23,"324d49"); s.box(608,139,21,19,"788f80")
    s.box(610,141,17,15,"a6afa0"); s.box(616,139,2,19,"566e64"); s.box(608,147,21,2,"607369")
    s.line([(609,147),(615,141)],"c2c4a6")
    s.box(607,159,25,2,"a69b79")
    for x in (513,547,635):
        s.box(x,162,3,39,"536456")
    s.box(509,201,133,4,"3b4e44")
    # Lamp housing is retained in both proofing modes.
    s.line([(572,134),(572,125),(581,125),(581,128)],"384d49",2)
    s.poly([(575,132),(578,128),(583,128),(586,132)],"485851")
    s.box(578,132,5,3,"d6bd88"); s.box(579,132,3,2,"ebd3a1")
    s.box(527,129,8,11,"4b655d")
    for y in (131,134,137):
        s.box(528,y,6,1,"8e9b81")


def sea_piles(s, x, top, bottom, width, tilt, rng):
    s.poly([(x,top),(x+width,top),(x+width+tilt,bottom),(x+tilt+2,bottom+1)],"314c4b")
    s.poly([(x+1,top),(x+4,top),(x+4+tilt,bottom-1),(x+1+tilt,bottom)],"716e55")
    s.line([(x+5,top+6),(x+5+tilt,bottom-5)],"526254")
    s.box(x-1,top+8,width+2,4,"46554b")
    s.box(x+1,top+8,width,1,"8f8669")
    s.box(x+tilt-1,bottom-3,width+3,2,"576f60")
    for _ in range(6):
        y=rng.randrange(top+12,bottom-4)
        s.box(x+rng.randrange(2,width),y,1,rng.randrange(2,7),"7c795c")
    for j in range(5):
        s.box(x+rng.randrange(-4,width+2),bottom+2+j*2,rng.randrange(4,14),1,"4a746c")


def dock_pieces(s):
    rng=random.Random(669)
    for left,right in [(-22,326),(407,664)]:
        for x in range(left+10,right-22,39):
            end=rng.randrange(283,311)
            s.poly([(x+1,258),(x+6,259),(x+33,end-5),(x+29,end-3)],"49594e")
            s.line([(x+4,260),(x+31,end-5)],"8d8162")
        for x in range(left+9,right,35):
            sea_piles(s,x,248,rng.randrange(288,310),rng.randrange(6,10),rng.choice([-2,0,1,2]),rng)
        s.box(left,251,right-left,11,"4e554a")
        s.box(left,256,right-left,3,"756b52")
        s.box(left,260,right-left,3,"414f46")
        for x in range(left+4,right,11):
            s.box(x,253,rng.randrange(3,9),1,"8e7f61")
    for label in ("left_quay","right_quay"):
        pts=[tuple(v) for v in LAYOUT[label]]
        wooden=Ink(); wooden.box(0,0,640,360,"a69069")
        for x in range(-22,657,9):
            mid=rng.randrange(-7,7)
            col=mix("a99470","bea981",rng.random()*.64) if mid>=0 else mix("ac9771","857c5f",-mid/14)
            wooden.poly([(x,202),(x+9,202),(x+15,253),(x+4,253)],col)
            wooden.line([(x+8,202),(x+14,253)],"887c5d")
            wooden.line([(x+9,202),(x+15,253)],"baaa81")
            for _ in range(7):
                xx = x+rng.randrange(2,8); yy=rng.randrange(206,249)
                wooden.line([(xx+(yy-204)//8,yy),(xx+(yy-204)//8+rng.choice([0,1]),yy+rng.randrange(1,6))],
                             mix(col,"615f4b",rng.uniform(.1,.3)))
            for yy in (209,247):
                wooden.box(x+5+(yy-205)//8, yy,1,1,"776f56")
        # Worn traffic surface gets a broad, quiet sunlit lane.
        for _ in range(92):
            xx,yy = rng.randrange(640),rng.randrange(215,242)
            wooden.box(xx,yy,rng.randrange(2,8),1,"bba77e")
        add_clip(s,wooden,pts)
        s.line([p for p in pts]+[pts[0]],"655f4c",2)
    s.line([(-4,205),(305,205),(317,208),(327,208)],"d9ca9f",2)
    s.line([(407,205),(642,205)],"d1c29b",2)
    s.line([(-6,250),(318,250)],"e0cfa0",2)
    s.line([(404,251),(643,251)],"deca9a",2)
    # Splinter faces and two broken joists frame the empty channel.
    for pts in [[(329,210),(324,215),(334,216)],[(328,221),(332,224),(326,229)],
                [(329,241),(322,245),(326,248)],[(408,217),(405,221),(410,224)],
                [(407,234),(404,237),(409,240)]]:
        s.line(pts,"e4d1a1",2)
    for x,y,sgn in [(321,248,1),(407,244,-1)]:
        s.poly([(x,y),(x+sgn*8,y+1),(x+sgn*13,y+5),(x+sgn*7,y+5),(x,y+4)],"817456")
        s.line([(x,y),(x+sgn*9,y+1)],"d6bd8e")
    for x in [9,62,121,181,241,307,414,476,533,605]:
        s.box(x,249,4,2,"62695a"); s.box(x,250,3,1,"afa47e")


def cargo_net(s, x, y, w, h):
    """Hand-knotted diamonds follow the weight of a trawl hung at three points."""
    def knot(u,v):
        sag = math.sin(math.pi*u)
        return (x+w*u + v*(4*math.sin(2*math.pi*u)-1),
                y+h*v*(.43+.57*sag)+5*sag+2*math.sin(5*u)+2*u)
    for i in range(10):
        u=i/9
        for j in range(5):
            v=j/5
            s.line([knot(u,v),knot(min(1,u+1/18),v+.10),knot(u,v+.20)],"586659")
            if i<9:
                s.line([knot(u+1/9,v),knot(u+1/18,v+.1),knot(u+1/9,v+.2)],"8b8b6d")
    s.line([knot(i/21,0) for i in range(22)],"b1a17a",2)
    s.line([knot(i/21,1) for i in range(22)],"696e57",2)
    for i in range(10):
        px,py=knot(i/9,0); s.box(round(px),round(py)-1,2,2,"c9b287")


def tarp(s):
    corners=[(29,49),(56,53),(92,52),(116,48),(110,76),(101,90),(100,96),(87,92),
             (80,87),(73,89),(65,80),(54,81),(43,68),(35,65)]
    s.poly([(x+1,y+2) for x,y in corners],"56685b")
    s.poly(corners,"bcaa83")
    s.poly([(29,49),(53,55),(63,63),(71,83),(65,80),(55,80),(45,66),(35,64)],"d1bd92")
    s.poly([(50,53),(77,55),(83,63),(91,86),(101,95),(87,91),(79,85),(73,88),(66,76)],"aa9673")
    s.poly([(76,54),(91,52),(97,56),(105,76),(100,90),(91,81),(85,67)],"d4bd90")
    s.poly([(103,51),(115,48),(108,77),(103,81),(100,66)],"947f65")
    s.line([(31,50),(55,55),(91,54),(115,49)],"e0cca0",2)
    s.line([(36,65),(44,68),(54,80),(64,79),(73,88),(81,86),(90,92),(100,96)],"87795e")
    s.line([(49,56),(58,61),(67,76)],"ac9875")
    s.line([(87,56),(92,65),(95,74)],"e1c99b")
    s.line([(92,84),(99,90)],"d1b98c")
    for x,y in [(28,47),(114,46)]:
        s.line([(x,y-6),(x+1,y+3)],"4f5d50",2)
        s.box(x,y,3,2,"d2bd90")
    # Stitched repair; sparse marks retain the large value shapes.
    s.poly([(57,64),(65,65),(67,71),(61,72)],"b7a17a")
    s.line([(57,64),(65,65),(67,71)],"907f64")
    s.box(60,66,2,1,"e0c79a")


def coil(s,x,y,rx,ry):
    for ring in range(3):
        dims=(x-rx+ring*2,y-ry+ring,x+rx-ring*2,y+ry-ring)
        if dims[2] > dims[0] and dims[3] >= dims[1]:
            s.pen.ellipse(dims,outline="#6c6954")
    for d in (0,2):
        s.pen.arc((x-rx+d,y-ry+d//2,x+rx-d,y+ry-d//2),195,320,fill="#b9a57a")
    s.line([(x+rx-2,y+1),(x+rx+3,y+3),(x+rx+10,y+2)],"99865f")


def crate(s,x,y,w,h):
    s.box(x,y,w,h,"696951"); s.box(x+1,y+1,w-2,h-2,"9c8b65")
    for xx in range(x+4,x+w-2,4):
        s.box(xx,y+1,1,h-2,"7f7759")
    s.line([(x+1,y+1),(x+w-2,y+1)],"c0aa7f",2)
    s.line([(x+1,y+h-2),(x+w-2,y+2)],"c2aa7b",2)
    s.box(x+1,y+h-2,w-2,2,"786f54")


def trawler_details(s):
    tarp(s)
    s.curve((6,100),(67,119),(148,93),"647260",2)
    cargo_net(s,10,101,49,34)
    for x,y in [(26,178),(39,178),(51,180)]:
        s.line([(x,y),(x-1,y+8)],"7d7d60")
    # Bucket, cleat, carpenter's saw trestle, stacked repair planks.
    for x,y in [(177,197),(192,197)]:
        s.line([(x-4,204),(x,y-8),(x+5,204)],"59634f",2)
    s.line([(171,192),(202,191)],"a89870",3)
    s.line([(179,190),(187,188)],"c2ad7f",2)
    s.line([(193,187),(198,186),(203,189),(201,191),(191,190)],"6c7a69",2)
    s.box(204,201,25,2,"7c7557"); s.box(202,198,25,2,"aa9970")
    s.box(207,196,17,2,"b6a37d")
    crate(s,3,190,18,15); crate(s,17,197,19,9)
    coil(s,239,202,8,3)
    # A short piece of laundry belongs to the workshop forecourt.
    s.curve((458,171),(483,184),(514,166),"6a7160")
    for x,y,col,dark in [(468,174,"b9b79a","9f9e80"),(481,176,"879d91","6e8b82"),(494,174,"c4bda0","a5aa8d")]:
        s.poly([(x,y),(x+8,y),(x+7,y+10),(x+2,y+12),(x,y+8)],col)
        s.line([(x+2,y+1),(x+3,y+9)],dark)
        s.box(x,y-1,2,3,"776f55")
    s.line([(458,164),(458,205)],"6b7260",2)
    s.box(456,166,5,2,"a39b76")
    # Hanging cork floats and rolled net beneath the shed window.
    cargo_net(s,598,170,40,24)
    for x in range(601,638,7):
        y=171+round(math.sin((x-601)/36*math.pi)*4)
        s.oval(x,y,2,2,"af9a70")
        s.box(x-1,y-1,2,1,"c3ad80")
    crate(s,591,192,17,12)
    coil(s,523,204,8,3)
    # A barrow wheel and two mending poles stay upstage of the lane.
    s.oval(541,199,4,4,"384e48"); s.oval(541,199,2,2,"9b9275")
    s.poly([(521,192),(540,190),(546,187),(543,196),(527,198)],"8e8566")
    s.line([(518,190),(527,194),(541,192)],"beaa7e",2)
    s.line([(616,200),(622,174)],"ac9a70",2)
    s.line([(620,202),(630,177)],"827d5f",2)


def rowboat(s):
    # The near skiff crops out of the left corner; its open interior exposes the ribs.
    rim=[(-12,278),(16,273),(50,272),(81,277),(110,285),(118,291),(104,299),
         (80,307),(49,310),(19,309),(-9,299)]
    s.poly([(x,y+5) for x,y in rim],"31545a")
    s.poly(rim,"b29b72")
    s.poly([(-11,281),(18,275),(49,275),(78,280),(105,287),(110,291),(98,296),
            (69,302),(40,304),(15,302),(-10,294)],"46615a")
    s.poly([(-8,284),(16,278),(54,280),(86,287),(103,291),(68,297),(48,297),(18,295)],"767860")
    for x,y in [(10,282),(33,281),(57,282),(79,286),(95,290)]:
        s.curve((x-4,y-3),(x-1,y+5),(x+6,y+10),"4e6154",2)
    for x,y in [(8,283),(37,283),(69,286)]:
        s.poly([(x-4,y-5),(x+2,y-6),(x+10,y+11),(x+5,y+12)],"b1a07a")
        s.line([(x-3,y-5),(x+4,y+10)],"d1ba8b")
    s.poly([(-9,294),(13,300),(45,305),(79,302),(103,296),(119,290),(113,299),
            (90,311),(60,316),(29,316),(5,312),(-9,307)],"627568")
    s.curve((-3,300),(55,325),(114,296),"b6a47b",2)
    s.curve((15,310),(72,326),(111,301),"3c5955",2)
    s.line([(-8,294),(20,302),(47,305),(78,302),(106,295),(117,290)],"d0bc91",2)
    s.line([(17,290),(61,280),(89,275)],"c0a980",2)
    s.poly([(79,276),(93,271),(98,273),(92,276),(80,278)],"a18c68")
    s.curve((115,291),(141,282),(147,254),"847b60")
    for x,y in [(20,319),(69,319),(94,315),(115,307)]:
        s.box(x,y,11,1,"779486")


def foreground(s):
    rng=random.Random(65)
    # Short planks enter in perspective from the bottom right. The water gap separates them from the route.
    face=[(444,360),(485,342),(521,332),(563,322),(583,316),(646,317),(646,360)]
    s.poly(face,"555e4f")
    s.line([(451,359),(486,343),(522,333),(556,325),(583,318),(643,317)],"a99d79",3)
    for x in range(468,667,13):
        s.line([(x,359),(x+30,328-max(0,(x-550)//18))],"6f7159",2)
    for x,y,h,w in [(560,333,44,10),(618,320,47,13)]:
        s.poly([(x,y),(x-2,y-h+2),(x+1,y-h-1),(x+w-3,y-h),(x+w,y-h+2),(x+w,y)],"3d5148")
        s.line([(x+1,y-2),(x,y-h+2)],"8d8968",2)
        s.oval(x+w//2-1,y-h+1,w//2-1,2,"a39973")
        for i in range(3):
            s.line([(x-1,y-h+8+i*2),(x+w,y-h+7+i*2)],"827e5e")
    s.curve((564,298),(590,322),(623,282),"a1936c",2)
    s.curve((563,299),(590,324),(622,283),"585f4c")
    for i in range(10):
        x=rng.randrange(555,639); y=rng.randrange(344,361)
        s.box(x,y,rng.randrange(3,9),1,"82816a")
    cargo_net(s,561,321,60,27)
    coil(s,603,342,12,4)
    crate(s,632,329,21,17)
    # Drift grass on a near pile at lower left is intentionally sparse.
    s.poly([(-8,361),(-7,342),(4,336),(13,337),(18,344),(26,345),(29,350),(37,352),(42,359)],"435849")
    for x in range(-4,27,3):
        y=348+rng.randrange(-1,8)
        s.line([(x-1,y+4),(x,y),(x-2,y-rng.randrange(3,9))],"74836b")


def night_palette(image):
    # Selective ink curve keeps far water, timber and lit edges on separate value steps.
    def tone(pixel):
        r,g,b,a=pixel
        if a==0:
            return (0,0,0,0)
        v=(.26*r+.60*g+.14*b)/255
        stops=((0,"182932"),(.23,"243e47"),(.40,"375660"),(.58,"577775"),
               (.76,"7d9690"),(1,"b8c2a6"))
        for (lo,one),(hi,two) in zip(stops,stops[1:]):
            if v<=hi:
                col=mix(one,two,(v-lo)/(hi-lo))
                break
        warm=max(0,(r-b)/100)
        return (min(255,round(col[0]+3*warm)),max(0,col[1]-round(warm)),max(0,col[2]-round(7*warm)),a)
    pixels=image.load()
    colors=[pixels[x,y] for y in range(image.height) for x in range(image.width)]
    table={color:tone(color) for color in set(colors)}
    result=Image.new("RGBA",image.size)
    result.putdata([table[color] for color in colors])
    return result


def make_night_windows(s):
    # A little of the day's timber warmth survives in the path after the water darkens.
    pixels=s.im.load()
    for label in ("left_quay","right_quay"):
        pts=[tuple(v) for v in LAYOUT[label]]
        mask=Image.new("1",SIZE)
        ImageDraw.Draw(mask).polygon(pts,1)
        area=mask.load()
        for y in range(204,252):
            for x in range(640):
                if area[x,y]:
                    r,g,b,a=pixels[x,y]
                    pixels[x,y]=(r+13,g+11,b+5,a)
    s.line([(-2,250),(317,250)],"a5b39d",2)
    s.line([(407,250),(641,250)],"acb59c",2)
    s.line([(-2,205),(308,205),(318,208),(329,208)],"a5ad92")
    s.line([(409,205),(641,205)],"a6ae95")
    for pts in [[(329,210),(324,215),(334,216)],[(328,221),(332,224),(326,229)],
                [(329,241),(322,245),(326,248)],[(408,217),(405,221),(410,224)],
                [(407,234),(404,237),(409,240)]]:
        s.line(pts,"b3ba9e",2)
    # Four panes and the shielded workshop lamp stay warmer than the evening light.
    s.box(610,141,17,15,"bfa67c")
    s.box(611,141,3,6,"cdb68b")
    s.box(620,148,6,6,"d4bb8f")
    s.box(616,139,2,19,"4d6560"); s.box(608,147,21,2,"5b7068")
    s.box(578,132,5,3,"d6b178"); s.box(579,132,3,2,"f0d29b")


def main():
    OUT.mkdir(exist_ok=True)
    base=landscape()
    repaired_hull(base); gantry(base); lighthouse_shed(base); dock_pieces(base)
    base.save("harbor.png")
    props=Ink()
    trawler_details(props); rowboat(props); foreground(props)
    props.save("gear.png")
    low=Ink(); low.im=night_palette(base.im); low.pen=ImageDraw.Draw(low.im)
    make_night_windows(low)
    low.save("harbor_evening.png")
    night_palette(props.im).save(OUT/"gear_evening.png",optimize=True)


if __name__=="__main__":
    main()
