from engine import *
from models import *
import re,os
ROOT=Path(__file__).resolve().parent.parent
CONFIG=json.loads((ROOT/'video.json').read_text())
SCENES=[(s['start'],s['end'],s['title'],s['label']) for s in CONFIG['scenes']]
# Cache a mathematical spiral disk texture; it is a drawing, not a telescope photo.
gy,gx=np.mgrid[-1:1:800j,-1:1:800j];rr=np.sqrt(gx*gx+gy*gy);theta=np.arctan2(gy,gx)
arm=np.maximum(0,np.cos(3*theta-5.2*np.log(rr+.04)))**10
bright=np.exp(-rr*3.4)*(.16+1.35*arm)+1.25*np.exp(-rr*rr*120)
gal=np.zeros((800,800,4),dtype=np.uint8)
gal[:,:,0]=np.clip(180+bright*60,0,255);gal[:,:,1]=np.clip(196+bright*38,0,255);gal[:,:,2]=np.clip(225+bright*20,0,255);gal[:,:,3]=np.clip(bright*190*np.clip((1-rr)*5,0,1),0,255)
galaxy_image=skia.Image.fromarray(gal,colorType=skia.ColorType.kRGBA_8888_ColorType)
rng=np.random.default_rng(458)
stars=[(rng.uniform(45,W-45),rng.uniform(240,910),rng.uniform(.6,1.7),rng.uniform(.15,.6)) for _ in range(105)]
cloud_offsets=[(rng.normal(0,65),rng.normal(0,92),rng.uniform(5,16)) for _ in range(16)]
cluster_galaxies=[(rng.normal(0,85),rng.normal(0,105),rng.uniform(2,6)) for _ in range(23)]
# Mild pseudo-3D network. Nodes/edges and all trajectories are fixed before rendering.
nodes=np.column_stack([rng.uniform(-1,1,52),rng.uniform(-.7,.7,52),rng.uniform(-.7,.7,52)])
edges=[]
for i in range(len(nodes)):
 for j in np.argsort(np.sum((nodes-nodes[i])**2,axis=1))[1:4]:
  if i<int(j):edges.append((i,int(j)))
curve_r=np.linspace(.05,30,190)
VB=np.array([baryon_speed(float(r)) for r in curve_r]);VH=np.array([halo_speed(float(r)) for r in curve_r]);VT=np.hypot(VB,VH);VO=np.array([illustrative_observation_trend(float(r)) for r in curve_r])
voice=json.loads((ROOT/'assets/voice-timing.json').read_text())
caps=[]
for s in voice['scenes']:
 phrases=[p for p in re.split('(?<=[，。？])',s['text']) if p];total=sum(map(len,phrases));pos=s['startOfSpeech'];dur=s['endOfSpeech']-pos
 for phrase in phrases:
  end=pos+dur*len(phrase)/total;caps.append((pos,end,phrase));pos=end
if caps:caps[-1]=(caps[-1][0],60.0,caps[-1][2])
(ROOT/'assets/captions.json').write_text(json.dumps(caps,ensure_ascii=False,indent=2))
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(ROOT/'assets/captions.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{s}' for i,(a,b,s) in enumerate(caps)))

def oval(c,x,y,rx,ry,col,aa=1,stroke=False,w=1):c.drawOval(skia.Rect.MakeLTRB(x-rx,y-ry,x+rx,y+ry),paint(col,aa,w,stroke))
def glow(c,x,y,r,col,aa=1):
 circle(c,x,y,r*2.8,col,.06*aa);circle(c,x,y,r*1.7,col,.14*aa);circle(c,x,y,r,col,.95*aa)
def panel(c,x,y,w,h,aa=.75):c.drawRoundRect(skia.Rect.MakeXYWH(x,y,w,h),15,15,paint('#08172a',aa))
def halo(c,cx,cy,scale,aa=1):
 # An outlined projected halo field, never a directly luminous gas cloud.
 for k in range(5):oval(c,cx,cy,scale*(.64+k*.1),scale*(.5+k*.07),'#63badd',aa*(.03 if k<4 else .2),k==4,2)
 for k in [0,1]:oval(c,cx,cy,scale,scale*(.36+k*.2),'#83d8f1',.14*aa,True,1)
 line(c,cx-scale*.9,cy,cx+scale*.9,cy,'#7cb7cf',.1*aa,1)
