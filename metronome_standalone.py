# Metronome — standalone
# Adafruit QT Py RP2040 (#4900) + EYESPI BFF (#5772)
# GC9A01A 1.28" 240x240 round LCD (#6178)
# Buttons: any two momentary tactile switches wired to A2→GND and BOOT→GND
# Audio: passive buzzer on A3 (2 wires), vibration motor on A1 (transistor circuit)
#
# Controls:
#   A2 short  — BPM up (+10, max 200)
#   A2 long   — cycle time signature (4/4 → 3/4 → 4/4)
#   BOOT short — BPM down (-10, min 40)
#   BOOT long  — toggle SOUND / SILENT
#
# SOUND mode: buzzer tick/tock  |  SILENT mode: vibration motor pulse
# Remove audio hardware init below if not using buzzer or motor.
#
# Copy this file to code.py on your CIRCUITPY drive to run.
# Requires: adafruit_gc9a01a.mpy, adafruit_display_text/, adafruit_ticks.mpy,
#           adafruit_bus_device/ in /lib

import gc
gc.collect()
import board,busio,displayio,fourwire,adafruit_gc9a01a
import terminalio,digitalio
import time,math
from adafruit_display_text import label
gc.collect()
displayio.release_displays()
gc.collect()

# ── Constants ─────────────────────────────────────────────────────
CX,CY=120,120
WIDTH,HEIGHT=240,240
BPM_START=80;BPM_MIN=40;BPM_MAX=200;BPM_STEP=10
REFRESH_FLOOR=0.065
HOLD_S=0.5
COLOR_CYAN=0x00FFFF;COLOR_WHITE=0xFFFFFF
MAX_FADE=max(1,int((60.0/BPM_MIN)/REFRESH_FLOOR))
NUM_COLOURS=MAX_FADE+1

# ── Palette and bitmap — before display driver ────────────────────
# Allocate the large bitmap before the display driver init to ensure
# contiguous RAM is available. Same requirement as code.py.
metro_palette=displayio.Palette(NUM_COLOURS)
metro_palette[0]=0x000000
bitmap=displayio.Bitmap(WIDTH,HEIGHT,NUM_COLOURS)
bitmap.fill(0)
gc.collect()

# ── Audio hardware ────────────────────────────────────────────────
# Passive buzzer on A3: one leg to A3, other to GND. No resistor needed.
# Vibration motor on A1: requires 2N2222 transistor circuit (see project docs).
import pwmio
buzzer=pwmio.PWMOut(board.A3,variable_frequency=True)
buzzer.frequency=440
BUZZER_DUTY=32768

motor=digitalio.DigitalInOut(board.A1)
motor.direction=digitalio.Direction.OUTPUT
motor.value=False

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

# ── BPM colour gradient ───────────────────────────────────────────
# Note colour shifts from blue (slow) through green/amber to red (fast)
GRADIENT=(
    ( 40,(0x00,0x22,0xFF)),( 59,(0x00,0x99,0xFF)),
    ( 60,(0x00,0xCC,0xAA)),( 79,(0x00,0xFF,0x88)),
    ( 80,(0xFF,0xCC,0x00)),(119,(0xFF,0x77,0x00)),
    (120,(0xFF,0x44,0x00)),(159,(0xFF,0x00,0x44)),
    (160,(0xFF,0x00,0x99)),(200,(0xCC,0x00,0x00)))

RANGES=(
    ( 40, 59,"whole"),( 60, 79,"half"),
    ( 80,119,"quarter"),(120,159,"eighth"),(160,200,"double_eighth"))

def bpm_colour(bpm):
    bpm=max(BPM_MIN,min(BPM_MAX,bpm))
    if bpm<=GRADIENT[0][0]:r,g,b=GRADIENT[0][1];return(r<<16)|(g<<8)|b
    if bpm>=GRADIENT[-1][0]:r,g,b=GRADIENT[-1][1];return(r<<16)|(g<<8)|b
    for i in range(len(GRADIENT)-1):
        b0,c0=GRADIENT[i];b1,c1=GRADIENT[i+1]
        if b0<=bpm<=b1:
            t=(bpm-b0)/(b1-b0)
            r=int(c0[0]+t*(c1[0]-c0[0]));g=int(c0[1]+t*(c1[1]-c0[1]));b=int(c0[2]+t*(c1[2]-c0[2]))
            return(r<<16)|(g<<8)|b
    return 0xFFFFFF

def bpm_range(bpm):
    colour=bpm_colour(bpm)
    for lo,hi,name in RANGES:
        if lo<=bpm<=hi:return colour,name
    return colour,RANGES[-1][2]

def build_palette(colour,fade_steps):
    r=(colour>>16)&0xFF;g=(colour>>8)&0xFF;b=colour&0xFF
    for i in range(1,fade_steps+1):
        s=i/fade_steps
        metro_palette[i]=(int(r*s)<<16)|(int(g*s)<<8)|int(b*s)
    for i in range(fade_steps+1,MAX_FADE+1):metro_palette[i]=0x000000

