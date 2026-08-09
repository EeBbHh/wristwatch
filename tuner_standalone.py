# Tuner — standalone
# Adafruit QT Py RP2040 (#4900) + custom PCB
# GC9A01A 1.28" 240x240 round LCD
# Button 1: A2 castellated pad → GND (cycle note when stopped)
# Button 2: SDA castellated pad → GND (strike / stop)
# Audio: magnetic transducer on A3 (via MMBT2222A)
#
# Controls:
#   BOOT — strike current note (plays 3s then auto-stops) / stop if playing
#   A2   — cycle note when stopped: E4 A4 D5 G5 B5 E6
#
# Tuning fork graphic flashes white on strike.
# Notes are guitar standard tuning +2 octaves for transducer clarity.
#
# Requires: adafruit_gc9a01a.mpy, adafruit_display_text/, adafruit_ticks.mpy,
#           adafruit_bus_device/ in /lib

import gc
gc.collect()
import board,busio,displayio,fourwire,adafruit_gc9a01a
import vectorio,terminalio,digitalio
import time
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import label
gc.collect()
displayio.release_displays()
gc.collect()
import pwmio
buzzer=pwmio.PWMOut(board.A3,variable_frequency=True)
buzzer.frequency=440
BUZZER_DUTY=32768
gc.collect()

CX=120;CY=120
COLOR_CYAN=0x00FFFF;COLOR_PINK_PURPLE=0xCC44AA;COLOR_WHITE=0xFFFFFF
BOTH_HOLD_S=0.3
TUNER_NOTES=(("E4",329.63),("A4",440.00),("D5",587.33),("G5",783.99),("B5",987.77),("E6",1318.51))
TUNER_ON_S=3.0
TUNER_FLASH_S=0.4

spi=busio.SPI(clock=board.SCK,MOSI=board.MOSI)
display_bus=fourwire.FourWire(spi,command=board.RX,chip_select=board.TX,reset=None,baudrate=24_000_000)
display=adafruit_gc9a01a.GC9A01A(display_bus,width=240,height=240,rotation=0,auto_refresh=False)

btn_a2=digitalio.DigitalInOut(board.A2)
btn_a2.direction=digitalio.Direction.INPUT
btn_a2.pull=digitalio.Pull.UP
btn_boot=digitalio.DigitalInOut(board.SDA)
btn_boot.direction=digitalio.Direction.INPUT
btn_boot.pull=digitalio.Pull.UP

p_black=displayio.Palette(1);p_black[0]=0x000000

def _build_tuner_group():
    global lbl_note,p_flash,p_fork
    g=displayio.Group()
    g.append(vectorio.Circle(pixel_shader=p_black,radius=120,x=CX,y=CY))
    tt=CY-40;bt=CY+16;bh=6;ht=bt+bh;hb=ht+26
    p_fork=displayio.Palette(1);p_fork[0]=COLOR_PINK_PURPLE
    g.append(vectorio.Rectangle(pixel_shader=p_fork,x=CX-8,y=tt,width=4,height=bt-tt))
    g.append(vectorio.Rectangle(pixel_shader=p_fork,x=CX+4,y=tt,width=4,height=bt-tt))
    g.append(vectorio.Rectangle(pixel_shader=p_fork,x=CX-8,y=bt,width=16,height=bh))
    g.append(vectorio.Rectangle(pixel_shader=p_fork,x=CX-3,y=ht,width=6,height=hb-ht))
    p_flash=displayio.Palette(1);p_flash[0]=0x000000
    g.append(vectorio.Rectangle(pixel_shader=p_flash,x=CX-26,y=CY-22,width=16,height=3))
    g.append(vectorio.Rectangle(pixel_shader=p_flash,x=CX-34,y=CY-9,width=22,height=3))
    g.append(vectorio.Rectangle(pixel_shader=p_flash,x=CX-26,y=CY+4,width=16,height=3))
    g.append(vectorio.Rectangle(pixel_shader=p_flash,x=CX+10,y=CY-22,width=16,height=3))
    g.append(vectorio.Rectangle(pixel_shader=p_flash,x=CX+12,y=CY-9,width=22,height=3))
    g.append(vectorio.Rectangle(pixel_shader=p_flash,x=CX+10,y=CY+4,width=16,height=3))
    lbl_note=Label(terminalio.FONT,text="E4  329Hz",color=COLOR_PINK_PURPLE,scale=2)
    lbl_note.anchor_point=(0.5,0.5);lbl_note.anchored_position=(CX,55);g.append(lbl_note)
    return g

tuner_group=_build_tuner_group();del _build_tuner_group;gc.collect()

lbl_mute=label.Label(terminalio.FONT,text="STRIKE",scale=1,color=COLOR_CYAN,
    anchor_point=(0.5,0.5),anchored_position=(CX,185))
tuner_group.append(lbl_mute);gc.collect()

def both_held():return(not btn_a2.value)and(not btn_boot.value)
def wait_release(btn):
    while not btn.value:time.sleep(0.05)

tuner_note_idx=0;tuner_playing=False;tuner_next_t=0.0;tuner_strike_t=0.0
btn_a2_prev=True;btn_boot_prev=True
display.root_group=tuner_group
display.refresh()

while True:
    now=time.monotonic()
    if tuner_playing and now>=tuner_next_t:
        buzzer.duty_cycle=0;tuner_playing=False
        lbl_mute.text="STRIKE";display.refresh()
    if tuner_strike_t>0.0 and now-tuner_strike_t>=TUNER_FLASH_S:
        p_flash[0]=0x000000;p_fork[0]=COLOR_PINK_PURPLE;tuner_strike_t=0.0;display.refresh()
    a2_now=btn_a2.value
    if btn_a2_prev and not a2_now:
        if not both_held() and not tuner_playing:
            while not btn_a2.value:
                if both_held():break
                time.sleep(0.02)
            else:
                tuner_note_idx=(tuner_note_idx+1)%len(TUNER_NOTES)
                name,freq=TUNER_NOTES[tuner_note_idx]
                lbl_note.text="{:s} {:4d}Hz".format(name,int(freq))
                display.refresh()
            a2_now=btn_a2.value
    btn_a2_prev=a2_now
    boot_now=btn_boot.value
    if btn_boot_prev and not boot_now:
        if not both_held():
            while not btn_boot.value:
                if both_held():break
                time.sleep(0.02)
            else:
                if tuner_playing:
                    buzzer.duty_cycle=0;tuner_playing=False
                    p_flash[0]=0x000000;p_fork[0]=COLOR_PINK_PURPLE;tuner_strike_t=0.0
                    lbl_mute.text="STRIKE"
                else:
                    name,freq=TUNER_NOTES[tuner_note_idx]
                    buzzer.frequency=int(freq);buzzer.duty_cycle=BUZZER_DUTY
                    tuner_playing=True;tuner_next_t=now+TUNER_ON_S
                    tuner_strike_t=now;p_flash[0]=0xFFFFFF;p_fork[0]=0xFFFFFF
                    lbl_mute.text="STOP";display.refresh()
                display.refresh()
            boot_now=btn_boot.value
    btn_boot_prev=boot_now
    time.sleep(0.02)