def galaxy(c,cx,cy,size,t,incl=.58,aa=1):
 c.save();c.translate(cx,cy);c.rotate(-14+t*.22);c.scale(size/400,size/400*incl);c.drawImage(galaxy_image,-400,-400,paint=skia.Paint(Alphaf=aa));c.restore();glow(c,cx,cy,max(3,size*.022),'#ffe8c3',aa)
def header(c,si,title,en):
 text(c,f'COSMIC EVIDENCE / 0{si+1}',90,54,23,'#91adc3');text(c,en,1680,58,18,'#91adc3',True)
 text(c,title,90,124,50,'#edf3fa',bold=True);line(c,90,207,1830,207,'#6b92b0',.3,1)
def legend(c,s,x,y,col):line(c,x,y+13,x+32,y+13,col,1,4);text(c,s,x+46,y,24,'#dce8f3')
def diagram_note(c,s):text(c,s,960,900,23,'#91acc5',True)
def composition(c,x,y):
 # Present-day total mass-energy density under the standard cosmological model.
 text(c,'今天宇宙的总质能密度',x,y,27,'#a8bfd1',True)
 for j,(title,value,col) in enumerate([('普通物质','约 5%','#f2d7a0'),('暗物质','约 27%','#8bdaf4'),('暗能量','约 68%','#ac9ed8')]):
  yy=y+64+j*90;text(c,title,x-162,yy,28,'#d9e6f2');text(c,value,x+110,yy,32,col,True,True);line(c,x-160,yy+47,x-160+320*[.05,.27,.68][j],yy+47,col,1,7)
 text(c,'标准宇宙学模型下的近似比例',x,y+360,21,'#94a9c0',True)
 text(c,'暗物质与暗能量是不同成分',x,y+400,22,'#b7a9de',True)
def rotation(c,t,q):
 cx,cy=415,535;halo(c,cx,cy,292,ease((q-.48)/.3));galaxy(c,cx,cy,240,t,incl=.77)
 for k,r in enumerate([6.,12.,20.,28.]):
  rad=r*8;oval(c,cx,cy,rad,rad*.77,'#5c839e',.35,True,1)
  phase=k*1.37+(t-8)*.035*total_speed(r)/r
  x=cx+rad*math.cos(phase);y=cy+rad*.77*math.sin(phase);glow(c,x,y,5,'#e3f7ff')
 text(c,'外围恒星持续绕行',cx,817,28,'#bdd9e9',True);text(c,'轨道角速度由同一模型的 v(r)/r 决定',cx,863,21,'#8fa9c0',True)
 x0,y0,ww,hh=850,732,850,388
 for r in [0,10,20,30]:
  xx=x0+r/30*ww;line(c,xx,y0-hh,xx,y0,'#59748e',.22,1);text(c,str(r),xx,y0+14,23,'#9cafc3',True)
 for v in [0,100,200,300]:
  yy=y0-v/300*hh;line(c,x0,yy,x0+ww,yy,'#59748e',.22,1);text(c,str(v),x0-52,yy-12,22,'#9cafc3')
 line(c,x0,y0,x0+ww,y0,'#b4cadf',.8,2);line(c,x0,y0,x0,y0-hh,'#b4cadf',.8,2)
 text(c,'轨道速度 / km/s',x0-42,y0-hh-50,24,'#adbed0');text(c,'距星系中心 / kpc',1270,y0+53,24,'#adbed0',True)
 n=max(2,min(len(curve_r),int(ease(q/.45)*len(curve_r))))
 A=[(x0+float(r)/30*ww,y0-float(v)/300*hh) for r,v in zip(curve_r[:n],VB[:n])];B=[(x0+float(r)/30*ww,y0-float(v)/300*hh) for r,v in zip(curve_r[:n],VO[:n])]
 if q>.3:
  poly=skia.Path();poly.moveTo(*A[0])
  for pt in A[1:]+list(reversed(B)):poly.lineTo(*pt)
  poly.close();c.drawPath(poly,paint('#6895c8',.12*ease((q-.3)/.2)))
 path(c,A,'#f0bb75',1,4);path(c,B,'#c5ddf6',1,3)
 if q>.55:path(c,[(x0+float(r)/30*ww,y0-float(v)/300*hh) for r,v in zip(curve_r,VT)],'#75e3e0',ease((q-.55)/.2),4)
 legend(c,'普通物质模型',835,250,'#f0bb75');legend(c,'典型观测趋势（示意）',1160,250,'#c5ddf6')
 if q>.55:legend(c,'加入暗物质晕',1420,295,'#75e3e0')
 text(c,'v(r) = √[G M(r) / r]',1275,827,31,'#e8d4aa',True)
 text(c,'球对称圆轨道近似 · 曲线均为模型示意，非实测数据',1275,878,21,'#94abc2',True)
