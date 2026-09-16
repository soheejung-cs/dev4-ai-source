#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cubrid-source-notes 정적 사이트 생성기.
   사용: python3 tools/gen_site.py  (리포 루트에서)  → site/*.html 재생성"""
import re, html, os, sys, datetime

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def md2html(md):
    out=[]; i=0; L=md.split('\n'); inul=0; incode=False
    def close_ul():
        nonlocal inul
        while inul: out.append('</ul>'); inul-=1
    def inline(t):
        t=html.escape(t, quote=False)
        t=re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        t=re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
        t=re.sub(r'\[\[([a-z0-9-]+)\]\]', r'<em>\1</em>', t)
        t=re.sub(r'\[(\.5[012])([^\]]*)\]', lambda m: '<span class="chip c%s">%s%s</span>'%(m.group(1)[1:], m.group(1), m.group(2)), t)
        return t
    while i < len(L):
        l=L[i]
        if l.startswith('```'):
            close_ul()
            out.append('</code></pre>' if incode else '<pre><code>'); incode=not incode
            i+=1; continue
        if incode: out.append(html.escape(l)); i+=1; continue
        if l.startswith('|') and i+1<len(L) and re.match(r'^\|[\s:|-]+\|?$', L[i+1] or ''):
            close_ul(); hdr=[c.strip() for c in l.strip('|').split('|')]
            out.append('<div class="tbl"><table><thead><tr>'+''.join('<th>%s</th>'%inline(c) for c in hdr)+'</tr></thead><tbody>')
            i+=2
            while i<len(L) and L[i].startswith('|'):
                cells=[c.strip() for c in L[i].strip('|').split('|')]
                out.append('<tr>'+''.join('<td>%s</td>'%inline(c) for c in cells)+'</tr>'); i+=1
            out.append('</tbody></table></div>'); continue
        m=re.match(r'^(#{1,5}) (.*)', l)
        if m:
            close_ul(); n=len(m.group(1))
            out.append('<h%d>%s</h%d>'%(min(n+1,6), inline(m.group(2)), min(n+1,6))); i+=1; continue
        m=re.match(r'^(\s*)- (.*)', l)
        if m:
            depth=len(m.group(1))//2+1
            while inul<depth: out.append('<ul>'); inul+=1
            while inul>depth: out.append('</ul>'); inul-=1
            b=m.group(2); j=i+1
            while j<len(L) and L[j].startswith('  ') and not re.match(r'^\s*- ', L[j]) and L[j].strip():
                b+=' '+L[j].strip(); j+=1
            if b.startswith('✅ **리뷰 체크포인트**:'):
                out.append('<li class="ck"><span class="cklab">리뷰 체크포인트</span>%s</li>'%inline(b.split(":",1)[1].strip()))
            else: out.append('<li>%s</li>'%inline(b))
            i=j; continue
        if l.startswith('> '):
            close_ul(); out.append('<blockquote>%s</blockquote>'%inline(l[2:])); i+=1; continue
        if not l.strip(): close_ul(); i+=1; continue
        close_ul(); para=[l]; j=i+1
        while j<len(L) and L[j].strip() and not re.match(r'^(#|\||- |> |```|\s*- )', L[j]): para.append(L[j]); j+=1
        out.append('<p>%s</p>'%inline(' '.join(x.strip() for x in para))); i=j
    close_ul()
    if incode: out.append('</code></pre>')
    return '\n'.join(out)

DOCS=[('common.md','공통','전 모듈 규칙'), ('build-link.md','빌드·링크 구성','모듈 횡단'),
      ('cross.md','모듈 경계','cross'), ('measurement.md','측정 방법론','성능 검증 필수')]
ORDER=['src-base','src-storage','src-transaction','src-query','src-xasl','src-optimizer','src-parser',
       'src-compat','src-object','src-executables','src-loaddb','src-method','src-sp','pl_engine',
       'src-broker','src-connection','src-communication','src-thread','src-monitor','unit_tests']

def mod_meta(md):
    name=md.split('\n')[0].lstrip('# ').strip()
    sec2=md.split('## 2.')[1].split('## 3.')[0] if '## 2.' in md and '## 3.' in md else ''
    acc=len(re.findall(r'^### ', sec2, re.M))
    iss=0
    if '## 3. 예비 이슈 사항' in md:
        iss=len(re.findall(r'^- (?!\(현재)', md.split('## 3. 예비 이슈 사항')[1], re.M))
    return name, acc, iss

pages=[]   # (fname, title, kind, acc, iss, srcmd)
for fn,t,d in DOCS: pages.append((fn[:-3]+'.html', t, 'doc', 0, 0, fn))
mods=sorted(os.listdir('modules'), key=lambda f: ORDER.index(f[:-3]) if f[:-3] in ORDER else 99)
for fn in mods:
    md=open('modules/'+fn).read()
    name,acc,iss=mod_meta(md)
    pages.append((fn[:-3]+'.html', name, 'mod', acc, iss, 'modules/'+fn))

def sidebar(current):
    li=['<li><a href="index.html"%s>개요</a></li>'%(' class="cur"' if current=='index.html' else '')]
    li.append('<li class="grp">공통 문서</li>')
    for f,t,k,acc,iss,_ in pages:
        if k!='doc': continue
        li.append('<li><a href="%s"%s>%s</a></li>'%(f, ' class="cur"' if f==current else '', html.escape(t)))
    li.append('<li class="grp">모듈</li>')
    for f,t,k,acc,iss,_ in pages:
        if k!='mod': continue
        badges=(('<span class="cnt">%d</span>'%acc) if acc else '')+(('<span class="iss">⚠%d</span>'%iss) if iss else '')
        li.append('<li><a href="%s"%s><span>%s</span><span class="bd">%s</span></a></li>'%(f, ' class="cur"' if f==current else '', html.escape(t), badges))
    return '<ul>'+'\n'.join(li)+'</ul>'

def shell(current, title, inner, lede=''):
    return """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s — CUBRID 소스 노트</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@500;700;800&family=Noto+Sans+KR:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
<link rel="stylesheet" href="style.css"></head><body>
<div class="shell">
<header class="top"><a class="home" href="index.html">CUBRID 소스 노트</a>
<span class="meta">upstream/develop 95b79e7ed · git: soheejung-cs/cubrid-source-notes</span></header>
<div class="layout">
<nav class="rail" aria-label="목차">
<input id="q" type="search" placeholder="이 페이지에서 검색" aria-label="검색">
%s
</nav>
<main>
<h1>%s</h1>%s
%s
</main></div></div>
<script>
(function(){var q=document.getElementById('q');if(!q)return;
var items=[].slice.call(document.querySelectorAll('main h3, main h4, main li, main p'));var t;
q.addEventListener('input',function(){clearTimeout(t);t=setTimeout(function(){
var v=q.value.trim().toLowerCase();
if(!v){items.forEach(function(e){e.classList.remove('hidden')});return}
items.forEach(function(e){e.classList.toggle('hidden',e.textContent.toLowerCase().indexOf(v)<0)});},120);});
})();
</script></body></html>"""%(html.escape(title), sidebar(current), html.escape(title),
    ('<p class="lede">%s</p>'%lede if lede else ''), inner)

CSS="""
:root{
  --bg:#F2F3F1; --panel:#FFFFFF; --ink:#1C242C; --muted:#5E6B74; --line:#D9DEE1;
  --accent:#33608C; --accent-ink:#2A4F73;
  --ck:#155E42; --ck-bg:#EDF6F1; --ck-line:#BFDCCB;
  --warn:#8A4B00; --warn-bg:#FBF2E4;
  --code-bg:#ECEFF1; --code-ink:#31556E;
  --c50:#0E6B6F; --c50bg:#E4F2F1; --c51:#33608C; --c51bg:#E8EEF6; --c52:#6B4E9E; --c52bg:#EFEAF7;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#12171C; --panel:#1A2129; --ink:#DAE2E8; --muted:#8A97A1; --line:#2A333C;
  --accent:#7FA9D4; --accent-ink:#9FC0E2;
  --ck:#7CC7A4; --ck-bg:#15231D; --ck-line:#25473A;
  --warn:#E0AE55; --warn-bg:#241C10;
  --code-bg:#212A33; --code-ink:#9CC1DB;
  --c50:#5FBEC2; --c50bg:#12292B; --c51:#7FA9D4; --c51bg:#182534; --c52:#B49AE0; --c52bg:#241D33;
}}
:root[data-theme="dark"]{
  --bg:#12171C; --panel:#1A2129; --ink:#DAE2E8; --muted:#8A97A1; --line:#2A333C;
  --accent:#7FA9D4; --accent-ink:#9FC0E2;
  --ck:#7CC7A4; --ck-bg:#15231D; --ck-line:#25473A;
  --warn:#E0AE55; --warn-bg:#241C10;
  --code-bg:#212A33; --code-ink:#9CC1DB;
  --c50:#5FBEC2; --c50bg:#12292B; --c51:#7FA9D4; --c51bg:#182534; --c52:#B49AE0; --c52bg:#241D33;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans KR",system-ui,sans-serif;
  font-size:15px;line-height:1.75;-webkit-font-smoothing:antialiased}
code{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:.85em;background:var(--code-bg);
  color:var(--code-ink);padding:.06em .3em;border-radius:3px;word-break:break-word}
pre{background:var(--code-bg);padding:12px 14px;border-radius:4px;overflow-x:auto;line-height:1.5}
pre code{background:none;padding:0}
a{color:var(--accent)}
h1,h2,h3,h4,h5{font-family:"Gothic A1",sans-serif;line-height:1.4;text-wrap:balance}
.shell{max-width:1280px;margin:0 auto;padding:0 22px 80px}
header.top{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 18px;
  padding:20px 0 14px;border-bottom:1px solid var(--line)}
a.home{font-family:"Gothic A1",sans-serif;font-weight:800;font-size:17px;color:var(--ink);text-decoration:none}
a.home:hover{color:var(--accent)}
.meta{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--muted)}
.layout{display:grid;grid-template-columns:1fr}
@media(min-width:960px){.layout{grid-template-columns:232px 1fr;gap:42px;align-items:start}}
nav.rail{padding-top:18px}
@media(min-width:960px){nav.rail{position:sticky;top:0;max-height:100vh;overflow-y:auto;padding:18px 0 40px}}
nav.rail ul{list-style:none;margin:0;padding:0}
nav.rail li{margin:0 0 1px}
nav.rail li.grp{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--muted);margin:14px 0 4px;padding-left:8px}
nav.rail a{display:flex;justify-content:space-between;gap:8px;text-decoration:none;color:var(--ink);
  font-size:13.5px;padding:3px 8px;border-radius:4px;border-left:2px solid transparent}
nav.rail a:hover,nav.rail a:focus-visible{background:var(--panel);color:var(--accent)}
nav.rail a.cur{background:var(--panel);border-left-color:var(--accent);font-weight:700}
.bd{display:flex;gap:5px;align-items:baseline}
.cnt{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--muted)}
.iss{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--warn)}
#q{width:100%;margin:0 0 12px;padding:7px 10px;border:1px solid var(--line);border-radius:4px;
  background:var(--panel);color:var(--ink);font:inherit;font-size:13px}
#q:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
main{min-width:0;padding-top:22px}
main h1{font-size:26px;font-weight:800;margin:0 0 6px;letter-spacing:-.01em}
.lede{color:var(--muted);max-width:70ch;margin:0 0 8px}
main h2{font-size:20px;font-weight:800;color:var(--accent-ink);border-bottom:2px solid var(--accent);
  padding-bottom:6px;margin:30px 0 10px}
main h3{font-size:16.5px;font-weight:700;margin:24px 0 8px}
main h4{font-size:15px;font-weight:700;margin:18px 0 6px}
main h5{font-size:14px;font-weight:700;margin:14px 0 4px;color:var(--muted)}
main p{margin:0 0 10px;max-width:78ch}
main ul{margin:0 0 12px;padding-left:22px;max-width:80ch}
main li{margin:4px 0}
blockquote{margin:10px 0;padding:6px 12px;border-left:3px solid var(--line);color:var(--muted);font-size:13.5px;max-width:76ch}
li.ck{list-style:none;margin:10px 0 12px -22px;padding:9px 12px;background:var(--ck-bg);
  border:1px solid var(--ck-line);border-radius:4px;font-size:13.5px}
.cklab{display:block;font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ck);margin-bottom:3px}
.chip{font-family:"JetBrains Mono",monospace;font-size:11.5px;font-weight:600;padding:.08em .45em;
  border-radius:3px;white-space:nowrap}
.chip.c50{color:var(--c50);background:var(--c50bg)}
.chip.c51{color:var(--c51);background:var(--c51bg)}
.chip.c52{color:var(--c52);background:var(--c52bg)}
.tbl{overflow-x:auto;margin:0 0 12px}
table{border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums}
th,td{border:1px solid var(--line);padding:5px 10px;text-align:left;vertical-align:top}
th{background:var(--panel);font-weight:700}
.hidden{display:none}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:12px;margin:16px 0}
.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:12px 14px;text-decoration:none;color:var(--ink)}
.card:hover{border-color:var(--accent)}
.card .nm{font-family:"JetBrains Mono",monospace;font-weight:600;font-size:14px;color:var(--accent-ink)}
.card .st{display:flex;gap:12px;margin-top:6px;font-family:"JetBrains Mono",monospace;font-size:11.5px;color:var(--muted)}
.card .st .iss{color:var(--warn)}
@media(prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""
open('site/style.css','w').write(CSS)

# 개별 페이지
for f,t,k,acc,iss,src in pages:
    md=open(src).read()
    body=md2html('\n'.join(md.split('\n')[1:]))  # 첫 줄 h1은 페이지 h1로 대체
    lede=''
    if k=='mod':
        lede='§1 목적·사용처(함수별) · §2 분석(함수별·통합) · §3 예비 이슈 · §4 진행중인 작업'+((' · ⚠ 이슈 %d건'%iss) if iss else '')
    open('site/'+f,'w').write(shell(f, t, body, lede))

# 홈(index.html): 카드 그리드
cards_doc=''.join('<a class="card" href="%s"><span class="nm">%s</span><div class="st"><span>%s</span></div></a>'%(f,html.escape(t),html.escape(d))
    for (f,t,k,acc,iss,src),(fn2,t2,d) in zip([p for p in pages if p[2]=='doc'], DOCS))
cards_mod=''.join('<a class="card" href="%s"><span class="nm">%s</span><div class="st"><span>축적 %d</span>%s</div></a>'%(
    f,html.escape(t),acc,('<span class="iss">⚠ %d</span>'%iss) if iss else '')
    for f,t,k,acc,iss,src in pages if k=='mod')
readme=open('README.md').read()
intro=md2html('\n'.join(readme.split('\n')[1:]).split('## 리포 구성')[0])
rules=md2html('## 공유 규약'+readme.split('## 공유 규약',1)[1]) if '## 공유 규약' in readme else ''
home_inner=intro+'<h2>공통 문서</h2><div class="cards">'+cards_doc+'</div><h2>모듈</h2><div class="cards">'+cards_mod+'</div>'+rules
open('site/index.html','w').write(shell('index.html','CUBRID 소스 노트',home_inner,
  'AGENTS.md 증류 + 컨테이너(.50/.51/.52) 축적 지식 — 모듈별 목적·분석·예비 이슈. git이 정본, 이 사이트는 웹 뷰.'))
print("생성:", sorted(os.listdir('site'))[:6], "... 총", len(os.listdir('site')), "파일")
