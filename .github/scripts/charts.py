"""Gera assets/contributions.svg e assets/evolution.svg na paleta do perfil.
Sem dependências externas: usa só a biblioteca padrão do Python."""
import os, re, json, datetime as dt, urllib.request

USER = os.environ.get("GH_USER", "vinic8")
OUT = os.environ.get("OUT_DIR", "assets")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
C = dict(bg="#16191e", border="#2b3038", text="#e6e9ed", muted="#8b939d", cyan="#5ce1e6")
LEVELS = ["#1f2329", "#134e52", "#1f7f84", "#33b3b8", "#5ce1e6"]
FONT = "font-family=\"'Segoe UI', Helvetica, Arial, sans-serif\""

def get(url, api=False):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-charts"})
    if api and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

# ---------- dados ----------
html = get(f"https://github.com/users/{USER}/contributions")
days = {}
for m in re.finditer(r'<td[^>]*data-date="([\d-]+)"[^>]*id="([^"]+)"[^>]*data-level="(\d)"', html):
    days[m.group(2)] = [dt.date.fromisoformat(m.group(1)), int(m.group(3)), 0]
for m in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
    if m.group(1) in days:
        n = re.match(r"(\d+)", m.group(2))
        days[m.group(1)][2] = int(n.group(1)) if n else 0
cal = sorted(days.values())
if not cal:
    raise SystemExit("Nenhum dado de contribuição encontrado")
total = sum(c for _, _, c in cal)

try:
    repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100", api=True))
    created = sorted(dt.date.fromisoformat(r["created_at"][:10]) for r in repos if not r.get("fork"))
except Exception as e:
    print("Aviso: sem dados de repositórios:", e)
    created = []

# ---------- gráfico de contribuições (estilo do padrão do GitHub) ----------
cell, gap, left, top = 11, 3, 44, 58
start = cal[0][0] - dt.timedelta(days=(cal[0][0].weekday() + 1) % 7)
rects, month_labels, last_month = [], [], None
for d, lvl, cnt in cal:
    col, row = (d - start).days // 7, (d.weekday() + 1) % 7
    x, y = left + col * (cell + gap), top + row * (cell + gap)
    rects.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[lvl]}"><title>{cnt} em {d:%d/%m/%Y}</title></rect>')
    if row == 0 and d.month != last_month and d.day <= 7:
        month_labels.append(f'<text x="{x}" y="{top - 8}" font-size="11" fill="{C["muted"]}" {FONT}>{MESES[d.month - 1]}</text>')
        last_month = d.month
ncols = (cal[-1][0] - start).days // 7 + 1
W = left + ncols * (cell + gap) + 20
H = top + 7 * (cell + gap) + 40
wd = "".join(f'<text x="{left - 8}" y="{top + r * (cell + gap) + 9}" text-anchor="end" font-size="10" fill="{C["muted"]}" {FONT}>{t}</text>'
             for r, t in ((1, "Seg"), (3, "Qua"), (5, "Sex")))
lx = W - 20 - 5 * (cell + 3) - 40
legend = (f'<text x="{lx - 8}" y="{H - 17}" text-anchor="end" font-size="10" fill="{C["muted"]}" {FONT}>Menos</text>'
          + "".join(f'<rect x="{lx + i * (cell + 3)}" y="{H - 26}" width="{cell}" height="{cell}" rx="2.5" fill="{c}"/>' for i, c in enumerate(LEVELS))
          + f'<text x="{lx + 5 * (cell + 3) + 4}" y="{H - 17}" font-size="10" fill="{C["muted"]}" {FONT}>Mais</text>')
contrib = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{C["bg"]}" stroke="{C["border"]}"/>
<text x="20" y="28" font-size="14" font-weight="600" fill="{C["text"]}" {FONT}>{total} contribuições no último ano</text>
{"".join(month_labels)}{wd}{"".join(rects)}{legend}
</svg>'''
open(f"{OUT}/contributions.svg", "w", encoding="utf-8").write(contrib)

# ---------- linha de evolução (contribuições acumuladas por semana) ----------
weeks = {}
for d, _, cnt in cal:
    wk = start + dt.timedelta(days=((d - start).days // 7) * 7)
    weeks[wk] = weeks.get(wk, 0) + cnt
wk_list = sorted(weeks)
acc, s = [], 0
for w in wk_list:
    s += weeks[w]; acc.append(s)
EW, EH, pl, pr, pt, pb = W, 230, 50, 24, 54, 38
iw, ih = EW - pl - pr, EH - pt - pb
mx = max(acc[-1], 1)
X = lambda i: pl + iw * i / max(len(wk_list) - 1, 1)
Y = lambda v: pt + ih - ih * v / mx
pts = [(X(i), Y(v)) for i, v in enumerate(acc)]
line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
area = line + f" L{pts[-1][0]:.1f},{pt + ih} L{pts[0][0]:.1f},{pt + ih} Z"
grid = "".join(f'<line x1="{pl}" x2="{EW - pr}" y1="{Y(mx * k / 4):.1f}" y2="{Y(mx * k / 4):.1f}" stroke="{C["border"]}" stroke-dasharray="3 5"/>'
               f'<text x="{pl - 8}" y="{Y(mx * k / 4) + 4:.1f}" text-anchor="end" font-size="10" fill="{C["muted"]}" {FONT}>{round(mx * k / 4)}</text>'
               for k in range(5))
xl, lm = [], None
for i, w in enumerate(wk_list):
    if w.month != lm and w.day <= 7:
        xl.append(f'<text x="{X(i):.1f}" y="{EH - 14}" text-anchor="middle" font-size="10" fill="{C["muted"]}" {FONT}>{MESES[w.month - 1]}</text>')
        lm = w.month
marks = []
for c in created:
    if c < wk_list[0]:
        continue
    i = min(range(len(wk_list)), key=lambda j: abs((wk_list[j] - c).days))
    marks.append(f'<circle cx="{pts[i][0]:.1f}" cy="{pts[i][1]:.1f}" r="4.5" fill="{C["bg"]}" stroke="{C["cyan"]}" stroke-width="2"><title>Novo repositório em {c:%d/%m/%Y}</title></circle>')
evo = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {EW} {EH}" width="{EW}" height="{EH}">
<defs><linearGradient id="a" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity=".35"/><stop offset="1" stop-color="{C["cyan"]}" stop-opacity="0"/></linearGradient></defs>
<rect x="1" y="1" width="{EW - 2}" height="{EH - 2}" rx="12" fill="{C["bg"]}" stroke="{C["border"]}"/>
<text x="20" y="28" font-size="14" font-weight="600" fill="{C["text"]}" {FONT}>Evolução dos projetos</text>
<circle cx="{EW - 150}" cy="24" r="4" fill="{C["bg"]}" stroke="{C["cyan"]}" stroke-width="2"/>
<text x="{EW - 140}" y="28" font-size="11" fill="{C["muted"]}" {FONT}>novo repositório</text>
<text x="20" y="44" font-size="11" fill="{C["muted"]}" {FONT}>contribuições acumuladas por semana</text>
{grid}{"".join(xl)}
<path d="{area}" fill="url(#a)"/>
<path d="{line}" fill="none" stroke="{C["cyan"]}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
{"".join(marks)}
</svg>'''
open(f"{OUT}/evolution.svg", "w", encoding="utf-8").write(evo)
print(f"ok: {total} contribuições, {len(created)} repositórios")