def cluster(c,t,q):
 p=ease(min(q/.74,1));galpos,gaspos=cluster_positions(p);cy=520
 # Gas cloud shapes: orange, slowed near center. Galaxies: small silver ellipses.
 for k,gx in enumerate(gaspos):
  for ox,oy,r in cloud_offsets:oval(c,gx+ox,cy+oy*.65,70+r,52+r*.6,'#e67b54',.035)
  oval(c,gx,cy,110,81,'#fa956e',.18,True,2)
 lens_a=ease((q-.28)/.34)
 for k,gx in enumerate(galpos):
  for ring in [1,.8,.6]:oval(c,gx,cy,143*ring,175*ring,'#80bde8',lens_a*(.20 if ring==1 else .10),True,2)
  for ox,oy,r in cluster_galaxies:oval(c,gx+ox,cy+oy,r*1.7,r*.55,'#e9edee',.7)
  line(c,gx,cy-192,gx,cy-215,'#8acfe9',lens_a,2)
 text(c,'子弹星系团：碰撞与观测关系示意',960,245,28,'#d9e7f5',True)
 text(c,'非真实照片 · 非真实透镜反演图',960,288,23,'#94acc5',True)
 legend(c,'可见星系：多数恒星穿行',120,748,'#e9edee');legend(c,'高温气体：X 射线对应成分',675,748,'#fa956e');legend(c,'引力透镜重建质量：蓝色轮廓',1230,748,'#80bde8')
 text(c,'气体峰被阻滞',960,678,25,'#f5ae8a',True)
 if q>.64:
  for gx,gasx in zip(galpos,gaspos):
   yy=cy+135;line(c,gx,yy,gasx,yy,'#f5d9a3',.85,2);circle(c,gx,yy,4,'#85c9ee');circle(c,gasx,yy,4,'#ee9677')
  text(c,'质量峰与热气体峰的空间偏移，是重要引力证据',960,834,30,'#d9eafb',True)
 diagram_note(c,'蓝色来自引力透镜重建的质量分布概念，不是直接看到的暗物质发光。')
