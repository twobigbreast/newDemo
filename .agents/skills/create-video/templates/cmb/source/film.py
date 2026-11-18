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
# An analytic illustration, never an observation map. Mollweide outline and
# deterministic low-order angular modes create conceptual temperature patches.
ny,nx=420,900;yy,xx=np.mgrid[-1:1:complex(ny),-2:2:complex(nx)];ell=(xx/2)**2+yy**2
th=np.arcsin(np.clip(yy,-1,1));lon=np.pi*xx/(2*np.maximum(np.cos(th),.001));lat=np.arcsin(np.clip((2*th+np.sin(2*th))/np.pi,-1,1));field=np.zeros_like(xx)
mode_rng=np.random.default_rng(1091)
nhat=np.array([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])
for j in range(80):
 direction=mode_rng.normal(size=3);direction/=np.linalg.norm(direction)
 k=mode_rng.uniform(12,68);phase=mode_rng.uniform(0,math.tau)
 field+=np.cos(k*np.einsum('i,ijk->jk',direction,nhat)+phase)/math.sqrt(80)
field=np.tanh(field*.65);cold=np.array([28,83,158]);mid=np.array([242,224,169]);hot=np.array([185,49,27]);rgb=np.where((field<0)[...,None],mid+(mid-cold)*field[...,None],mid+(hot-mid)*field[...,None]);a=np.where((ell<=1)&(abs(lon)<=np.pi),255,0).astype('uint8');cmb=skia.Image.fromarray(np.dstack([rgb.astype('uint8'),a]),colorType=skia.ColorType.kRGBA_8888_ColorType)
stars=[(rng.uniform(20,W-20),rng.uniform(140,870),rng.uniform(.7,2),rng.uniform(.15,.65)) for _ in range(140)]
ions=[(rng.uniform(160,1760),rng.uniform(290,760),rng.uniform(0,6.28),rng.uniform(0,1)) for _ in range(34)]
# continuous zig-zag paths, vertices correspond to electrons in scattering scene
photonpaths=[]
for k in range(12):
 pp=[(rng.uniform(170,550),rng.uniform(310,730))]
 for j in range(9):
  px,py=pp[-1]; pp.append((min(1740,max(150,px+rng.uniform(-50,260))),min(770,max(280,py+rng.uniform(-140,140)))))
 photonpaths.append(pp)
nodes=np.column_stack([rng.uniform(200,1720,44),rng.uniform(300,740,44)])
edges=[]
for i in range(len(nodes)):
 for j in np.argsort(np.sum((nodes-nodes[i])**2,axis=1))[1:4]:
  if i<int(j):edges.append((i,int(j)))
def mapdraw(c,t,cx=960,cy=520,ww=1300,aa=1):
 hh=ww*420/900;rect=skia.Rect.MakeXYWH(cx-ww/2,cy-hh/2,ww,hh);c.drawImageRect(cmb,rect,skia.SamplingOptions(skia.FilterMode.kLinear),skia.Paint(Alphaf=aa))
 text(c,'全天温度图 · 示意，非观测数据',1485,237,22,'#a6b9d2',True,alpha=aa)
def header(c,num,title,en):
 text(c,f'COSMIC ARCHIVE  /  0{num}',95,60,24,'#8bafc9');text(c,en,1690,64,19,'#8bafc9',True)
 text(c,title,95,132,48,bold=True);line(c,96,214,1824,214,'#7b9dbb',.3,1)
def tag(c,s,x,y):
 rr=skia.Rect.MakeXYWH(x,y,520,54);c.drawRoundRect(rr,12,12,paint('#102b40',.88));text(c,s,x+18,y+13,24,'#b4eaff')
def glow(c,x,y,r,col):
 circle(c,x,y,r*3,col,.055);circle(c,x,y,r*1.8,col,.14);circle(c,x,y,r,col,.95)
def galaxy(c,x,y,s,t):
 c.save();c.translate(x,y);c.rotate(-20)
 for j in range(4):
  r=s*(1-j*.19);c.drawOval(skia.Rect.MakeLTRB(-r,-r*.23,r,r*.23),paint('#80accd',.035+j*.023))
 glow(c,0,0,max(2,s*.06),'#ffe4b0');c.restore()
