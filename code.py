# Clock+Metro+Tuner | QT Py RP2040 (#4900) EYESPI BFF (#5772)
# GC9A01A 240x240 LCD (#6178) Charger BFF (#5397) 400mAh LiPo (#3898)
# Both held 0.5s: Clock->Metro->Tuner->Clock
# Clock: BOOT=enter/next field  A2=increment
# Metro: A2 short=BPM+  A2 long=timesig  BOOT short=BPM-  BOOT long=sound/silent
# Tuner: BOOT=toggle LIVE/MUTE  (A440 reference pitch)
import gc
gc.collect()
import board,busio,displayio,fourwire,adafruit_gc9a01a
import vectorio,bitmaptools,terminalio,digitalio,rtc
import time,math
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import label
gc.collect()
displayio.release_displays()
gc.collect()
shared_bitmap=displayio.Bitmap(240,240,max(1,int((60.0/40)/0.065)+1))
shared_bitmap.fill(0)
import pwmio
backlight=pwmio.PWMOut(board.A0,frequency=1000,duty_cycle=65535)
spi=busio.SPI(clock=board.SCK,MOSI=board.MOSI)
display_bus=fourwire.FourWire(spi,command=board.RX,chip_select=board.TX,reset=None,baudrate=24_000_000)
display=adafruit_gc9a01a.GC9A01A(display_bus,width=240,height=240,rotation=0,auto_refresh=False)
btn_a2=digitalio.DigitalInOut(board.A2)
btn_a2.direction=digitalio.Direction.INPUT
btn_a2.pull=digitalio.Pull.UP
btn_boot=digitalio.DigitalInOut(board.BUTTON)
btn_boot.direction=digitalio.Direction.INPUT
btn_boot.pull=digitalio.Pull.UP
motor=pwmio.PWMOut(board.A1,frequency=1000,duty_cycle=0)
MOTOR_STRENGTH=49151  # 75% — adjust 0-65535 to set vibration strength
buzzer=pwmio.PWMOut(board.A3,variable_frequency=True)
buzzer.frequency=440
BUZZER_DUTY=32768
BOTH_HOLD_S=0.5
CX,CY=120,120
clock_rtc=rtc.RTC()
clock_rtc.datetime=time.struct_time((2025,1,1,12,0,0,0,-1,-1))
BPM_START=80;BPM_MIN=40;BPM_MAX=200;BPM_STEP=10
REFRESH_FLOOR=0.065
MAX_FADE=max(1,int((60.0/BPM_MIN)/REFRESH_FLOOR))
RANGES=(( 40, 59,"whole"),( 60, 79,"half"),( 80,119,"quarter"),(120,159,"eighth"),(160,200,"double_eighth"))
GRADIENT=(( 40,(0x00,0x22,0xFF)),( 59,(0x00,0x99,0xFF)),( 60,(0x00,0xCC,0xAA)),( 79,(0x00,0xFF,0x88)),( 80,(0xFF,0xCC,0x00)),(119,(0xFF,0x77,0x00)),(120,(0xFF,0x44,0x00)),(159,(0xFF,0x00,0x44)),(160,(0xFF,0x00,0x99)),(200,(0xCC,0x00,0x00)))
NUM_COLOURS=MAX_FADE+1
CLK_BG=0;CLK_GREEN=1;CLK_RED=2
COLOR_RED=0xFF2200
COLOR_CYAN=0x00FFFF;COLOR_WHITE=0xFFFFFF;COLOR_PINK_PURPLE=0xCC44AA
clock_palette=displayio.Palette(NUM_COLOURS)
clock_palette[CLK_BG]=0xFF00FF
clock_palette[CLK_GREEN]=0x00FF00
clock_palette[CLK_RED]=COLOR_RED
clock_palette.make_transparent(CLK_BG)
for _i in range(3,NUM_COLOURS):clock_palette[_i]=0x000000
metro_palette=displayio.Palette(NUM_COLOURS)
metro_palette[0]=0x000000
clock_tilegrid=displayio.TileGrid(shared_bitmap,pixel_shader=clock_palette)
metro_tilegrid=displayio.TileGrid(shared_bitmap,pixel_shader=metro_palette)
gc.collect()
BL_FULL=65535;BL_DIM=32768
DIM_AFTER_S=3600;BATT_CHECK_S=60;CHARGE_FLASH_S=1.0
CHARGE_V=4.3
BAT_GREEN=0x00CC44;BAT_YELLOW=0xCCAA00;BAT_RED=0xFF2200
LABEL_R=100;DOT_R=92
p_black=displayio.Palette(1);p_black[0]=0x000000
p_pink_purple=displayio.Palette(1);p_pink_purple[0]=COLOR_PINK_PURPLE
p_red_pal=displayio.Palette(1);p_red_pal[0]=COLOR_RED
dial=displayio.Group()
dial.append(vectorio.Circle(pixel_shader=p_black,radius=120,x=CX,y=CY))
for _i in range(60):
    if _i%5==0:continue
    _a=math.radians(_i*6-90)
    dial.append(vectorio.Circle(pixel_shader=p_pink_purple,radius=1,x=int(CX+DOT_R*math.cos(_a)),y=int(CY+DOT_R*math.sin(_a))))