# ── Labels ────────────────────────────────────────────────────────
lbl_bpm=label.Label(terminalio.FONT,text="BPM",scale=3,color=COLOR_WHITE,
    background_color=0x000000,anchor_point=(1.0,0.5),anchored_position=(CX-45,CY))
lbl_num=label.Label(terminalio.FONT,text="80",scale=3,color=COLOR_WHITE,
    background_color=0x000000,anchor_point=(0.0,0.5),anchored_position=(CX+45,CY))
lbl_timesig=label.Label(terminalio.FONT,text="4/4",scale=1,color=COLOR_CYAN,
    background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,50))
lbl_audio_mode=label.Label(terminalio.FONT,text="SOUND",scale=1,color=COLOR_CYAN,
    background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,185))
gc.collect()

# ── Note sprite builders ──────────────────────────────────────────
# Each sprite is a flat bytearray of (x,y) pixel pairs.
def filled_ellipse(cx,cy,rx,ry,ang):
    buf=bytearray();a=math.radians(ang);ca,sa=math.cos(a),math.sin(a);rx2,ry2=rx*rx,ry*ry
    for dy in range(-ry-2,ry+3):
        for dx in range(-rx-2,rx+3):
            xr=dx*ca+dy*sa;yr=-dx*sa+dy*ca
            if xr*xr*ry2+yr*yr*rx2<=rx2*ry2:
                px,py=cx+dx,cy+dy
                if 0<=px<WIDTH and 0<=py<HEIGHT:buf.append(px);buf.append(py)
    return buf

def outline_ellipse(cx,cy,rx,ry,ang,thickness=3):
    buf=bytearray();a=math.radians(ang);ca,sa=math.cos(a),math.sin(a);rx2,ry2=rx*rx,ry*ry
    irx,iry=max(1,rx-thickness),max(1,ry-thickness);irx2,iry2=irx*irx,iry*iry
    for dy in range(-ry-2,ry+3):
        for dx in range(-rx-2,rx+3):
            xr=dx*ca+dy*sa;yr=-dx*sa+dy*ca
            outer=xr*xr*ry2+yr*yr*rx2<=rx2*ry2;inner=xr*xr*iry2+yr*yr*irx2<=irx2*iry2
            if outer and not inner:
                px,py=cx+dx,cy+dy
                if 0<=px<WIDTH and 0<=py<HEIGHT:buf.append(px);buf.append(py)
    return buf

def thick_vline(x,y0,y1,w):
    buf=bytearray();half=w//2
    for y in range(min(y0,y1),max(y0,y1)+1):
        for dx in range(-half,half+1):
            px=x+dx
            if 0<=px<WIDTH and 0<=y<HEIGHT:buf.append(px);buf.append(y)
    return buf

def filled_rect(x,y,w,h):
    buf=bytearray()
    for dy in range(h):
        for dx in range(w):
            px,py=x+dx,y+dy
            if 0<=px<WIDTH and 0<=py<HEIGHT:buf.append(px);buf.append(py)
    return buf

def bezier_flag(x0,y0,steps=20,thickness=3):
    buf=bytearray();p0=(x0,y0);p1=(x0+22,y0+2);p2=(x0+24,y0+14);p3=(x0+14,y0+22);half=thickness//2
    for i in range(steps+1):
        t=i/steps;mt=1-t
        bx=int(mt**3*p0[0]+3*mt**2*t*p1[0]+3*mt*t**2*p2[0]+t**3*p3[0])
        by=int(mt**3*p0[1]+3*mt**2*t*p1[1]+3*mt*t**2*p2[1]+t**3*p3[1])
        for dy in range(-half,half+1):
            for dx in range(-half,half+1):
                if dx*dx+dy*dy<=half*half+1:
                    px,py=bx+dx,by+dy
                    if 0<=px<WIDTH and 0<=py<HEIGHT:buf.append(px);buf.append(py)
    return buf

def merge(*bufs):
    out=bytearray()
    for buf in bufs:out.extend(buf)
    return out

gc.collect();SPRITE={}
SPRITE["whole"]=outline_ellipse(CX,CY,20,14,-20,thickness=4);gc.collect()
head_h=outline_ellipse(CX-12,CY+15,14,10,-20,thickness=3);stem_h=thick_vline(CX,CY+8,CY-32,4)
SPRITE["half"]=merge(head_h,stem_h);del head_h,stem_h;gc.collect()
head_q=filled_ellipse(CX-12,CY+15,14,10,-20);stem_q=thick_vline(CX,CY+8,CY-32,4)
SPRITE["quarter"]=merge(head_q,stem_q);del head_q,stem_q;gc.collect()
head_e=filled_ellipse(CX-12,CY+15,14,10,-20);stem_e=thick_vline(CX,CY+8,CY-32,4);flag_e=bezier_flag(CX,CY-32,steps=24,thickness=3)
SPRITE["eighth"]=merge(head_e,stem_e,flag_e);del head_e,stem_e,flag_e;gc.collect()
head_e1=filled_ellipse(CX-22,CY+15,13,9,-20);stem_e1=thick_vline(CX-11,CY+7,CY-22,4)
head_e2=filled_ellipse(CX+12,CY+5,13,9,-20);stem_e2=thick_vline(CX+23,CY-3,CY-22,4);beam=filled_rect(CX-11,CY-26,35,7)
SPRITE["double_eighth"]=merge(head_e1,stem_e1,head_e2,stem_e2,beam);del head_e1,stem_e1,head_e2,stem_e2,beam;gc.collect()