def web(c,t,q):
 # Slowly turn a fixed 3D graph and project; no N-body simulation or free particles.
 ang=.10*(t-37);ct,st=math.cos(ang),math.sin(ang);s=1+.13*q;proj=[]
 for x,y,z in nodes:
  xx=x*ct+z*st;zz=-x*st+z*ct;f=1/(1+.22*zz);proj.append((960+xx*640*s*f,510+y*330*s*f))
 contrast=.15+.85*ease(q/.68)
 for i,j in edges:
  p1,p2=proj[i],proj[j];line(c,*p1,*p2,'#7b9dde',contrast*.35,1.8)
  # Ordinary gas gathers along the same potential filaments, delayed with respect to the framework.
  if q>.25:
   frac=1-ease((q-.25)/.65);u=.15+.7*frac;xx=p1[0]*(1-u)+p2[0]*u;yy=p1[1]*(1-u)+p2[1]*u;glow(c,xx,yy,2.4,'#f3d9ae',ease((q-.25)/.25))
 for k,(x,y) in enumerate(proj):
  glow(c,x,y,2.4+(k%4)*.65,'#91b8ed',contrast)
  if q>.5 and k%4==0:galaxy(c,x,y,20+6*q,t,incl=.5,aa=ease((q-.5)/.3))
 text(c,'暗物质引力 → 密度扰动增长 → 结构形成',960,792,33,'#b3d5f2',True)
 text(c,'普通物质的冷却、气体动力学与恒星形成，同样重要',960,849,27,'#e0cda9',True)
 diagram_note(c,'宇宙网为标准模型下的结构形成示意；不是暗物质实体的直接照片。')

def scene(c,t,si,q):
 if si==0:
  sz=330+65*ease(q);halo(c,620,545,sz*1.1,ease(q/.6));galaxy(c,620,545,sz,t,incl=.66)
  text(c,'暗物质晕 · 模型示意',620,819,28,'#8ac8e3',True);text(c,'Dark Matter',620,865,24,'#adbed2',True)
  panel(c,1190,273,560,594,.73);composition(c,1470,305)
 elif si==1:rotation(c,t,q)
 elif si==2:cluster(c,t,q)
 elif si==3:web(c,t,q)
 elif si==4:
  # Abstract candidate emblem: explicitly a question, not a discovered particle.
  circle(c,960,485,120,'#6f91b8',.32,True,2);circle(c,960,485,94,'#8bb4db',.16,True,1)
  text(c,'?',960,395,140,'#d0e5f5',True)
  for j,(label,xx) in enumerate([('轴子等候选粒子',390),('WIMP 等候选粒子',960),('修正引力研究',1530)]):
   panel(c,xx-230,668,460,72,.9);text(c,label,xx,687,29,'#a9c6dd',True)
  text(c,'尚无被普遍接受的暗物质粒子直接探测结果',960,796,33,'#e4cda3',True)
  text(c,'多种独立观测共同支持标准暗物质模型；微观本质仍未知',960,859,26,'#adbed4',True)
 elif si==5:
  fade=1-ease(q/.65);halo(c,960,501,365,fade*.6);galaxy(c,960,501,345+15*q,t,incl=.58)
  panel(c,470,681,980,99,.88);text(c,'暗物质的身份，仍待揭晓。',960,705,42,'#f2d9af',True,True)
  text(c,'强有力的引力证据 ≠ 已确认微观本质',960,819,30,'#b3d8ea',True)
  diagram_note(c,'星系为原创模型绘图；暗物质晕淡出只表示去掉示意图层。')

surf=skia.Surface(W,H);c=surf.getCanvas()
def frame(t):
 anim=min(t,59.0)
 c.drawImage(background,0,0)
 for xx,yy,rr,aa in stars:circle(c,xx,yy,rr,'#d6e6f3',aa)
 si=next(i for i,(a,b,*_) in enumerate(SCENES) if a<=t<b);a,b,title,en=SCENES[si];q=(anim-a)/(b-a)
 header(c,si,title,en);scene(c,anim,si,q)
 c.drawRect(skia.Rect.MakeXYWH(0,952,W,128),paint('#020711',.97))
 cap=next((s for a,b,s in caps if a<=t<b),'')
 if cap:text(c,cap,960,979,36,'#ffffff',True)
 line(c,90,1049,1830,1049,'#3c5c78',.5,2);line(c,90,1049,90+1740*anim/60,1049,'#8acde3',1,3)
 text(c,f'{min(int(t),59):02d} / 60',1785,1017,18,'#89a3ba')
 if si>0 and t-a<.25:c.drawRect(skia.Rect.MakeWH(W,H),paint('#0c2034',.25*(1-ease((t-a)/.25))))
 return surf.makeImageSnapshot()