def particles(c,t,rec=0):
 for k,(px,py,ph,st) in enumerate(ions):
  x=px+8*math.sin(t*.3+ph);y=py+7*math.cos(t*.3+ph)
  circle(c,x,y,11,'#f3b86a');circle(c,x-3,y-3,3,'#ffedbd')
  bind=ease((rec-st*.7)/.3);ex=x+(48*math.cos(ph+t*.12))*(1-bind)+17*bind;ey=y+(39*math.sin(ph+t*.12))*(1-bind)
  glow(c,ex,ey,4,'#73dcff')
  if bind>.1:circle(c,x,y,28,'#9bd8f5',bind*.4,True,1.7)
 for k,pp in enumerate(photonpaths):
  speed=t*.67+k*.71;u=speed%8;idx=int(u);frac=u-idx
  pts=pp[max(0,idx-2):idx+1];xx=pp[idx][0]*(1-frac)+pp[idx+1][0]*frac;yy=pp[idx][1]*(1-frac)+pp[idx+1][1]*frac
  if rec<.5:
   path(c,pts+[(xx,yy)],'#ffe0a1',.52,2);glow(c,xx,yy,4,'#ffe6b0')
   # electron at each scattering vertex
   glow(c,*pp[idx+1],3,'#78ddfa')
  else:
   # staggered release; some paths remain scattering longer than others
   freed=ease((rec-.5-k*.025)/.18)
   qx=160+((t*180+k*153)%1560);qy=300+k*39
   line(c,qx-110*freed,qy,qx,qy,'#83ebff',freed*.8,2.3);glow(c,qx,qy,4,'#a9f5ff')
def web(c,t,a=1):
 for i,j in edges:
  p=nodes[i];q=nodes[j];mid=(p+q)/2+np.array([12*math.sin(i),19*math.cos(j)])
  path(c,[tuple(p),tuple(mid),tuple(q)],'#7496d4',a*.35,2)
 for k,(xx,yy) in enumerate(nodes):glow(c,xx,yy,(2+(k%4)*.8)*( .7+.3*math.sin(t*.4+k)**2),'#b4dfff')
 # modest dense junctions, no mapping from CMB pixels
 for i in [3,11,24,31]:circle(c,*nodes[i],15,'#bfcfff',.055*a)
CONFIG=json.loads((ROOT/'video.json').read_text())
SCENES=[(s['start'],s['end'],s['title'],s['label']) for s in CONFIG['scenes']]
voice=json.loads((ROOT/'assets/voice-timing.json').read_text())
# Phrase-sized subtitles, synchronized to the measured audio interval.
import re
caps=[]
for s in voice['scenes']:
 phrases=[p for p in re.split('(?<=[，。？])',s['text']) if p];full=sum(len(p) for p in phrases);pos=s['startOfSpeech'];dur=s['endOfSpeech']-pos
 for p in phrases:
  end=pos+dur*len(p)/full;caps.append((pos,end,p));pos=end
