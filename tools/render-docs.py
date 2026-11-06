#!/usr/bin/env python3
"""Export repository Markdown to matching offline HTML under htmls/.

Usage: tools/render-docs.py README.md docs/report.md codex_handoff/CURRENT_STATE.md
Existing manually authored HTML beside Markdown is never overwritten.
"""
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import argparse,hashlib,html,os,re
import markdown

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'htmls'
STYLE='''body{max-width:1100px;margin:36px auto;padding:0 22px;color:#24313d;
font:17px/1.65 system-ui,sans-serif;background:#f8fafc}article{background:white;padding:28px}
h1,h2,h3{line-height:1.25}a{color:#175b91}img{max-width:100%;height:auto}
table{border-collapse:collapse;width:100%;margin:20px 0}td,th{padding:10px;border:1px solid #ccd5df;
vertical-align:top}th{background:#edf2f7;text-align:left}pre{overflow:auto;padding:15px;background:#edf2f7}
code{font:0.9em ui-monospace,monospace;overflow-wrap:anywhere}footer{font-size:13px;color:#586979}
@media(max-width:700px){body{margin:12px auto}article{padding:12px}table{display:block;overflow:auto}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('files',nargs='+',type=Path)
    a=p.parse_args();sources=[f.resolve() for f in a.files]
    for f in sources:
        assert f.is_relative_to(ROOT) and f.suffix=='.md',f
    outputs={f:OUT/f.relative_to(ROOT).with_suffix('.html') for f in sources}
    for source,target in outputs.items():
        text=source.read_text();body=markdown.markdown(text,extensions=['tables','fenced_code','sane_lists','toc'])
        def link(match):
            attr,raw=match.groups();parts=urlsplit(html.unescape(raw))
            if parts.scheme or parts.netloc or not parts.path:return match.group(0)
            dest=(source.parent/parts.path).resolve()
            if dest in outputs:dest=outputs[dest]
            elif dest.is_relative_to(ROOT) and (OUT/dest.relative_to(ROOT).with_suffix('.html')).is_file() and dest.suffix=='.md':
                dest=OUT/dest.relative_to(ROOT).with_suffix('.html')
            value=urlunsplit(('', '',Path(os.path.relpath(dest,target.parent)).as_posix(),parts.query,parts.fragment))
            return attr+'="'+html.escape(value,quote=True)+'"'
        body=re.sub(r'(href|src)="([^\"]+)"',link,body)
        title=next((s[2:] for s in text.splitlines() if s.startswith('# ')),source.stem)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="{digest}">'
            f'<title>{html.escape(title)}</title><style>{STYLE}</style></head><body><article>{body}</article>'
            f'<footer>Generated from {html.escape(str(source.relative_to(ROOT)))}. Source SHA256: {digest}.</footer></body></html>\n')
        print(target.relative_to(ROOT))

if __name__=='__main__':main()
