# -*- coding: utf-8 -*-
"""Erzeugt den Evidenz-Browser als einzelne HTML-Datei.

Aufruf: python3 -I build.py <Evidenzdatenbank.json> <template.html> <Ausgabe.html> [codenamen.json] [Ordner mit Zulieferung 1 bis 5 als CSV]
Die Datenbank wird nur gelesen. In die Ausgabe geht ein schlanker Auszug ohne Herkunfts- und Prüfketten.
"""
import json, sys, datetime, csv, glob, os, re, collections

src, tpl, out = sys.argv[1:4]
names = json.load(open(sys.argv[4], encoding='utf-8')) if len(sys.argv) > 4 else {}
j = json.load(open(src, encoding='utf-8'))
E = j['evidenzeinheiten']
M = j['metadaten']
order = {'Etabliert': 0, 'Experte': 1, 'AI-First': 2}
faelle = sorted({(e['fall_id'], e['interview_id'], e['fallgruppe']) for e in E}, key=lambda x: (order[x[2]], x[0]))
codes = sorted({c['code_id'] for e in E for c in e['codes']})
ff = sorted({f for e in E for f in (e['forschungsfragen'] or [])})
fidx = {f[0]: i for i, f in enumerate(faelle)}
rows = []
for e in sorted(E, key=lambda e: (fidx[e['fall_id']], e['evidenz_id'])):
    assert e['datensatzstatus'] == 'aktiv'
    rows.append({
        'id': e['evidenz_id'], 'i': e['interview_id'], 'f': e['fall_id'], 'g': e['fallgruppe'],
        'p': e['aussage_paraphrase'], 't': e['interpretation'],
        'c': [[c['code_id'], c.get('auspraegung') or ''] for c in e['codes']],
        'a': [a for q in e['quellen'] for a in (q.get('absatz_ids') or [])],
        'u': e['unsicherheiten'] or [], 'x': e['gegenbelege'] or [], 'ff': e['forschungsfragen'] or [],
    })

# ---------- Zulieferung des Autorenteams: Aussagen, Begründungen, Kodierbuch, Massnahmen
aus, mas, kb = [], [], {}
if len(sys.argv) > 5:
    zd = sys.argv[5]
    def rd(n):
        return list(csv.DictReader(open(glob.glob(os.path.join(zd, '*%d_*.csv' % n))[0], encoding='utf-8-sig')))
    A, B, C, MS, PR = (rd(i) for i in range(1, 6))
    units = collections.defaultdict(list)
    for r in rows:
        for a in r['a']:
            units[a].append(r['id'])
    cover = json.dumps(j['fallabdeckung'], ensure_ascii=False)
    def norm(x):
        m = re.match(r'ID (\d{2}) P(\d{4})$', x.strip()); assert m, x
        return 'ID-%s-P%s' % m.groups()
    SN = {'Evidenzeinheit': 0, 'Nachbarabsatz hat Evidenzeinheit': 1, 'nur Indikator oder Abdeckung': 2, 'nicht in der Datenbank': 3}
    geliefert = {norm(r['Belegstelle']): SN[r['Status in Evidenzdatenbank L002']] for r in PR}
    def nachbarn(k, w):
        i, n = k[:5], int(k[-4:])
        return sorted({u for o in range(-w, w + 1) if o for u in units.get('%s-P%04d' % (i, n + o), [])})
    def status(k):
        """0 Evidenzeinheit, 1 Nachbarabsatz, 2 ohne aktive Evidenzeinheit, 3 nicht in der Datenbank. Massgeblich ist die Prüfung des Autorenteams, wo sie vorliegt."""
        if k in units: return 0, units[k]
        st = geliefert.get(k)
        if st is None:
            st = 1 if nachbarn(k, 1) else (2 if k in cover else 3)
            print('  nicht in Datei 5, selbst eingestuft:', k, st)
        if st == 1:
            nb = nachbarn(k, 1) or nachbarn(k, 2)
            assert nb, k
            return 1, nb
        return st, []
    for k, st in geliefert.items():
        assert (st == 0) == (k in units), k
    print('Nachbarabsätze laut Zulieferung:', sum(1 for v in geliefert.values() if v == 1), '| davon direkt angrenzend:', sum(1 for k, v in geliefert.items() if v == 1 and nachbarn(k, 1)))
    def refs(cell, rolle=0):
        out = []
        for x in filter(None, (y.strip() for y in cell.split(';'))):
            k = norm(x); st, ids = status(k)
            out.append([k, st, ids, rolle])
        return out
    beg = {r['Aussage']: r for r in B}
    for r in A:
        k = r['Aussage']; rolle = {'stützt': 0, 'schränkt ein': 1}[r['Rolle']]
        cur = next((a for a in aus if a['k'] == k), None)
        if not cur:
            cur = {'k': k, 'w': beg[k]['Wortlaut'], 'b': beg[k]['Begründung'], 'r': []}; aus.append(cur)
        cur['r'] += refs(r['Belegstellen'], rolle)
    assert len(aus) == 18 and set(beg) == {a['k'] for a in aus}
    for r in MS:
        mas.append({'m': r['Massnahme'], 'p': [x.strip() for x in r['Prinzip'].split(',')], 'h': r['Hinweis'], 'r': refs(r['Belegstellen'])})
    kb = {r['Kürzel']: {'n': r['Name'], 'b': r['Bereich'], 'd': r['Definition'], 'a': r['Ausprägungen']} for r in C}
    assert set(kb) == set(codes), set(kb) ^ set(codes)
    names = {k: v['n'] for k, v in kb.items()}
    allr = [x for a in aus for x in a['r']] + [x for m in mas for x in m['r']]
    print(len(aus), 'Aussagen,', len(mas), 'Massnahmen,', len(allr), 'Verweise; Status', dict(collections.Counter(x[1] for x in allr)))
