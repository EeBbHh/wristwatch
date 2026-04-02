# Clock — standalone
# Adafruit QT Py RP2040 (#4900) + EYESPI BFF (#5772)
# GC9A01A 1.28" 240x240 round LCD (#6178)
# Buttons: any two momentary tactile switches wired to A2→GND and BOOT→GND
#
# Controls:
#   BOOT short — enter time-set
#   During time-set: A2 increments field, BOOT advances to next field
#
# Copy this file to code.py on your CIRCUITPY drive to run.
# Requires: adafruit_gc9a01a.mpy, adafruit_display_text/, adafruit_ticks.mpy,
#           adafruit_bus_device/ in /lib

import gc
gc.collect()
import board,busio,displayio,fourwire,vectorio,adafruit_gc9a01a
import bitmaptools,terminalio,digitalio,rtc
import time,math
from adafruit_display_text.bitmap_label import Label
gc.collect()
displayio.release_displays()
gc.collect()

# ── Bitmap first — must be allocated before display driver ────────
# Allocates the 57,600 byte shared bitmap before anything else
# claims contiguous RAM. Same requirement as code.py.
CX,CY=120,120
WIDTH,HEIGHT=240,240
CLK_BG=0;CLK_GREEN=1;CLK_RED=2
COLOR_CYAN=0x00FFFF;COLOR_RED=0xFF2200
LABEL_R=100;DOT_R=92

clock_palette=displayio.Palette(3)
clock_palette[CLK_BG]=0xFF00FF
clock_palette[CLK_GREEN]=0x00FF00
clock_palette[CLK_RED]=COLOR_RED
clock_palette.make_transparent(CLK_BG)
bitmap=displayio.Bitmap(WIDTH,HEIGHT,3)
bitmap.fill(CLK_BG)
gc.collect()

# ── Display ───────────────────────────────────────────────────────
spi=busio.SPI(clock=board.SCK,MOSI=board.MOSI)
display_bus=fourwire.FourWire(spi,command=board.RX,chip_select=board.TX,reset=None,baudrate=24_000_000)
display=adafruit_gc9a01a.GC9A01A(display_bus,width=240,height=240,rotation=0,auto_refresh=False)

# ── Buttons ───────────────────────────────────────────────────────
btn_a2=digitalio.DigitalInOut(board.A2)
btn_a2.direction=digitalio.Direction.INPUT
btn_a2.pull=digitalio.Pull.UP
btn_boot=digitalio.DigitalInOut(board.BUTTON)
btn_boot.direction=digitalio.Direction.INPUT
btn_boot.pull=digitalio.Pull.UP

# ── RTC ───────────────────────────────────────────────────────────
clock_rtc=rtc.RTC()
clock_rtc.datetime=time.struct_time((2025,1,1,12,0,0,0,-1,-1))

# ── Palettes ──────────────────────────────────────────────────────
# Bitmap colour slots:
#   0 = transparent (shows dial group behind it)
#   1 = green (hour and minute hands)
#   2 = red (second hand)
p_black=displayio.Palette(1);p_black[0]=0x000000
p_pink_purple=displayio.Palette(1);p_pink_purple[0]=0xCC44AA
p_red_pal=displayio.Palette(1);p_red_pal[0]=COLOR_RED

# ── Dial group ────────────────────────────────────────────────────
# Built once at boot: black background, minute dots, hour numbers,
# and set_label (shown only during time-set).
dial=displayio.Group()
dial.append(vectorio.Circle(pixel_shader=p_black,radius=120,x=CX,y=CY))
for _i in range(60):
    if _i%5==0:continue
    _a=math.radians(_i*6-90)
    dial.append(vectorio.Circle(pixel_shader=p_pink_purple,radius=1,
        x=int(CX+DOT_R*math.cos(_a)),y=int(CY+DOT_R*math.sin(_a))))
for _i in range(1,13):
    _a=math.radians(_i*30-90)
    _l=Label(terminalio.FONT,text=str(_i),color=COLOR_CYAN,scale=2)
    _l.anchor_point=(0.5,0.5)
    _l.anchored_position=(int(CX+LABEL_R*math.cos(_a)),int(CY+LABEL_R*math.sin(_a)))
    dial.append(_l)
