# src/utils.py
import os, json, random, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data') if os.path.basename(BASE_DIR).lower() == 'src' else os.path.join(BASE_DIR, 'data')
SOAL_FILE = os.path.join(DATA_DIR, 'soal.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        save_json(HISTORY_FILE, [])

def load_json(path, default=None):
    if default is None: default = []
    if not os.path.exists(path): return default
    with open(path, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_all_items():
    ensure_dirs()
    return load_json(SOAL_FILE, default=[])

def list_packages_from_soal():
    items = load_all_items()
    pkgs = set()
    for it in items:
        p = str(it.get('package','')).strip()
        if p: pkgs.add(p.upper())
    return sorted(pkgs)

def load_questions_for_package(pkg_name):
    items = load_all_items()
    if not pkg_name:
        return [it.copy() for it in items if it.get('question') or it.get('choices') or it.get('reading')]
    target = str(pkg_name).strip().lower()
    questions = []
    for it in items:
        p = str(it.get('package','')).strip().lower()
        if p == target and (it.get('question') or it.get('choices') or it.get('reading')):
            questions.append(it.copy())
    if not questions:
        for it in items:
            p = str(it.get('package','')).strip().lower()
            if target in p and (it.get('question') or it.get('choices') or it.get('reading')):
                questions.append(it.copy())
    return questions

def normalize_correct_answer(db):
    for q in db:
        ca = q.get('correct_answer')
        choices = q.get('choices') or []
        if isinstance(ca,int): continue
        if isinstance(ca,str):
            s = ca.strip()
            if len(s)==1 and s.isalpha():
                idx = ord(s.upper())-ord('A')
                if 0<=idx<len(choices): q['correct_answer']=idx; continue
            try: q['correct_answer']=choices.index(s); continue
            except Exception:
                lowered=[str(c).strip().lower() for c in choices]
                try: q['correct_answer']=lowered.index(s.lower()); continue
                except Exception: pass
    return db

def used_ids_for_package(history, package):
    target=(package or '').strip().lower()
    used=set()
    for s in history:
        if str(s.get('package','')).strip().lower()==target:
            for qid in s.get('all_ids',[]): used.add(qid)
    return used

def pick_questions_with_fresh_priority(db,n,history,package,level='all'):
    level=(level or 'all').strip().lower()
    pool=[q for q in db if (level=='all' or not q.get('level') or str(q.get('level','')).strip().lower()==level)]
    used=used_ids_for_package(history,package)
    fresh=[q for q in pool if q.get('id') not in used]
    rng=random.SystemRandom()
    if len(fresh)>=n: selected=rng.sample(fresh,k=n)
    else:
        selected=list(fresh)
        remaining=[q for q in pool if q.get('id') not in {x.get('id') for x in selected}]
        if remaining: selected.extend(rng.sample(remaining,k=min(n-len(selected),len(remaining))))
    rng.shuffle(selected)
    return selected

def pick_daily_challenge_by_level(db,package,level='all',count=1):
    level=(level or 'all').strip().lower()
    pool=[q for q in db if (level=='all' or not q.get('level') or str(q.get('level','')).strip().lower()==level)]
    if not pool: return []
    today=datetime.date.today().isoformat()
    seed_str=f"{today}::{package}::{level}"
    seed=abs(hash(seed_str))%(2**32)
    rng=random.Random(seed)
    selected=rng.sample(pool,k=min(count,len(pool)))
    rng.shuffle(selected)
    return selected