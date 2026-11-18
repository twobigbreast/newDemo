"""CPU Skia renderer, direct RGBA pipe; no browser, GPU or per-frame PNGs.
Reuses the existing personal-notes Skia/FFmpeg architecture and audio pipeline.
"""
from pathlib import Path
import math, time, json, subprocess, resource, sys
import numpy as np
import skia
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent.parent
W,H,FPS=1920,1080,30
rng=np.random.default_rng(761)
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
fonts={}
def pf(size,bold=False):
 k=(size,bold)
 if k not in fonts: fonts[k]=ImageFont.truetype(BOLD if bold else FONT,size)
 return fonts[k]
def img(a): return skia.Image.fromarray(np.asarray(a.convert('RGBA')),colorType=skia.ColorType.kRGBA_8888_ColorType)
cache={}
def text(c,s,x,y,size=30,color='#eaf3ff',center=False,bold=False,alpha=1):
 key=(s,size,color,bold)
 if key not in cache:
  f=pf(size,bold); box=f.getbbox(s); im=Image.new('RGBA',(math.ceil(f.getlength(s))+8,size*2),(0,0,0,0));ImageDraw.Draw(im).text((4,-box[1]+2),s,font=f,fill=color);cache[key]=(img(im),im.width,box[3]-box[1]+4)
 im,ww,hh=cache[key];p=skia.Paint(Alphaf=max(0,min(1,alpha)));c.drawImage(im,x-ww/2 if center else x,y,paint=p)
def paint(col,alpha=1,width=1,stroke=False):
 rgb=tuple(int(col[i:i+2],16) for i in (1,3,5)) if isinstance(col,str) else col
 p=skia.Paint(Color=skia.ColorSetARGB(int(255*max(0,min(1,alpha))),*rgb),AntiAlias=True)
 if stroke:p.setStyle(skia.Paint.kStroke_Style);p.setStrokeWidth(width)
 return p
def line(c,x1,y1,x2,y2,col='#79d7ed',a=1,w=2):c.drawLine(x1,y1,x2,y2,paint(col,a,w,True))
def circle(c,x,y,r,col,a=1,stroke=False,w=1):c.drawCircle(x,y,r,paint(col,a,w,stroke))
def path(c,pts,col,a=1,w=2):
 p=skia.Path();p.moveTo(*pts[0])
 for v in pts[1:]:p.lineTo(*v)
 c.drawPath(p,paint(col,a,w,True))
def ease(x):x=max(0,min(1,x));return x*x*(3-2*x)
# Backgrounds are computed once, all full-size output frames stay 1920 x 1080.
y,x=np.mgrid[0:H,0:W];v=((x-1050)/1200)**2+((y-450)/800)**2
base=np.zeros((H,W,4),dtype=np.uint8);base[:,:,3]=255
base[:,:,0]=(3+8*np.exp(-v*2)).astype('uint8');base[:,:,1]=(7+17*np.exp(-v*2)).astype('uint8');base[:,:,2]=(18+35*np.exp(-v*2)).astype('uint8')
background=skia.Image.fromarray(base,colorType=skia.ColorType.kRGBA_8888_ColorType)