for _i in range(1,13):
    _a=math.radians(_i*30-90)
    _l=Label(terminalio.FONT,text=str(_i),color=COLOR_CYAN,scale=2)
    _l.anchor_point=(0.5,0.5);_l.anchored_position=(int(CX+LABEL_R*math.cos(_a)),int(CY+LABEL_R*math.sin(_a)))
    dial.append(_l)
set_label=Label(terminalio.FONT,text="",color=COLOR_CYAN,scale=1)
set_label.anchor_point=(0.5,0.5);set_label.anchored_position=(CX,175)
dial.append(set_label)
gc.collect()
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
    shared_bitmap.fill(CLK_BG)
    draw_hand(shared_bitmap,*hand_coords(hour_angle(h,m),58,12),CLK_GREEN,2)
    draw_hand(shared_bitmap,*hand_coords(minute_angle(m,s),88,12),CLK_GREEN,1)
    draw_hand(shared_bitmap,*hand_coords(second_angle(s),82,12),CLK_RED,0)
clock_group=displayio.Group()
clock_group.append(dial)
clock_group.append(clock_tilegrid)
clock_group.append(vectorio.Circle(pixel_shader=p_red_pal,radius=5,x=CX,y=CY))
gc.collect()
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
def build_metro_palette(colour,fade_steps):
    r=(colour>>16)&0xFF;g=(colour>>8)&0xFF;b=colour&0xFF
    for i in range(1,fade_steps+1):
        s=i/fade_steps
        metro_palette[i]=(int(r*s)<<16)|(int(g*s)<<8)|int(b*s)
    for i in range(fade_steps+1,MAX_FADE+1):metro_palette[i]=0x000000
lbl_bpm=label.Label(terminalio.FONT,text="BPM",scale=3,color=COLOR_WHITE,background_color=0x000000,anchor_point=(1.0,0.5),anchored_position=(CX-45,CY))
lbl_num=label.Label(terminalio.FONT,text="80",scale=3,color=COLOR_WHITE,background_color=0x000000,anchor_point=(0.0,0.5),anchored_position=(CX+45,CY))
gc.collect()
import sprites as _spr;gc.collect()
SPRITE=_spr.build_sprites();del _spr;gc.collect()
def apply_bpm(bpm):
    colour,note=bpm_range(bpm);cycle=60.0/bpm;fsteps=max(1,int(cycle/REFRESH_FLOOR))
    build_metro_palette(colour,fsteps)
    lbl_num.text=str(bpm);lbl_num.color=colour;lbl_bpm.color=colour
    return cycle,fsteps,SPRITE[note]
def apply_sprite(buf,colour_idx):
    for i in range(0,len(buf),2):shared_bitmap[buf[i],buf[i+1]]=colour_idx
metro_group=displayio.Group()
metro_group.append(metro_tilegrid);metro_group.append(lbl_bpm);metro_group.append(lbl_num)
metro_silent=False
lbl_audio_mode=label.Label(terminalio.FONT,text="SOUND",scale=1,color=COLOR_CYAN,background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,185))
metro_group.append(lbl_audio_mode)
TIME_SIGS=("4/4","3/4");TIME_SIG_BEATS=(4,3)
metro_ts_idx=0;metro_beat_pos=0
lbl_timesig=label.Label(terminalio.FONT,text="4/4",scale=1,color=COLOR_CYAN,background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,50))
metro_group.append(lbl_timesig)
gc.collect()
p_cyan=displayio.Palette(1);p_cyan[0]=COLOR_CYAN
def _build_tuner_group():
    g=displayio.Group()
    g.append(vectorio.Circle(pixel_shader=p_black,radius=120,x=CX,y=CY))
    tt=CY-40;bt=CY+16;bh=6;ht=bt+bh;hb=ht+26
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX-8,y=tt,width=4,height=bt-tt))
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX+4,y=tt,width=4,height=bt-tt))
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX-8,y=bt,width=16,height=bh))
    g.append(vectorio.Rectangle(pixel_shader=p_cyan,x=CX-3,y=ht,width=6,height=hb-ht))
    global lbl_note
    lbl_note=Label(terminalio.FONT,text="A4 440 Hz",color=COLOR_PINK_PURPLE,scale=2)
    lbl_note.anchor_point=(0.5,0.5);lbl_note.anchored_position=(CX,55);g.append(lbl_note)
    return g
