# Tuner — standalone
# Adafruit QT Py RP2040 (#4900) + EYESPI BFF (#5772)
# GC9A01A 1.28" 240x240 round LCD (#6178)
# Passive buzzer on A3 (2 wires to A3 and GND, no resistor)
# Buttons: any two momentary tactile switches wired to A2→GND and BOOT→GND
#
# Controls:
#   BOOT — toggle LIVE / MUTE
#
# LIVE: buzzer plays A4 440 Hz (4s on, 2s off, repeating)
# MUTE: buzzer silent, display shows MUTE
#
# Copy this file to code.py on your CIRCUITPY drive to run.
# Requires: adafruit_gc9a01a.mpy, adafruit_display_text/, adafruit_ticks.mpy,
#           adafruit_bus_device/ in /lib

import gc
gc.collect()
import board,busio,displayio,fourwire,vectorio,adafruit_gc9a01a
import terminalio,digitalio
import time
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import label
gc.collect()
displayio.release_displays()
gc.collect()

# ── Constants ─────────────────────────────────────────────────────
CX,CY=120,120
COLOR_CYAN=0x00FFFF
COLOR_PINK_PURPLE=0xCC44AA
TUNER_FREQ=440
TUNER_ON_S=4.0   # tone on duration (seconds)
TUNER_OFF_S=2.0  # silence between pulses (seconds)

# ── Buzzer — before display driver ────────────────────────────────
# pwmio must be imported and buzzer initialised before the display
# driver. The GC9A01A init resets the LITE line so backlight PWM
# must also precede display init — same principle applies here.
import pwmio
buzzer=pwmio.PWMOut(board.A3,variable_frequency=True)
buzzer.frequency=TUNER_FREQ
BUZZER_DUTY=32768

# ── Display ───────────────────────────────────────────────────────
spi=busio.SPI(clock=board.SCK,MOSI=board.MOSI)
display_bus=fourwire.FourWire(spi,command=board.RX,chip_select=board.TX,reset=None,baudrate=24_000_000)
display=adafruit_gc9a01a.GC9A01A(display_bus,width=240,height=240,rotation=0,auto_refresh=False)

# ── Buttons ───────────────────────────────────────────────────────
btn_boot=digitalio.DigitalInOut(board.BUTTON)
btn_boot.direction=digitalio.Direction.INPUT
btn_boot.pull=digitalio.Pull.UP

# ── Palettes ──────────────────────────────────────────────────────
p_black=displayio.Palette(1);p_black[0]=0x000000
p_cyan=displayio.Palette(1);p_cyan[0]=COLOR_CYAN

# ── Tuner group ───────────────────────────────────────────────────
# Built once: black background, tuning fork (vectorio rectangles),
# A440 label, and LIVE/MUTE status label.
#
# Fork geometry:
#   tt = tine tops, bt = base top, bh = base height
#   ht = handle top, hb = handle bottom
def _build_tuner_group():
    g=displayio.Group()
    g.append(vectorio.Circle(pixel_shader=p_black,radius=120,x=CX,y=CY))
    tt=CY-40;bt=CY+16;bh=6;ht=bt+bh;hb=ht+26
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX-8,y=tt,width=4,height=bt-tt))
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX+4,y=tt,width=4,height=bt-tt))
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX-8,y=bt,width=16,height=bh))
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX-3,y=ht,width=6,height=hb-ht))
    lbl=Label(terminalio.FONT,text="A4 440 Hz",color=COLOR_PINK_PURPLE,scale=2)
    lbl.anchor_point=(0.5,0.5);lbl.anchored_position=(CX,55);g.append(lbl)
    return g

tuner_group=_build_tuner_group();del _build_tuner_group;gc.collect()

lbl_mute=label.Label(terminalio.FONT,text="LIVE",scale=1,color=COLOR_CYAN,
    anchor_point=(0.5,0.5),anchored_position=(CX,185))
tuner_group.append(lbl_mute);gc.collect()

# ── Helper ────────────────────────────────────────────────────────
def wait_release(btn):
    while not btn.value:time.sleep(0.05)

# ── Boot ──────────────────────────────────────────────────────────
tuner_muted=False
tuner_tone_on=False
tuner_next_t=0.0
display.root_group=tuner_group
display.refresh()
btn_boot_prev=True

# ── Main loop ─────────────────────────────────────────────────────
while True:
    now=time.monotonic()

    # Non-blocking tone state machine
    if not tuner_muted:
        if now>=tuner_next_t:
            if tuner_tone_on:
                buzzer.duty_cycle=0;tuner_tone_on=False
                tuner_next_t=now+TUNER_OFF_S
            else:
                buzzer.frequency=TUNER_FREQ;buzzer.duty_cycle=BUZZER_DUTY
                tuner_tone_on=True;tuner_next_t=now+TUNER_ON_S
    else:
        if tuner_tone_on:
            buzzer.duty_cycle=0;tuner_tone_on=False

    # BOOT — toggle LIVE/MUTE
    boot_now=btn_boot.value
    if btn_boot_prev and not boot_now:
        wait_release(btn_boot)
        boot_now=btn_boot.value
        tuner_muted=not tuner_muted
        lbl_mute.text="MUTE" if tuner_muted else "LIVE"
        display.refresh()
        if not tuner_muted:
            buzzer.frequency=TUNER_FREQ;buzzer.duty_cycle=BUZZER_DUTY
            tuner_tone_on=True;tuner_next_t=time.monotonic()+TUNER_ON_S
        else:
            buzzer.duty_cycle=0;tuner_tone_on=False
    btn_boot_prev=boot_now
    time.sleep(0.02)
