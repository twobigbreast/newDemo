#!/usr/bin/env python3
"""Generate original 60s Chinese male narration and an original procedural score.

KOKORO_MODEL_DIR points to the externally downloaded Kokoro int8 model.
Models and the Python virtualenv must be excluded from source/download archives.
"""
from pathlib import Path
import json, os, shutil, subprocess, time
import numpy as np
import sherpa_onnx
import soundfile as sf

ROOT=Path(__file__).resolve().parent.parent
ASSETS=ROOT/'assets'; ASSETS.mkdir(exist_ok=True)
SCRATCH=ROOT/'work/audio'; SCRATCH.mkdir(parents=True,exist_ok=True)
MODEL=Path(os.environ['KOKORO_MODEL_DIR'])
SR=24000; TOTAL=60; VOICE=50; MODEL_SPEED=1.0; MAX_ATEMPO=1.0
CONFIG=json.loads((ROOT/'video.json').read_text())
SCENES=[(s['start'],s['end'],s['narration']) for s in CONFIG['scenes']]
MODEL_SPEED=float(CONFIG.get('voice',{}).get('speed',1.0))
MAX_ATEMPO=float(CONFIG.get('voice',{}).get('max_atempo',1.0))
VOICE=int(CONFIG.get('voice',{}).get('speaker',50))

def ffmpeg(args):
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)

def trim_edges(a):
 # Preserve all spoken sound; only remove near-silent leading/trailing model padding.
 active=np.flatnonzero(np.abs(a)>.001)
 if len(active):a=a[max(0,active[0]-int(.025*SR)):min(len(a),active[-1]+int(.07*SR))]
 edge=min(120,len(a)//4)
 a=a.copy();a[:edge]*=np.linspace(0,1,edge);a[-edge:]*=np.linspace(1,0,edge)
 return a

def shrink_pauses(a,max_pause=.16):
 # Optional conservative pause tightening: only whole 10ms windows below -55dBFS.
 # Never time-compress voiced portions. Keep at least160ms for long punctuation pauses.
 block=240; blocks=len(a)//block
 rms=np.sqrt(np.mean(a[:blocks*block].reshape(blocks,block)**2,axis=1))
 silent=rms<.0018;keep=np.ones(blocks,dtype=bool);i=0
 while i<blocks:
  if not silent[i]:i+=1;continue
  j=i+1
  while j<blocks and silent[j]:j+=1
  retain=round(max_pause*SR/block)
  if j-i>retain:keep[i+retain:j]=False
  i=j
 return np.concatenate([a[:blocks*block].reshape(blocks,block)[keep].reshape(-1),a[blocks*block:]])

begin=time.perf_counter();cpu_begin=time.process_time()
config=sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(model=str(MODEL/'model.int8.onnx'),voices=str(MODEL/'voices.bin'),tokens=str(MODEL/'tokens.txt'),data_dir=str(MODEL/'espeak-ng-data'),dict_dir=str(MODEL/'dict'),lexicon=','.join(str(MODEL/f) for f in ['lexicon-us-en.txt','lexicon-zh.txt'])),num_threads=2,provider='cpu'),rule_fsts=','.join(str(MODEL/f) for f in ['phone-zh.fst','date-zh.fst','number-zh.fst']),max_num_sentences=1)
tts=sherpa_onnx.OfflineTts(config)
model_load_wall=time.perf_counter()-begin;model_load_cpu=time.process_time()-cpu_begin
master=np.zeros(TOTAL*SR,dtype=np.float32);timings=[];captions=[];tts_wall=0.;tts_cpu=0.
for i,(start,end,text) in enumerate(SCENES):
 at=start+.25;latest=59.85 if i==5 else end-.15;budget=latest-at
 generated_start=time.perf_counter();generated_cpu=time.process_time()
 audio=tts.generate(text,sid=VOICE,speed=MODEL_SPEED)
 a=trim_edges(np.asarray(audio.samples,dtype=np.float32));assert audio.sample_rate==SR
 tw=time.perf_counter()-generated_start;tc=time.process_time()-generated_cpu;tts_wall+=tw;tts_cpu+=tc
 raw_seconds=len(a)/SR;pause_tightened=False
 if CONFIG.get('voice',{}).get('allow_pause_tightening',False) and len(a)/SR>budget*MAX_ATEMPO:
  a=shrink_pauses(a);pause_tightened=True
 rate=max(1.,len(a)/SR/budget)
 if rate>MAX_ATEMPO+1e-6:
  sf.write(str(SCRATCH/f'unfitted-{i}.wav'),a,SR)
  raise RuntimeError(f'Scene{i} cannot fit naturally: {len(a)/SR:.3f}s into{budget:.3f}s, rate{rate:.3f}>{MAX_ATEMPO}. Uncompressed audio saved. Rearrange the timeline or simplify wording; do not speed up speech to fit the template.')
 if rate>1:
  inp=SCRATCH/f'scene-{i}-raw.wav';out=SCRATCH/f'scene-{i}-fit.wav';sf.write(str(inp),a,SR,subtype='FLOAT')
  ffmpeg(['-i',inp,'-af',f'atempo={rate:.9f}','-ar',SR,out]);a=sf.read(str(out),dtype='float32')[0]
 # atempo overlap-add has slight duration rounding: tiny terminal silence trim only.
 max_samples=round(budget*SR)
 if len(a)>max_samples:
  extra=len(a)-max_samples
  if np.max(np.abs(a[-extra:]))>.003:raise RuntimeError(f'Scene{i} atempo rounding exceeds budget with voiced samples')
  a=a[:max_samples]
 a*=min(1.4,.80/(np.max(np.abs(a))+1e-9))
 offset=round(at*SR);master[offset:offset+len(a)]+=a
 speech_end=at+len(a)/SR
 timings.append({'scene':i,'sceneStart':start,'sceneEnd':end,'text':text,'spokenText':text,'startOfSpeech':at,'endOfSpeech':speech_end,'budgetEnd':latest,'rawTrimmedSeconds':raw_seconds,'pauseTightened':pause_tightened,'modelSpeed':MODEL_SPEED,'atempo':rate,'ttsWallSeconds':tw,'ttsCpuSeconds':tc})
 captions.append((at,min(speech_end+.08,latest),text))
 print(json.dumps(timings[-1],ensure_ascii=False),flush=True)

