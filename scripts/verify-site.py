"""Check POLS pages against centralized records and local deployment paths."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json, re, sys

ROOT=Path(__file__).resolve().parents[1]
SHARED=ROOT.parent/'css-shared'
OUT=ROOT/'_site'
prefix=sys.argv[1].rstrip('/') if len(sys.argv)>1 else ''
class Scan(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.urls=[];self.h1=0;self.description=False
    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        if t=='h1':self.h1+=1
        if a.get('id'):self.ids.append(a['id'])
        if t=='meta' and a.get('name')=='description' and a.get('content'):self.description=True
        if t in ['a','img','link','script','iframe']:
            v=a.get('href') if t in ['a','link'] else a.get('src')
            if v:self.urls.append(v)
pages={}
for f in OUT.rglob('*.html'):
    p=Scan();p.feed(f.read_text());pages[f]=p
errors=[]
unit=SHARED/'src/data/units/pols'
faculty=json.loads((unit/'faculty.json').read_text())
students=json.loads((unit/'graduate-students.json').read_text())
heroes=json.loads((unit/'heroes.json').read_text())['pages']
heroes.update(json.loads((unit/'faculty-heroes.json').read_text())['pages'])
for f,p in pages.items():
    rel=f.relative_to(OUT);raw=f.read_text()
    url='/' if str(rel)=='index.html' else '/'+str(rel).removesuffix('index.html') if rel.name=='index.html' else '/'+str(rel)
    if p.h1!=1:errors.append(str(rel)+': H1 count')
    if not p.description:errors.append(str(rel)+': missing description')
    if len(p.ids)!=len(set(p.ids)):errors.append(str(rel)+': duplicate IDs')
    if url not in heroes or heroes[url]['image'] not in raw:errors.append(str(rel)+': missing assigned hero')
    if any(x in raw for x in ['{{','{%','Profile coming soon','logo-google-scholar','logo-research-gate']):errors.append(str(rel)+': leftover template or imported logo')
    for v in p.urls:
        u=urlsplit(v)
        if u.scheme or u.netloc:continue
        path=unquote(u.path)
        if prefix and path.startswith('/'):
            if not path.startswith(prefix+'/'):errors.append(str(rel)+': missing prefix '+v);continue
            path=path[len(prefix):]
        target=OUT/path.lstrip('/') if path.startswith('/') else f.parent/path if path else f
        if target.is_dir():target=target/'index.html'
        if not target.exists():errors.append(str(rel)+': missing '+v)
        elif u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:errors.append(str(rel)+': missing anchor '+v)
for person in faculty:
    f=OUT/person['url'].lstrip('/');raw=f.read_text()
    if 'profile-sidebar' not in raw or 'profile-biography' not in raw:errors.append(person['name']+': missing shared profile')
    if person['photo'] not in raw:errors.append(person['name']+': missing temporary portrait')
    if not (SHARED/'src'/person['photo'].lstrip('/')).exists():errors.append(person['name']+': missing source portrait')
cohort=(OUT/'graduate/current-cohort.html').read_text()
if cohort.count(' graduate-student"')!=len(students):errors.append('Cohort record count')
for student in students:
    if student['name'] not in cohort:errors.append('Missing student '+student['name'])
    for advisor in student['advisors']:
        if advisor.get('url') and not (OUT/advisor['url'].lstrip('/')).exists():errors.append('Missing advisor '+advisor['name'])
if len(pages)!=51 or len(faculty)!=18 or len(students)!=27:errors.append('Unexpected page/record count')
if errors:print('\n'.join(errors));sys.exit(1)
print(f'Checked {len(pages)} pages, {len(faculty)} faculty, {len(students)} students, links, assets, anchors, metadata and heroes. Prefix: {prefix or "/"}.')