tuner_group=_build_tuner_group();del _build_tuner_group;gc.collect()
tuner_muted=False
TUNER_FREQ=440
TUNER_ON_S=4.0   # tone on duration
TUNER_OFF_S=2.0  # silence between pulses
tuner_tone_on=False;tuner_next_t=0.0
display_dimmed=False
bat_charging=False;bat_percent=100
last_batt_check=0.0;last_flash_t=0.0;flash_state=True
lbl_tuner_mute=label.Label(terminalio.FONT,text="LIVE",scale=1,color=COLOR_CYAN,anchor_point=(0.5,0.5),anchored_position=(CX,185))
tuner_group.append(lbl_tuner_mute);gc.collect()
lbl_bat_clock=label.Label(terminalio.FONT,text="BAT",scale=1,color=BAT_GREEN,background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,197))
lbl_bat_metro=label.Label(terminalio.FONT,text="BAT",scale=1,color=BAT_GREEN,background_color=0x000000,anchor_point=(0.5,0.5),anchored_position=(CX,205))
lbl_bat_tuner=label.Label(terminalio.FONT,text="BAT",scale=1,color=BAT_GREEN,anchor_point=(0.5,0.5),anchored_position=(CX,200))
clock_group.append(lbl_bat_clock)
metro_group.append(lbl_bat_metro)
tuner_group.append(lbl_bat_tuner)
gc.collect()
def both_held():return(not btn_a2.value)and(not btn_boot.value)
def wait_release_both():
    while(not btn_a2.value)or(not btn_boot.value):time.sleep(0.02)
def check_mode_switch():
    t=time.monotonic()
    while both_held():
        if time.monotonic()-t>=BOTH_HOLD_S:wait_release_both();return True
        time.sleep(0.02)
    return False
def wait_release(btn):
    while not btn.value:time.sleep(0.05)
def vibrate(ms):
    motor.duty_cycle=MOTOR_STRENGTH;time.sleep(ms/1000);motor.duty_cycle=0
def tone(freq,ms):
    buzzer.frequency=freq;buzzer.duty_cycle=BUZZER_DUTY
    time.sleep(ms/1000);buzzer.duty_cycle=0
def set_backlight(duty):backlight.duty_cycle=duty
def register_interaction():
    global last_interaction,display_dimmed
    last_interaction=time.monotonic()
    if display_dimmed:set_backlight(BL_FULL);display_dimmed=False
def is_waking():return display_dimmed
def check_dim_timeout():
    global display_dimmed
    if not display_dimmed and time.monotonic()-last_interaction>=DIM_AFTER_S:
        set_backlight(BL_DIM);display_dimmed=True
def read_battery():
    global btn_a2
    import analogio
    btn_a2.deinit()
    adc=analogio.AnalogIn(board.A2);raw=adc.value;adc.deinit()
    btn_a2=digitalio.DigitalInOut(board.A2)
    btn_a2.direction=digitalio.Direction.INPUT;btn_a2.pull=digitalio.Pull.UP
    return(raw/65535)*3.3*2.0
def bat_colour(pct):
    if pct>=50:return BAT_GREEN
    if pct>=25:return BAT_YELLOW
    return BAT_RED
def update_bat_labels():
    global last_flash_t,flash_state
    now=time.monotonic();c=bat_colour(bat_percent)
    if bat_charging:
        if now-last_flash_t>=CHARGE_FLASH_S:flash_state=not flash_state;last_flash_t=now
        c=c if flash_state else 0x000000
    lbl_bat_clock.color=c;lbl_bat_metro.color=c;lbl_bat_tuner.color=c
MODE_CLOCK=0;MODE_METRO=1;MODE_TUNER=2;NUM_MODES=3
mode=MODE_CLOCK
def enter_clock():
    global tuner_tone_on;buzzer.duty_cycle=0;tuner_tone_on=False
    t=time.localtime();redraw_hands(t.tm_hour,t.tm_min,t.tm_sec)
    display.root_group=clock_group;display.refresh()
def enter_metro():
    global tuner_tone_on;buzzer.duty_cycle=0;tuner_tone_on=False
    shared_bitmap.fill(0);display.root_group=metro_group;display.refresh()
def enter_tuner():
    display.root_group=tuner_group;display.refresh()
def advance_mode():
    global mode,beat_start,last_beat_t,beat_count,step,btn_a2_prev,btn_boot_prev,metro_beat_pos
    mode=(mode+1)%NUM_MODES
    if mode==MODE_CLOCK:
        global last_sec;last_sec=-1;enter_clock()
    elif mode==MODE_METRO:
        beat_start=time.monotonic()+0.15;last_beat_t=beat_start
        beat_count=0;step=FADE_STEPS;metro_beat_pos=0
        btn_a2_prev=True;btn_boot_prev=True;enter_metro()
    elif mode==MODE_TUNER:
        btn_a2_prev=True;btn_boot_prev=True;enter_tuner()