set_label=Label(terminalio.FONT,text="",color=COLOR_CYAN,scale=1)
set_label.anchor_point=(0.5,0.5);set_label.anchored_position=(CX,175)
dial.append(set_label)
gc.collect()

# ── Hand drawing ──────────────────────────────────────────────────
def hand_coords(ang,length,tail):
    a=math.radians(ang-90);ca,sa=math.cos(a),math.sin(a)
    return(int(CX-tail*ca),int(CY-tail*sa),int(CX+length*ca),int(CY+length*sa))

def draw_hand(bmp,x0,y0,x1,y1,col,hw):
    dx,dy=x1-x0,y1-y0;ln=math.sqrt(dx*dx+dy*dy)
    if ln==0:return
    px,py=-dy/ln,dx/ln
    for d in range(-hw,hw+1):
        ox,oy=int(d*px),int(d*py)
        bitmaptools.draw_line(bmp,x0+ox,y0+oy,x1+ox,y1+oy,col)

def hour_angle(h,m):return(h%12)*30+m*0.5
def minute_angle(m,s):return m*6+s*0.1
def second_angle(s):return s*6

def redraw_hands(h,m,s):
    bitmap.fill(CLK_BG)
    draw_hand(bitmap,*hand_coords(hour_angle(h,m),58,12),CLK_GREEN,2)
    draw_hand(bitmap,*hand_coords(minute_angle(m,s),88,12),CLK_GREEN,1)
    draw_hand(bitmap,*hand_coords(second_angle(s),82,12),CLK_RED,0)

# ── Display group ─────────────────────────────────────────────────
clock_tilegrid=displayio.TileGrid(bitmap,pixel_shader=clock_palette)
clock_group=displayio.Group()
clock_group.append(dial)
clock_group.append(clock_tilegrid)
clock_group.append(vectorio.Circle(pixel_shader=p_red_pal,radius=5,x=CX,y=CY))
gc.collect()

# ── Helpers ───────────────────────────────────────────────────────
def wait_release(btn):
    while not btn.value:time.sleep(0.05)

FIELDS=("HOUR","MIN")

def run_time_set():
    t=time.localtime();edit=[t.tm_hour,t.tm_min]
    def rd():
        bitmap.fill(CLK_BG)
        draw_hand(bitmap,*hand_coords(hour_angle(edit[0],edit[1]),58,12),CLK_GREEN,2)
        draw_hand(bitmap,*hand_coords(minute_angle(edit[1],0),88,12),CLK_GREEN,1)
        display.refresh()
    def inc(f):
        if f==0:edit[0]=(edit[0]+1)%24
        elif f==1:edit[1]=(edit[1]+1)%60
    for f in range(len(FIELDS)):
        set_label.text=FIELDS[f];rd()
        while True:
            if not btn_boot.value:wait_release(btn_boot);break
            if not btn_a2.value:inc(f);rd();wait_release(btn_a2)
            time.sleep(0.05)
    set_label.text=""
    clock_rtc.datetime=time.struct_time((2025,1,1,edit[0],edit[1],0,0,-1,-1))

# ── Boot ──────────────────────────────────────────────────────────
t=time.localtime()
redraw_hands(t.tm_hour,t.tm_min,t.tm_sec)
display.root_group=clock_group
display.refresh()
last_sec=t.tm_sec

# ── Main loop ─────────────────────────────────────────────────────
while True:
    if not btn_boot.value:
        wait_release(btn_boot)
        run_time_set()
        t=time.localtime();redraw_hands(t.tm_hour,t.tm_min,t.tm_sec)
        last_sec=t.tm_sec;display.refresh()
        continue
    t=time.localtime()
    if t.tm_sec!=last_sec:
        redraw_hands(t.tm_hour,t.tm_min,t.tm_sec);last_sec=t.tm_sec;display.refresh()
    else:
        time.sleep(0.01)
