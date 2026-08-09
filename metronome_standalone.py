# Metronome — standalone
# Adafruit QT Py RP2040 (#4900) + custom PCB
# GC9A01A 1.28" 240x240 round LCD
# Button 1: A2 castellated pad → GND
# Button 2: SDA castellated pad → GND
# Audio: magnetic transducer on A3 (via MMBT2222A), vibration motor on A1 (via MMBT2222A)
#
# Controls:
#   A2 short  — BPM up (+5, max 250)
#   A2 long   — cycle time signature (4/4 → 3/4)
#   BOOT short — BPM down (-5, min 40)
#   BOOT long  — toggle SOUND / SILENT
#   Both held  — advance mode (no-op in standalone)
#
# Requires: adafruit_gc9a01a.mpy, adafruit_display_text/, adafruit_ticks.mpy,
#           adafruit_bus_device/ in /lib
# Also copy sprites.py to CIRCUITPY root

import gc
gc.collect()
import board,busio,displayio,fourwire,adafruit_gc9a01a
import terminalio,digitalio,vectorio
import time,math
from adafruit_display_text import label
gc.collect()
displayio.release_displays()
gc.collect()

CX=120;CY=120
WIDTH=240;HEIGHT=240
BPM_START=80;BPM_MIN=40;BPM_MAX=250;BPM_STEP=5
REFRESH_FLOOR=0.065
BOTH_HOLD_S=0.3;LONG_PRESS_S=0.8
COLOR_CYAN=0x00FFFF;COLOR_WHITE=0xFFFFFF
MAX_FADE=max(1,int((60.0/BPM_MIN)/REFRESH_FLOOR))
NUM_COLOURS=MAX_FADE+1

metro_palette=displayio.Palette(NUM_COLOURS)
metro_palette[0]=0x000000
shared_bitmap=displayio.Bitmap(WIDTH,HEIGHT,NUM_COLOURS)
shared_bitmap.fill(0)
gc.collect()

import pwmio
buzzer=pwmio.PWMOut(board.A3,variable_frequency=True)
buzzer.frequency=440
BUZZER_DUTY=32768
motor=pwmio.PWMOut(board.A1,frequency=1000,duty_cycle=0)
MOTOR_STRENGTH=49151

spi=busio.SPI(clock=board.SCK,MOSI=board.MOSI)
display_bus=fourwire.FourWire(spi,command=board.RX,chip_select=board.TX,reset=None,baudrate=24_000_000)
display=adafruit_gc9a01a.GC9A01A(display_bus,width=240,height=240,rotation=0,auto_refresh=False)

btn_a2=digitalio.DigitalInOut(board.A2)
btn_a2.direction=digitalio.Direction.INPUT
btn_a2.pull=digitalio.Pull.UP
btn_boot=digitalio.DigitalInOut(board.SDA)
btn_boot.direction=digitalio.Direction.INPUT
btn_boot.pull=digitalio.Pull.UP

GRADIENT=(
    ( 40,(0x00,0x22,0xFF)),( 59,(0x00,0x99,0xFF)),
    ( 60,(0x00,0xCC,0xAA)),( 79,(0x00,0xFF,0x88)),
    ( 80,(0xFF,0xCC,0x00)),(119,(0xFF,0x77,0x00)),
    (120,(0xFF,0x44,0x00)),(159,(0xFF,0x00,0x44)),
    (160,(0xFF,0x00,0x99)),(199,(0xCC,0x00,0x00)),
    (200,(0xAA,0x00,0x00)),(250,(0x66,0x00,0x00)))
RANGES=(( 40, 59,"whole"),( 60, 79,"half"),( 80,119,"quarter"),
        (120,159,"eighth"),(160,199,"double_eighth"),(200,250,"sixteenth"))

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

lbl_bpm=label.Label(terminalio.FONT,text="BPM",scale=3,color=COLOR_WHITE,
    background_color=0x000000,anchor_point=(1.0,0.5),anchored_position=(CX-45,CY))
lbl_num=label.Label(terminalio.FONT,text="80",scale=3,color=COLOR_WHITE,
    background_color=0x000000,anchor_point=(0.0,0.5),anchored_position=(CX+45,CY))