FIELDS=("HOUR","MIN")
def run_time_set():
    t=time.localtime();edit=[t.tm_hour,t.tm_min]
    def rd():
        shared_bitmap.fill(CLK_BG)
        draw_hand(shared_bitmap,*hand_coords(hour_angle(edit[0],edit[1]),58,12),CLK_GREEN,2)
        draw_hand(shared_bitmap,*hand_coords(minute_angle(edit[1],0),88,12),CLK_GREEN,1)
        display.refresh()
    def inc(f):
        if f==0:edit[0]=(edit[0]+1)%24
        elif f==1:edit[1]=(edit[1]+1)%60
    for f in range(len(FIELDS)):
        set_label.text=FIELDS[f];rd()
        while True:
            if both_held():set_label.text="";return False
            if not btn_boot.value:wait_release(btn_boot);break
            if not btn_a2.value:inc(f);rd();wait_release(btn_a2)
            time.sleep(0.05)
    set_label.text=""
    clock_rtc.datetime=time.struct_time((2025,1,1,edit[0],edit[1],0,0,-1,-1))
    return True
enter_clock()
last_sec=time.localtime().tm_sec
BPM=BPM_START
cycle_s,FADE_STEPS,SPR=apply_bpm(BPM)
beat_start=time.monotonic()+0.15;beat_count=0;last_beat_t=beat_start;step=FADE_STEPS
btn_a2_prev=True;btn_boot_prev=True
last_interaction=time.monotonic()
while True:
    check_dim_timeout()
    update_bat_labels()
    now_t=time.monotonic()
    if now_t-last_batt_check>=BATT_CHECK_S:
        voltage=read_battery();bat_charging=voltage>=CHARGE_V
        bat_percent=max(0,min(100,int((voltage-3.0)/(4.2-3.0)*100))) if not bat_charging else 100
        last_batt_check=now_t;gc.collect()
    if both_held():
        if check_mode_switch():advance_mode();continue
    if mode==MODE_CLOCK:
        if not btn_boot.value:
            if is_waking():register_interaction();continue
            register_interaction()
            wait_release(btn_boot);result=run_time_set()
            if not result:
                if check_mode_switch():advance_mode()
            else:
                t=time.localtime();redraw_hands(t.tm_hour,t.tm_min,t.tm_sec)
                last_sec=t.tm_sec;display.refresh()
            continue
        t=time.localtime()
        if t.tm_sec!=last_sec:
            redraw_hands(t.tm_hour,t.tm_min,t.tm_sec);last_sec=t.tm_sec;display.refresh()
        else:
            time.sleep(0.01)
    elif mode==MODE_METRO:
        a2_now=btn_a2.value
        if btn_a2_prev and not a2_now:
            if is_waking():register_interaction();btn_a2_prev=btn_a2.value
            elif not both_held():
                a2_press_t=time.monotonic()
                while not btn_a2.value:
                    if both_held():break
                    if time.monotonic()-a2_press_t>=BOTH_HOLD_S*2:
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
        boot_now=btn_boot.value
        if btn_boot_prev and not boot_now:
            if is_waking():register_interaction();boot_now=btn_boot.value
            elif not both_held():
                boot_press_t=time.monotonic()
                while not btn_boot.value:
                    if both_held():break
                    if time.monotonic()-boot_press_t>=BOTH_HOLD_S*2:
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
            now=time.monotonic();actual_interval=now-last_beat_t;last_beat_t=now
            if beat_count%8==0:gc.collect()
    elif mode==MODE_TUNER:
        now=time.monotonic()
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
        a2_now=btn_a2.value
        if btn_a2_prev and not a2_now:
            if is_waking():register_interaction();a2_now=btn_a2.value
        btn_a2_prev=a2_now
        boot_now=btn_boot.value
        if btn_boot_prev and not boot_now:
            if is_waking():register_interaction();boot_now=btn_boot.value
            elif not both_held():
                wait_release(btn_boot)
                boot_now=btn_boot.value
                tuner_muted=not tuner_muted
                lbl_tuner_mute.text="MUTE" if tuner_muted else "LIVE"
                display.refresh()
                register_interaction()
                if not tuner_muted:
                    buzzer.frequency=TUNER_FREQ;buzzer.duty_cycle=BUZZER_DUTY
                    tuner_tone_on=True;tuner_next_t=time.monotonic()+TUNER_ON_S
                else:
                    buzzer.duty_cycle=0;tuner_tone_on=False
        btn_boot_prev=boot_now
        time.sleep(0.02)