def apply_bpm(bpm):
    colour,note=bpm_range(bpm);cycle=60.0/bpm
    fsteps=max(1,int(cycle/REFRESH_FLOOR))
    build_palette(colour,fsteps)
    lbl_num.text=str(bpm);lbl_num.color=colour;lbl_bpm.color=colour
    return cycle,fsteps,SPRITE[note]

def apply_sprite(buf,colour_idx):
    for i in range(0,len(buf),2):bitmap[buf[i],buf[i+1]]=colour_idx

# ── Audio helpers ─────────────────────────────────────────────────
def vibrate(ms):
    motor.value=True;time.sleep(ms/1000);motor.value=False

def tone(freq,ms):
    buzzer.frequency=freq;buzzer.duty_cycle=BUZZER_DUTY
    time.sleep(ms/1000);buzzer.duty_cycle=0

# ── Display group ─────────────────────────────────────────────────
tilegrid=displayio.TileGrid(bitmap,pixel_shader=metro_palette)
group=displayio.Group()
group.append(tilegrid)
group.append(lbl_bpm);group.append(lbl_num)
group.append(lbl_timesig);group.append(lbl_audio_mode)

# ── Time signatures ───────────────────────────────────────────────
TIME_SIGS=("4/4","3/4");TIME_SIG_BEATS=(4,3)
metro_ts_idx=0;metro_beat_pos=0;metro_silent=False

def wait_release(btn):
    while not btn.value:time.sleep(0.05)

# ── Boot ──────────────────────────────────────────────────────────
BPM=BPM_START
cycle_s,FADE_STEPS,SPR=apply_bpm(BPM)
beat_start=time.monotonic()+0.15
last_beat_t=beat_start;beat_count=0;step=FADE_STEPS
btn_a2_prev=True;btn_boot_prev=True
display.root_group=group
display.refresh()

# ── Main loop ─────────────────────────────────────────────────────
while True:
    # A2 — BPM up (short) or time signature change (long)
    a2_now=btn_a2.value
    if btn_a2_prev and not a2_now:
        a2_press_t=time.monotonic()
        while not btn_a2.value:
            if time.monotonic()-a2_press_t>=HOLD_S*2:
                metro_ts_idx=(metro_ts_idx+1)%len(TIME_SIGS)
                lbl_timesig.text=TIME_SIGS[metro_ts_idx];metro_beat_pos=0
                step=FADE_STEPS
                wait_release(btn_a2);a2_now=btn_a2.value
                beat_start=time.monotonic()+0.15;break
            time.sleep(0.02)
        else:
            if BPM<BPM_MAX:
                old_spr=SPR;BPM=min(BPM_MAX,BPM+BPM_STEP)
                cycle_s,FADE_STEPS,SPR=apply_bpm(BPM);apply_sprite(old_spr,0)
                beat_start=time.monotonic()+0.15;step=FADE_STEPS;gc.collect()
    btn_a2_prev=a2_now

    # BOOT — BPM down (short) or sound/silent toggle (long)
    boot_now=btn_boot.value
    if btn_boot_prev and not boot_now:
        boot_press_t=time.monotonic()
        while not btn_boot.value:
            if time.monotonic()-boot_press_t>=HOLD_S*2:
                metro_silent=not metro_silent
                lbl_audio_mode.text="SILENT" if metro_silent else "SOUND"
                wait_release(btn_boot);boot_now=btn_boot.value
                beat_start=time.monotonic()+0.15;step=FADE_STEPS;break
            time.sleep(0.02)
        else:
            if BPM>BPM_MIN:
                old_spr=SPR;BPM=max(BPM_MIN,BPM-BPM_STEP)
                cycle_s,FADE_STEPS,SPR=apply_bpm(BPM);apply_sprite(old_spr,0)
                beat_start=time.monotonic()+0.15;step=FADE_STEPS;gc.collect()
    btn_boot_prev=boot_now

    # Draw frame and sleep until next frame target
    apply_sprite(SPR,step);display.refresh()
    step_num=FADE_STEPS-step
    target_time=beat_start+(step_num+1)/(FADE_STEPS+1)*cycle_s
    remainder=target_time-time.monotonic()
    if remainder>0:time.sleep(remainder)
    step-=1

    # Beat rollover
    if step<0:
        step=FADE_STEPS;beat_start+=cycle_s;beat_count+=1
        is_downbeat=(metro_beat_pos==0)
        if not metro_silent:
            tone(880 if is_downbeat else 660,60)
        else:
            vibrate(80 if is_downbeat else 50)
        metro_beat_pos=(metro_beat_pos+1)%TIME_SIG_BEATS[metro_ts_idx]
        now=time.monotonic();actual_interval=now-last_beat_t;last_beat_t=now
        if beat_count%8==0:gc.collect()
