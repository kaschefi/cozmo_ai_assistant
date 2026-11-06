
import re, glob
for p in sorted(glob.glob('docs/images/diagram*.svg')):
    with open(p, 'r', encoding='utf-8') as f:
        s = f.read(1500)
    m = re.search(r'<svg[^>]+>', s)
    print(p, m.group(0)[:120] if m else 'No svg tag')