(ROOT/'assets/captions.json').write_text(json.dumps(caps,ensure_ascii=False,indent=2))
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(ROOT/'assets/captions.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{s}' for i,(a,b,s) in enumerate(caps)))
surf=skia.Surface(W,H);c=surf.getCanvas()
def frame(t):
 t=min(t,59);c.drawImage(background,0,0)
 for xx,yy,rr,aa in stars:circle(c,xx,yy,rr,'#d0e6ff',aa)
 si=next(i for i,(a,b,*_) in enumerate(SCENES) if a<=t<b);a,b,title,en=SCENES[si];q=(t-a)/(b-a);header(c,si+1,title,en)
 if si==0:
  for k in range(8):
   z=1+q*1.1;xx=960+(220+k*191-960)*z;yy=500+(290+(k*97)%360-500)*z;galaxy(c,xx,yy,40+(k%3)*26,t)
  fade=ease((q-.18)/.45);mapdraw(c,t,cy=535,ww=1250+q*80,aa=fade*.85)
  # dark readable title plate, two lines avoid truncation
  c.drawRoundRect(skia.Rect.MakeXYWH(300,380,1320,190),18,18,paint('#050e20',.78))
  text(c,'138 亿年前的光，',960,402,62,'#fff0d2',True,True);text(c,'为什么今天还能看见？',960,488,62,'#fff0d2',True,True)
  text(c,'宇宙微波背景辐射 · CMB',960,795,30,'#9fddf1',True)
 elif si==1:
  # warm broad plasma, not a fireball in empty space
  c.drawRect(skia.Rect.MakeXYWH(110,255,1700,550),paint('#af6425',.13));particles(c,t)
  tag(c,'自由电子 e-',140,814);tag(c,'汤姆孙散射：方向不断改变',1140,814)
  text(c,'早期宇宙并不缺光；光子一直在运动。',960,890,26,'#e0bea1',True)
 elif si==2:
  particles(c,t,q)
  c.drawRoundRect(skia.Rect.MakeXYWH(790,248,340,129),16,16,paint('#071324',.92))
  text(c,'约 38 万年',960,260,46,'#ffdfa7',True,True);text(c,'≈ 3000 K',960,323,33,'#e3d0aa',True)
  tag(c,'复合  Recombination',145,808);tag(c,'光子退耦  Photon decoupling',1140,808)
  text(c,'自由电子减少 → 散射率降低 · 是持续的过程，并非瞬间释放',960,891,26,'#a9d5e1',True)
 elif si==3:
  aq=1+q*2.9
  for k in range(-13,14):
   dx=k*100*aq;line(c,960+dx,300,960+dx,748,'#537bb3',.28,1)
  for k in range(-4,5):
   yy=530+k*70*aq;line(c,150,yy,1770,yy,'#537bb3',.28,1)
  pts=[];wavelength=90*aq
  # moving crests maintain constant screen propagation speed at a given local a
  for xx in range(150,1771,4):pts.append((xx,535+80*math.sin(2*math.pi*((xx-960)/wavelength-200/(90*(2.9/12))*math.log(aq)))))
  path(c,pts,'#a8bcff',.12,18);path(c,pts,'#b9ccff',1,4)
  text(c,'约 3000 K',260,288,41,'#ffcc8a',True,True);text(c,'今天 2.725 K',1540,288,41,'#a3ddff',True,True)
  text(c,'λ ∝ a(t)      E = hc / λ      T ∝ 1 / a(t)',960,720,39,'#ece3ff',True)
  text(c,'尺度因子增长约 1100 倍 · 波长变化压缩比例示意',960,799,29,'#b7b1db',True)
  text(c,'局部真空中仍以光速传播；温度指辐射的黑体温度。',960,869,26,'#adbed6',True)
 elif si==4:
  if q<.55:
   mapdraw(c,t,cy=520,ww=1120+q*120,aa=1-ease((q-.43)/.12))
   text(c,'平均温度 2.725 K     |     ΔT / T ~ 10^-5',960,805,35,'#ffdea5',True)
   text(c,'伪彩色只表示温度差异；已扣除主要前景与偶极等影响',960,877,25,'#b1c6dd',True)
  else:
   aa=ease((q-.55)/.16);web(c,t,aa)
   text(c,'早期扰动  →  漫长的引力增长  →  宇宙网',960,804,34,'#b4dbf6',True)
   text(c,'包含密度扰动、引力势与光子—重子声学振荡信息',960,866,25,'#b0bfdb',True)
   text(c,'结构形成概念示意 · 与温度图斑点不作一一对应',960,904,22,'#93a5c4',True)
 elif si==5:
  if q<.3:web(c,t,1-ease(q/.3))
  mapdraw(c,t,cy=500,ww=1080,aa=ease(q/.25)*.65)
  c.drawRoundRect(skia.Rect.MakeXYWH(370,369,1180,192),18,18,paint('#070f23',.86))
  text(c,'宇宙微波背景辐射',960,390,66,'#fff0d5',True,True)
  text(c,'来自宇宙约 38 万岁时的光',960,486,37,'#b4e6ff',True)
  # observer-dependent last scattering surface: many lines of sight, not a shell of universe
  circle(c,960,744,9,'#ffe4aa')
  for k in range(7):
   ang=math.pi*(.12+.76*k/6);xx=960+220*math.cos(ang);yy=744-100*math.sin(ang);line(c,xx,yy,960,744,'#8bbddf',.45,2);glow(c,xx,yy,3,'#9fdfff')
  text(c,'不同方向的遥远区域 → 我们的最后散射面',960,789,28,'#a7cde4',True)
  text(c,'不是宇宙的实体外壳，宇宙膨胀也没有爆炸中心',960,841,24,'#98acc9',True)
 # Subtitles separated from science annotations
 c.drawRect(skia.Rect.MakeXYWH(0,958,W,122),paint('#020711',.96))
 cap=next((s for aa,bb,s in caps if aa<=t<bb),'')
 if cap:text(c,cap,960,981,36,'#ffffff',True)
 line(c,95,1047,1825,1047,'#42617d',.5,2);line(c,95,1047,95+1730*t/60,1047,'#8bd9e7',1,3)
 text(c,f'{int(t):02d} / 60',1770,1019,18,'#8ca6bf')
 # short crossfade to a tinted transition; no black frames
 if si>0 and t-a<.25:c.drawRect(skia.Rect.MakeWH(W,H),paint('#0a1a2d',(1-ease((t-a)/.25))*.38))
 return surf.makeImageSnapshot()