erstellt = datetime.datetime.fromisoformat(M['erstellt_am'].replace('Z', '+00:00')).strftime('%d.%m.%Y')
grenzen = [
    'Die Paraphrasen stammen aus geglätteten Kodierfassungen. Es sind keine audioverifizierten Zitate.',
    'Jedes Gespräch wurde in zwei getrennten Läufen mit KI-Unterstützung kodiert und danach konsolidiert. Die beiden Läufe sind zwei Lesarten desselben Gesprächs, keine unabhängigen Quellen.',
    'Die Konsolidierung ist je Gespräch von einem Mitglied des Autorenteams freigegeben. Nicht jede einzelne Einheit ist einzeln von einem Menschen geprüft.',
    'Eine Reliabilitätskennzahl ist nicht berechnet.',
    'Die Zahl der Einheiten je Code ist kein Mass für das Gewicht eines Befunds. Die Arbeit gewichtet nach Relevanz und Kontrast.',
]
data = {
    'stand': f"{M['datenstand']} vom {erstellt}, Schema {M['schema_version']}, Kodierbuch {M['methodenstand']['kodierbuch']}",
    'faelle': [{'f': f, 'i': i, 'g': g} for f, i, g in faelle], 'codes': codes, 'codenamen': names, 'ff': ff,
    'grenzen': grenzen, 'e': rows, 'aus': aus, 'mas': mas, 'kb': kb,
}

# ---------- Auszug für die Belegansicht des Leitfadens (evidenz/belege.js)
if len(sys.argv) > 6 and aus:
    byid = {r['id']: r for r in rows}
    GNAME = {'Etabliert': 'Etablierte Unternehmen', 'Experte': 'Experten', 'AI-First': 'AI-First Firms'}
    igr = {f[1]: f[2] for f in faelle}
    def pick(refs, n):
        cand = []
        for x in refs:
            if x[1] != 0: continue
            for u in x[2]:
                r = byid[u]
                if r in cand or len(r['p']) > 340 or re.search(r'ungeprüfte Zuordnung|Originalstelle|vorgeschlagen|ß|–|—', r['p']): continue
                cand.append(r)
        out = []
        for key in ('g', 'i', 'id'):          # zuerst je Gruppe eine, dann je Gespräch, dann auffüllen
            for r in cand:
                if len(out) < n and r not in out and all(r[key] != o[key] for o in out): out.append(r)
        return [{'f': r['f'], 'g': GNAME[r['g']], 't': r['p']} for r in out]
    bel = {}
    for a in aus:
        st = [x for x in a['r'] if not x[3]]; ein = [x for x in a['r'] if x[3]]
        ids = sorted({x[0][:5] for x in st})
        bel[a['k']] = {'w': a['w'], 'b': a['b'], 'n': len(st), 'i': len(ids), 'u': sum(1 for x in st if x[1] == 0),
                       'gr': [GNAME[g] for g in ('Etabliert', 'Experte', 'AI-First') if g in {igr[i] for i in ids}],
                       'e': len(ein), 'p': pick(st, 3), 'x': pick(ein, 1)}
    js = 'window.RF_BELEGE=' + json.dumps({'stand': data['stand'], 'aus': bel}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';\n'
    open(sys.argv[6], 'w', encoding='utf-8').write(js)
    print('Belegansicht:', len(bel), 'Aussagen,', sum(len(v['p']) + len(v['x']) for v in bel.values()), 'Paraphrasen,', len(js), 'Zeichen; ohne Paraphrase:', [k for k, v in bel.items() if not v['p']])
blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
html = open(tpl, encoding='utf-8').read()
assert html.count('/*DATA*/null') == 1
open(out, 'w', encoding='utf-8').write(html.replace('/*DATA*/null', blob))
print(len(rows), 'Einheiten,', len(faelle), 'Fälle,', len(codes), 'Codes,', sum(len(r['c']) for r in rows), 'Zuordnungen;', len(html) + len(blob), 'Zeichen')