sf.write(str(ASSETS/'narration.wav'),master,SR,subtype='PCM_16')
# Original ambient score: no recordings, samples, commercial melody or copyrighted music.
t=np.arange(TOTAL*SR,dtype=np.float64)/SR;score=np.zeros_like(t)
for hz,amp,phase in [(55,.036,0),(82.4069,.017,.7),(110,.008,1.2),(130.8128,.007,2.1),(164.8138,.004,2.9)]:
 score+=amp*np.sin(2*np.pi*hz*t+phase+.18*np.sin(.13*t))*(.75+.25*np.sin(.11*t+phase)**2)
score*=np.clip(t/3,0,1)*np.clip((60-t)/3,0,1)
# Smooth speech-aware ducking, computed independently of the narration waveform.
duck=np.ones_like(t)
for a,b,_ in captions:
 attack=np.clip((t-(a-.15))/.15,0,1);release=np.clip(((b+.3)-t)/.3,0,1)
 duck*=1-.72*np.minimum(attack,release)
score*=duck
sf.write(str(ASSETS/'score.wav'),score.astype(np.float32),SR,subtype='PCM_16')
ffmpeg(['-i',ASSETS/'narration.wav','-i',ASSETS/'score.wav','-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]','-map','[a]','-t','60','-ar','48000','-ac','1','-c:a','aac','-b:a','128k',ASSETS/'soundtrack.m4a'])

def stamp(seconds):
 ms=round(seconds*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(ASSETS/'captions.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{text}' for i,(a,b,text) in enumerate(captions))+'\n')
if (MODEL/'LICENSE').exists():shutil.copyfile(MODEL/'LICENSE',ASSETS/'KOKORO-LICENSE.txt')
summary={'durationSeconds':TOTAL,'sampleRate':SR,'voice':{'engine':'sherpa-onnx Kokoro int8 multilingual v1.0','speakerId':VOICE,'description':'Chinese male AI narration','modelSpeed':MODEL_SPEED,'modelSource':'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-int8-multi-lang-v1_0.tar.bz2'},'ttsWallSeconds':tts_wall,'ttsCpuSeconds':tts_cpu,'modelLoadWallSeconds':model_load_wall,'modelLoadCpuSeconds':model_load_cpu,'generationTotalWallSeconds':time.perf_counter()-begin,'generationTotalCpuSeconds':time.process_time()-cpu_begin,'narrationTextChanged':False,'lastSpeechEnd':timings[-1]['endOfSpeech'],'score':'Original deterministic low-amplitude sine ambient score with speech ducking; no copyrighted recordings','scenes':timings}
assert summary['lastSpeechEnd']<=59.85
(ASSETS/'voice-timing.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False),flush=True)
