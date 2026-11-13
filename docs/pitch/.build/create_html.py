from pathlib import Path
import base64

root = Path('C:/DAIT/docs/pitch')
slides = []
for n in range(1, 13):
    raw = (root / '.build' / f'final12-{n}.png').read_bytes()
    data = base64.b64encode(raw).decode('ascii')
    slides.append(f'<img class="slide" src="data:image/png;base64,{data}" alt="DAIT 발표 자료 {n}번 슬라이드" {"" if n == 1 else "hidden"}>')

html = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DAIT 3팀 발표 자료</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#09172e;color:white;font-family:Malgun Gothic,system-ui,sans-serif;min-height:100dvh;display:flex;align-items:center;justify-content:center}
main{width:min(100vw,1600px);padding:20px} .frame{background:#102a56;box-shadow:0 12px 45px #0007;aspect-ratio:16/9;overflow:hidden}.slide{display:block;width:100%;height:100%;object-fit:contain}.slide[hidden]{display:none}
.controls{display:flex;justify-content:center;align-items:center;gap:16px;padding:18px 0;color:#d2def2}button{background:#1e3c68;color:white;border:1px solid #7890b0;border-radius:8px;padding:10px 18px;font:inherit;cursor:pointer}button:hover{background:#2454a0}button:focus-visible{outline:3px solid #8ab5ff;outline-offset:3px}button:disabled{opacity:.4;cursor:default}.count{min-width:70px;text-align:center}.hint{text-align:center;color:#aabbd3;font-size:13px;margin:0} @media(max-width:600px){main{padding:8px}.controls{gap:8px}button{padding:9px 12px}.hint{font-size:11px}}
</style></head><body><main><div class="frame" aria-live="polite">SLIDES</div><nav class="controls" aria-label="슬라이드 이동"><button id="prev" type="button">이전</button><span class="count" id="count"></span><button id="next" type="button">다음</button><button id="full" type="button">전체 화면</button></nav><p class="hint">방향키 또는 스페이스바로 이동 · F로 전체 화면</p></main>
<script>
const slides=[...document.querySelectorAll('.slide')], count=document.querySelector('#count'),prev=document.querySelector('#prev'),next=document.querySelector('#next');let current=0;
function show(n){current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>s.hidden=i!==current);count.textContent=(current+1)+' / '+slides.length;prev.disabled=current===0;next.disabled=current===slides.length-1;}
prev.onclick=()=>show(current-1);next.onclick=()=>show(current+1);async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch{}}document.querySelector('#full').onclick=fullscreen;
document.addEventListener('keydown',e=>{if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();show(current+1)}else if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();show(current-1)}else if(e.key==='Home'){e.preventDefault();show(0)}else if(e.key==='End'){e.preventDefault();show(slides.length-1)}else if(e.key.toLowerCase()==='f')fullscreen()});show(0);
</script></body></html>'''.replace('SLIDES', '\n'.join(slides))
out = root / 'output' / 'DAIT_3팀_발표대회_12장.html'
out.write_text(html, encoding='utf-8')
print(f'{out} / {len(slides)} slides / {out.stat().st_size} bytes')