lbl_timesig=label.Label(terminalio.FONT,text="4/4",scale=1,color=COLOR_CYAN,
    background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,50))
lbl_audio_mode=label.Label(terminalio.FONT,text="SOUND",scale=1,color=COLOR_CYAN,
    background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,185))
gc.collect()

import sprites as _spr;gc.collect()
SPRITE=_spr.build_sprites();del _spr;gc.collect()

def apply_bpm(bpm):
    colour,note=bpm_range(bpm);cycle=60.0/bpm;fsteps=max(1,int(cycle/REFRESH_FLOOR))
    build_palette(colour,fsteps)
    lbl_num.text=str(bpm);lbl_num.color=colour;lbl_bpm.color=colour
    return cycle,fsteps,SPRITE[note]

def apply_sprite(buf,colour_idx):
    for i in range(0,len(buf),2):shared_bitmap[buf[i],buf[i+1]]=colour_idx

def vibrate(ms):
    motor.duty_cycle=MOTOR_STRENGTH;time.sleep(ms/1000);motor.duty_cycle=0
def tone(freq,ms):
    buzzer.frequency=freq;buzzer.duty_cycle=BUZZER_DUTY
    time.sleep(ms/1000);buzzer.duty_cycle=0

tilegrid=displayio.TileGrid(shared_bitmap,pixel_shader=metro_palette)
group=displayio.Group()
group.append(tilegrid)
group.append(lbl_bpm);group.append(lbl_num)
group.append(lbl_timesig);group.append(lbl_audio_mode)

TIME_SIGS=("4/4","3/4");TIME_SIG_BEATS=(4,3)
metro_ts_idx=0;metro_beat_pos=0;metro_silent=False

def both_held():return(not btn_a2.value)and(not btn_boot.value)
def wait_release(btn):
    while not btn.value:time.sleep(0.05)

BPM=BPM_START
cycle_s,FADE_STEPS,SPR=apply_bpm(BPM)
beat_start=time.monotonic()+0.15
last_beat_t=beat_start;beat_count=0;step=FADE_STEPS
btn_a2_prev=True;btn_boot_prev=True
display.root_group=group
display.refresh()

while True:
    a2_now=btn_a2.value
    if btn_a2_prev and not a2_now:
        a2_press_t=time.monotonic()
        while not btn_a2.value:
            if both_held():break
            if time.monotonic()-a2_press_t>=LONG_PRESS_S:
                metro_ts_idx=(metro_ts_idx+1)%len(TIME_SIGS)
                lbl_timesig.text=TIME_SIGS[metro_ts_idx];metro_beat_pos=0
                step=FADE_STEPS;wait_release(btn_a2);a2_now=btn_a2.value
                beat_start=time.monotonic()+0.15;break
            time.sleep(0.02)
        else:
            if BPM<BPM_MAX:
                old_spr=SPR;BPM=min(BPM_MAX,BPM+BPM_STEP)
                cycle_s,FADE_STEPS,SPR=apply_bpm(BPM);apply_sprite(old_spr,0)
                beat_start=time.monotonic()+0.15;step=FADE_STEPS;gc.collect()
    btn_a2_prev=a2_now
    boot_now=btn_boot.value
    if btn_boot_prev and not boot_now:
        boot_press_t=time.monotonic()
        while not btn_boot.value:
            if both_held():break
            if time.monotonic()-boot_press_t>=LONG_PRESS_S:
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
    apply_sprite(SPR,step);display.refresh()
    step_num=FADE_STEPS-step
    target_time=beat_start+(step_num+1)/(FADE_STEPS+1)*cycle_s
    remainder=target_time-time.monotonic()
    if remainder>0:time.sleep(remainder)
    step-=1
    if step<0:
        step=FADE_STEPS;beat_start+=cycle_s;beat_count+=1
        is_downbeat=(metro_beat_pos==0)
        if not metro_silent:
            tone(880 if is_downbeat else 660,60)
        else:
            vibrate(80 if is_downbeat else 50)
        metro_beat_pos=(metro_beat_pos+1)%TIME_SIG_BEATS[metro_ts_idx]
        now=time.monotonic();last_beat_t=now
        if beat_count%8==0:gc.collect()
