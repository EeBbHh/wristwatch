# sprites.py — note sprite pixel buffers for metronome
# Imported by code.py after shared_bitmap is allocated.
# CX/CY and WIDTH/HEIGHT are duplicated from code.py intentionally —
# this module imports independently and cannot reference code.py globals.
import math,gc
CX,CY=120,120
WIDTH,HEIGHT=240,240

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

def build_sprites():
    SPRITE={}
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
    return SPRITE
