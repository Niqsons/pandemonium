#!/usr/bin/env python3
"""Сборка серии «Пандемониума»: текстовый исходник -> один html-файл.

Разметка исходника:
  TITLE / NUMBER / EMBLEM   шапка до первой пустой строки
  COLD: 1                   в шапке: насколько остыл Архив — сцена «Внизу» холоднее (с С5)
  пустая строка             граница абзаца
  ***                       смена сцены
  >>> Подпись               сцена «внизу», до <<< или до конца
  >>> Город · 19:12 · Садовая, 9 · датчик
                            вставка о мире до <<<: вместо заголовка штамп «Фосфора»;
                            последнее поле «нет данных» — место, где датчиков нет
  >[метка] текст            голос из телефона и т. п.
  >> текст                  лист-воспоминание (сгорает, когда его дочитали)
  >log[метка]               тетрадный лист; каждая следующая строка — запись
  >notice[метка] текст      уведомление на телефоне
  >notice.prompt[метка]     окно с кнопками: последняя строка «[Позже] [Принимаю]»
  >doc[метка]               документ; строка «✎ …» — от руки, «…: ____» — пустая строка подписи,
                            «· …» — мелкий шрифт
  >doc.cold[метка]          тот же документ, но холодный — договор без подписи
  *текст*                   курсив; абзац целиком в звёздочках — крупная реплика
  __слово__                 двойное подчёркивание (в журнале)
  {fox}                     знак лисьего алфавита; {paper+} — «много», {speak^} — прошедшее время
  абзац из одних знаков     написанное пальцем: крупно, по центру
  [[mirror: a b / c d]]     знаки на запотевшем зеркале (рисуются при прокрутке)
  [[mirror-hot: a]]         то же на раскалённом стекле
  [[mirror-below: a b]]     то же стекло, вид снизу: зеркально и огнём
  "СЛОВО" внутри [[mirror…]] буквы, выведенные пальцем
  [[tape: 9:41 10:26]]      кусок ленты самописца с «почерком» между отметками
  [[smokemap]]              карта дыма «Фосфора»: зелёные датчики и одна оранжевая вспышка
  [[smokemap: 14]]          та же карта, но вспышек столько, сколько указано
  [[sator]]                 квадрат SATOR на чугунной печной заслонке
"""
import html
import math
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NBSP = " "
THIN = " "

FOX = "M5 3 L9 9 L15 9 L19 3 L20.5 11.5 L12 20.5 L3.5 11.5 Z"


def ring(cx, cy, r):
    return f"M{cx - r:g} {cy:g} a{r:g} {r:g} 0 1 0 {2 * r:g} 0 a{r:g} {r:g} 0 1 0 {-2 * r:g} 0"


def oval(cx, cy, rx, ry):
    return f"M{cx - rx:g} {cy:g} a{rx:g} {ry:g} 0 1 0 {2 * rx:g} 0 a{rx:g} {ry:g} 0 1 0 {-2 * rx:g} 0"


def stroke(d):
    return f'<path pathLength="1" d="{d}"/>'


def dot(cx, cy, r):
    return f'<circle class="dot" cx="{cx:g}" cy="{cy:g}" r="{r:g}"/>'


WAVES = " ".join(f"M4 {y} Q6 {y - 2} 8 {y} T12 {y} T16 {y} T20 {y}" for y in (8, 12, 16))

# Лисий алфавит: имя -> (подпись для экранного диктора, рисунок 24×24).
# Рисунки держим в полосе y 2.5–20.5: снизу остаётся место для «много», сверху — для черты прошлого.
GLYPHS = {
    # С1
    "fox": ("лисёнок", stroke(FOX) + dot(9.4, 13, 1.05) + dot(14.6, 13, 1.05)),
    "papa": ("лис в очках", stroke(FOX) + stroke(ring(9.3, 13, 2.2)) + stroke(ring(14.7, 13, 2.2))
             + stroke("M11.5 13 L12.5 13")),
    "bird": ("птица", stroke("M3 11.5 Q7.5 6.5 12 12.5 Q16.5 6.5 21 11.5")),
    "here": ("здесь", stroke(ring(12, 12, 7.5)) + dot(12, 12, 1.7)),
    "no": ("не", stroke("M6 6 L18 18 M18 6 L6 18")),
    "speak": ("говорить", stroke(WAVES)),
    # С2
    "fire": ("огонь", stroke("M12 3 C13 6.4 16.3 8.2 16.9 12.1 C17.5 16.2 15 19.2 12 19.2 "
                             "C8.6 19.2 6.4 16.6 6.9 13.2 C7.2 11.3 8.3 10.2 9.3 9.6 "
                             "C9.2 11.4 9.9 12.6 11 13.1 C10.2 9.8 10.9 6.2 12 3 Z")
             + stroke("M12.3 13 C13.6 14.2 14.3 15.5 13.9 16.7 C13.5 17.8 11.2 17.9 10.8 16.6 "
                      "C10.5 15.4 11.3 14.1 12.3 13 Z")),
    "house": ("дом", stroke("M4.5 11.4 L12 4.4 L19.5 11.4") + stroke("M6.8 9.3 V19.2 H17.2 V9.3")
              + stroke("M10.3 19.2 V14.6 H13.7 V19.2")),
    "paper": ("бумага", stroke("M6.6 3.4 H13.6 L17.6 7.4 V19 H6.6 Z") + stroke("M13.6 3.4 V7.4 H17.6")
              + stroke("M9.3 11.2 H14.9 M9.3 14.4 H14.9")),
    "why": ("почему", stroke("M7.8 8.2 C7.2 4.8 9.8 2.9 12.5 2.9 C15.4 2.9 17.3 4.8 17.3 7.4 "
                             "C17.3 10.6 13.4 11.3 12.9 14.3 L12.8 15.6")
            + stroke("M7.8 8.2 L5.9 7.5 M7.8 8.2 L6.6 9.9") + dot(12.8, 19, 1.55)),
    "lake": ("озеро", stroke(oval(12, 13, 8.6, 5.2)) + stroke("M8 13.3 Q10 11.4 12 13.3 T16 13.3")),
    "frog": ("лягушка", stroke(ring(8.1, 7.9, 2.5)) + stroke(ring(15.9, 7.9, 2.5))
             + dot(8.1, 8.1, 0.95) + dot(15.9, 8.1, 0.95)
             + stroke("M5.8 9.9 C3.4 12.6 4.3 18.1 12 18.3 C19.7 18.1 20.6 12.6 18.2 9.9")
             + stroke("M8.4 13.4 Q12 16.4 15.6 13.4")),
    "remember": ("помнить", stroke("M3.6 18.4 C6.8 17.2 8.9 15.1 9.6 12.4 C10.4 9.4 13.7 8.3 15.4 10.3 "
                                   "C17 12.2 15.3 15.1 12.6 14.7 C10 14.3 9.8 10.7 12.6 8.3 "
                                   "C14.6 6.6 17.6 5.6 20.4 5.8")),
    "eat": ("есть", stroke("M4 12 C6.6 6.9 17.4 6.9 20 12 C17.4 17.1 6.6 17.1 4 12 Z")
            + stroke("M8.6 9.2 L9.7 11.3 L10.8 9.1 M13.2 9.1 L14.3 11.3 L15.4 9.2")),
    "help": ("помогать", stroke("M3.4 16.6 C3.8 12 6.6 8.8 10.4 9.3 L13 11.9")
             + stroke("M20.6 16.6 C20.2 12 17.4 8.8 13.6 9.3 L11 11.9")
             + stroke("M9.2 13.7 C10.3 15.9 13.7 15.9 14.8 13.7")),
    "pie": ("пирог", stroke("M4 15.6 C4 10.7 7.5 8 12 8 C16.5 8 20 10.7 20 15.6 Z")
            + stroke("M8.4 11.9 L9.5 10.4 M12 11.2 V9.5 M15.6 11.9 L14.5 10.4") + stroke("M3 18.6 H21")),
    "puddle": ("лужа", stroke("M4.4 15.6 C3.7 13.3 6.3 12.2 8.6 12.7 C10 11.3 13.7 11.2 15.3 12.6 "
                              "C17.9 12.1 20.6 13.5 19.6 15.8 C18.7 17.9 5.4 18.1 4.4 15.6 Z")
               + stroke("M12 3.4 C10.6 5.9 10.1 7.1 10.1 7.9 C10.1 9 11 9.9 12 9.9 "
                        "C13 9.9 13.9 9 13.9 7.9 C13.9 7.1 13.4 5.9 12 3.4 Z")),
    # С3 — первый знак, который Вера придумала без папы: «здесь», но двое
    "friend": ("друг", stroke(ring(12, 12, 7.5)) + dot(9.3, 12, 1.55) + dot(14.7, 12, 1.55)),
    # С5 — первый за много лет знак от Феликса: кувшин, а в нём «здесь» без точки — никого
    "vessel": ("сосуд", stroke("M9.4 3.2 H14.6 M10.3 3.2 V5.4 C6.6 6.9 5.4 10 5.9 13.3 "
                               "C6.5 17.1 8.8 19.7 12 19.7 C15.2 19.7 17.5 17.1 18.1 13.3 "
                               "C18.6 10 17.4 6.9 13.7 5.4 V3.2")
               + stroke("M16.2 6.6 C20.4 6 21.6 10.9 18.2 12.6")          # ручка: кувшин, а не склянка
               + stroke(ring(12, 13.2, 3.1))),
}

MANY = dot(9.6, 22.7, 1.15) + dot(14.4, 22.7, 1.15)   # две точки под знаком — «много»
PAST = stroke("M7 1.2 H17")                           # черта над знаком — прошедшее время

SPARK = ('<svg viewBox="0 0 24 24" aria-hidden="true"><rect width="24" height="24" rx="6" fill="#0e0e12"/>'
         '<path d="M12 4.2 13.5 10.5 19.8 12 13.5 13.5 12 19.8 10.5 13.5 4.2 12 10.5 10.5Z" fill="#dfe1e8"/></svg>')

ORDINAL = ["", "первой", "второй", "третьей", "четвёртой", "пятой", "шестой", "седьмой",
           "восьмой", "девятой", "десятой", "одиннадцатой", "двенадцатой", "тринадцатой",
           "четырнадцатой", "пятнадцатой", "шестнадцатой", "семнадцатой", "восемнадцатой",
           "девятнадцатой", "двадцатой"]

DIVIDER = '<div class="divider" aria-hidden="true"><span></span><span></span><span></span></div>'

TOKEN = r"\{\w+[+^]*\}"
RUN = rf"(?:{TOKEN})+"


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def glyph(name, cls="g", i=None, mods=""):
    if name not in GLYPHS:
        sys.exit(f"Неизвестный знак лисьего алфавита: {{{name}}}")
    label, body = GLYPHS[name]
    if "+" in mods:
        body += MANY
        label += ", много"
    if "^" in mods:
        body += PAST
        label += ", прошедшее время"
    style = f' style="--i:{i}"' if i is not None else ""
    return f'<svg class="{cls}" viewBox="0 0 24 24" role="img" aria-label="{label}"{style}>{body}</svg>'


def _nowrap(m):
    # Знак не отрывается ни от слова перед ним, ни от препинания и тире после него
    # (неразрывный пробел перед встроенным svg браузеры не соблюдают, поэтому nowrap)
    pre, run, post = m.group(1) or "", m.group(2), m.group(3) or ""
    pre = pre[:-1] + NBSP if pre else ""
    return f'<span class="nw">{pre}{run.replace("}{", "}" + THIN + "{")}{post}</span>'


def typo(s):
    """Экранирование и русская типографика: неразрывные пробелы перед тире и после коротких слов."""
    s = " ".join(s.split())
    s = html.escape(s, quote=False)
    s = s.replace("...", "…")
    s = s.replace(" — ", NBSP + "— ")
    s = re.sub(r"^— ", "—" + NBSP, s)
    s = s.replace("до н. э.", f"до{NBSP}н.{NBSP}э.").replace("гг. ", "гг." + NBSP)
    s = re.sub(r"(?<![^\s («„])([вксуоиаяВКСУОИАЯ]) ", "\\1" + NBSP, s)
    s = re.sub(rf"(\S+[  ])?({RUN})([.,:;!?»“)…]*(?: —)?)", _nowrap, s)
    s = re.sub(r"__([^_]+?)__", r"<u>\1</u>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"\{(\w+)([+^]*)\}", lambda m: glyph(m.group(1), mods=m.group(2)), s)
    return s


def mirror(kind, spec):
    rows, i = [], 0
    for row in spec.split("/"):
        cells = []
        for tok in re.findall(r'"[^"]+"|\S+', row):
            if tok.startswith('"'):
                cells.append(f'<span class="letters" style="--i:{i}">{html.escape(tok[1:-1])}</span>')
            else:
                m = re.fullmatch(r"(\w+)([+^]*)", tok)
                if not m:
                    sys.exit(f"Не разобрать знак на зеркале: {tok}")
                cells.append(glyph(m.group(1), i=i, mods=m.group(2)))
            i += 1
        rows.append('<div class="row">' + "".join(cells) + "</div>")
    cls = {"mirror": "mirror", "mirror-hot": "mirror hot", "mirror-below": "mirror back"}[kind]
    label = "Знаки на стекле, вид снизу" if kind == "mirror-below" else "Знаки на зеркале"
    return f'<figure class="{cls}" aria-label="{label}">' + "".join(rows) + "</figure>"


def tape(spec):
    """Кусок ленты самописца: сонная колючая дорожка, а между отметками — «почерк»."""
    marks = spec.split()
    rnd = random.Random("tape:" + spec)
    W, H, MID = 480, 136, 58
    x0, x1 = 150, 330
    d, x = [f"M0 {MID}"], 0.0
    while x < W:
        if x0 <= x < x1:
            step = rnd.uniform(9, 16)
            up = MID - rnd.uniform(14, 32)
            down = MID + rnd.uniform(8, 24)
            back = x + step * rnd.uniform(-0.7, 0.15)       # перо уходит назад — получается петля
            d.append(f"C{x + step * .3:.1f} {up:.1f} {x + step * 1.4:.1f} {up - 4:.1f} "
                     f"{back:.1f} {MID + rnd.uniform(-10, 4):.1f}")
            d.append(f"S{x + step * 1.2:.1f} {down:.1f} {x + step:.1f} {MID + rnd.uniform(-5, 5):.1f}")
            x += step
        else:
            x += 3.2
            d.append(f"L{x:.1f} {MID + rnd.uniform(-3, 3):.1f}")
    grid = "".join(f"M{gx} 8 V{H - 34} " for gx in range(15, W, 30))
    grid += "".join(f"M0 {gy} H{W} " for gy in (22, 58, 94))
    labels = ""
    if len(marks) >= 2:
        labels = (f'<path class="tick" d="M{x0} {H - 36} V{H - 26} M{x1} {H - 36} V{H - 26}"/>'
                  f'<text x="{x0}" y="{H - 6}" text-anchor="middle">{html.escape(marks[0])}</text>'
                  f'<text x="{x1}" y="{H - 6}" text-anchor="middle">{html.escape(marks[1])}</text>')
    label = "Лента самописца" + (f": {html.escape(marks[0])}–{html.escape(marks[1])}" if len(marks) >= 2 else "")
    return (f'<figure class="tape" role="img" aria-label="{label}"><svg viewBox="0 0 {W} {H}" aria-hidden="true">'
            f'<rect class="paper" width="{W}" height="{H}"/><path class="grid" d="{grid.strip()}"/>'
            f'<path class="ink" d="{" ".join(d)}"/>{labels}</svg></figure>')


def smokemap(n=1):
    """Карта дыма «Фосфора»: город из зелёных точек-датчиков, река и оранжевые вспышки.

    Одна вспышка — квартира Каро (С3). Остальные раскладываются своим генератором,
    так что карта с одной вспышкой остаётся точно такой же, как была.
    """
    rnd = random.Random("smokemap")
    W, H = 400, 250

    def river_y(x):
        return 176 + 20 * math.sin(x / 68) - x * 0.13

    river = " ".join(f"{'M' if x == -10 else 'L'}{x} {river_y(x):.1f}" for x in range(-10, 415, 5))
    streets = "".join(f"M{rnd.uniform(0, W):.0f} 0 L{rnd.uniform(0, W):.0f} {H} " for _ in range(7))
    streets += "".join(f"M0 {rnd.uniform(0, H):.0f} L{W} {rnd.uniform(0, H):.0f} " for _ in range(6))
    pts = []
    for _ in range(26):
        cx, cy = rnd.uniform(15, W - 15), rnd.uniform(15, H - 15)
        sx, sy = rnd.uniform(9, 24), rnd.uniform(7, 18)
        pts += [(rnd.gauss(cx, sx), rnd.gauss(cy, sy)) for _ in range(rnd.randint(22, 46))]
    pts += [(rnd.uniform(0, W), rnd.uniform(0, H)) for _ in range(220)]
    hits = [(268.0, 92.0)]
    more = random.Random(f"smokemap-hits:{n}")
    while len(hits) < n:
        hx, hy = round(more.uniform(18, W - 18), 1), round(more.uniform(18, H - 18), 1)
        if abs(hy - river_y(hx)) < 16 or any(math.hypot(hx - a, hy - b) < 20 for a, b in hits):
            continue
        hits.append((hx, hy))
    groups = {0: [], 1: [], 2: []}
    for px, py in pts:
        if not (3 < px < W - 3 and 3 < py < H - 3) or abs(py - river_y(px)) < 11:
            continue
        if any(math.hypot(px - a, py - b) < 4 for a, b in hits):
            continue
        groups[rnd.choice((0, 1, 1, 2, 2, 2))].append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.3"/>')
    dots = "".join(f'<g class="d{k}">{"".join(v)}</g>' for k, v in groups.items())
    flashes = ""
    for k, (hx, hy) in enumerate(hits):
        delay = f' style="animation-delay:-{k * 0.83 % 2.6:.2f}s"' if k else ""
        flashes += (f'<circle class="ring" cx="{hx:g}" cy="{hy:g}" r="3"{delay}/>'
                    f'<circle class="hit" cx="{hx:g}" cy="{hy:g}" r="3"/>')
    label = "одна оранжевая" if n == 1 else "много оранжевых"
    return (f'<figure class="smokemap" role="img" aria-label="Карта дыма: тысячи зелёных точек и {label}">'
            f'<svg viewBox="0 0 {W} {H}" aria-hidden="true"><rect class="bg" width="{W}" height="{H}"/>'
            f'<path class="streets" d="{streets.strip()}"/><path class="river" d="{river}"/>{dots}'
            f'{flashes}</svg></figure>')


SATOR_ROWS = ("SATOR", "AREPO", "TENET", "OPERA", "ROTAS")


def sator():
    """Квадрат SATOR на чугунной печной заслонке: читается одинаково с любой стороны."""
    cells = "".join(f"<span>{ch}</span>" for row in SATOR_ROWS for ch in row)
    return ('<figure class="sator" role="img" aria-label="Квадрат SATOR: '
            + ", ".join(SATOR_ROWS) + f'"><div class="grid" aria-hidden="true">{cells}</div></figure>')


def city_open(fields):
    """Начало вставки «Город»: штамп «Фосфора» — время, место и что видит датчик."""
    blind = len(fields) > 1 and fields[-1].lower() == "нет данных"
    spans = []
    for j, field in enumerate(fields):
        text = html.escape(field, quote=False).replace("№ ", "№" + NBSP)
        if j == len(fields) - 1 and len(fields) > 1:
            text += '<i class="pin" aria-hidden="true"></i>'
        spans.append(f"<span>{text}</span>")
    aria = html.escape(". ".join(fields))
    # Разделитель «·» стоит перед каждым полем; у первого поля в строке он уезжает
    # за левый край и обрезается, так что перенос не начинается с точки
    return (f'<section class="city{" blind" if blind else ""}" aria-label="{aria}"><div class="wrap">\n'
            f'<p class="stamp"><span class="stamp-in">{"".join(spans)}</span></p>\n')


def card(kind, mods, label, lines):
    cls = " ".join([kind] + [x for x in mods.split(".") if x])
    lines = [ln.strip() for ln in lines if ln.strip()]
    if kind == "notice":
        head = f'<div class="notice-head">{SPARK}<span>{html.escape(label or "«Фосфор»")}</span></div>'
        buttons = ""
        if lines and re.fullmatch(r"(?:\[[^\]]+\]\s*)+", lines[-1]):
            names = re.findall(r"\[([^\]]+)\]", lines.pop())
            buttons = '<div class="btns" aria-hidden="true">' + "".join(
                f'<span class="btn{" primary" if j == len(names) - 1 else ""}">{html.escape(n)}</span>'
                for j, n in enumerate(names)) + "</div>"
        return f'<div class="{cls}" role="note">{head}<p>{typo(" ".join(lines))}</p>{buttons}</div>'
    body = []
    for ln in lines:
        if kind == "doc" and ln.startswith("✎"):
            body.append(f'<p class="hand">{typo(ln[1:])}</p>')
        elif kind == "doc" and ln.startswith("·"):
            body.append(f'<p class="fine">{typo(ln[1:])}</p>')
        elif kind == "doc" and (sm := re.fullmatch(r"(.+?):\s*_{3,}", ln)):
            body.append(f'<p class="sig"><span>{typo(sm.group(1))}:</span>'
                        f'<span class="line" role="img" aria-label="пусто"></span></p>')
        else:
            body.append(f"<p>{typo(ln)}</p>")
    cap = f"<figcaption>{html.escape(label)}</figcaption>" if label else ""
    return f'<figure class="{cls}">{cap}{"".join(body)}</figure>'


def build(src, out, template):
    raw = Path(src).read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    head, _, body = raw.partition("\n\n")
    meta = {}
    for line in head.splitlines():
        key, _, value = line.partition(":")
        meta[key.strip().upper()] = value.strip()
    title = meta["TITLE"]
    number = int(meta["NUMBER"])
    emblem = meta.get("EMBLEM", "fox")
    cold = int(meta.get("COLD", "0") or 0)   # насколько остыл Архив: 0 — как в С1–С4

    sections = [["earth", "", []]]
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        items = sections[-1][2]
        if block == "***":
            items.append(DIVIDER)
        elif block.startswith(">>>"):
            label = block[3:].strip()
            fields = [f.strip() for f in label.split("·") if f.strip()]
            if fields and fields[0].lower() == "город":
                sections.append(["city", fields, []])
            else:
                sections.append(["below", label, []])
        elif block.startswith("<<<"):
            sections.append(["earth", "", []])
        elif (m := re.fullmatch(r"\[\[(mirror(?:-hot|-below)?):\s*(.+?)\]\]", block)):
            items.append(mirror(m.group(1), m.group(2)))
        elif (m := re.fullmatch(r"\[\[tape:\s*(.*?)\]\]", block)):
            items.append(tape(m.group(1)))
        elif (m := re.fullmatch(r"\[\[smokemap(?::\s*(\d+))?\]\]", block)):
            items.append(smokemap(int(m.group(1) or 1)))
        elif block == "[[sator]]":
            items.append(sator())
        elif block.startswith(">>"):
            items.append(f'<div class="page"><p>{typo(block[2:])}</p></div>')
        elif (m := re.match(r">(log|doc|notice)((?:\.[\w-]+)*)(?:\[(.+?)\])?[ \t]*(.*)", block)):
            kind, mods, label, first = m.groups()
            items.append(card(kind, mods, label, [first] + block.splitlines()[1:]))
        elif block.startswith(">"):
            rest, label = block[1:].strip(), ""
            if (lm := re.match(r"\[(.+?)\]\s*", rest)):
                label = f'<span class="label">{html.escape(lm.group(1))}</span>'
                rest = rest[lm.end():]
            items.append(f'<div class="call">{label}<p>{typo(rest)}</p></div>')
        elif re.fullmatch(rf"(?:{TOKEN}\s*)+", block):
            toks = re.findall(r"\{(\w+)([+^]*)\}", block)
            items.append('<p class="signs">' + THIN.join(glyph(n, mods=md) for n, md in toks) + "</p>")
        elif re.fullmatch(r"\*[^*]+\*", block):
            items.append(f'<p class="voice"><em>{typo(block[1:-1])}</em></p>')
        else:
            items.append(f"<p>{typo(block)}</p>")

    plain = re.sub(rf"{TOKEN}|\[\[.*?\]\]|^>+\w*(?:\.[\w-]+)*(?:\[.*?\])?|^\*+|\*+$|✎|_+", " ",
                   body, flags=re.M)
    words = len(re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", plain))
    minutes = words / 190
    minutes = max(5, int(5 * round(minutes / 5))) if minutes >= 7.5 else max(1, round(minutes))

    parts = [
        '<header class="hero"><div class="wrap">',
        glyph(emblem, cls="g emblem"),
        '<p class="series">Пандемониум</p>',
        f'<p class="ep">Серия {number}</p>',
        f"<h1>{html.escape(title)}</h1>",
        f'<p class="meta">≈{NBSP}{minutes}{NBSP}{plural(minutes, "минута", "минуты", "минут")} чтения</p>',
        '<div class="scroll-cue" aria-hidden="true"></div>',
        "</div></header>",
    ]
    for kind, label, items in sections:
        if not items:
            continue
        if kind == "earth":
            parts.append('<section class="earth"><div class="wrap">\n' + "\n".join(items) + "\n</div></section>")
        elif kind == "city":
            parts.append(city_open(label) + "\n".join(items) + "\n</div></section>")
        else:
            lab = f'<p class="below-label">{html.escape(label)}</p>\n' if label else ""
            cls = f'below cold-{cold}" data-cold="{cold}' if cold else "below"
            parts.append(f'<section class="{cls}"><div class="ash" aria-hidden="true"></div><div class="wrap">\n'
                         + lab + "\n".join(items) + "\n</div></section>")
    ordinal = ORDINAL[number] if number < len(ORDINAL) else f"{number}-й"
    parts += [
        '<footer class="end"><div class="wrap">',
        DIVIDER,
        f'<p class="end-title">Конец {ordinal} серии</p>',
        '<p class="end-sub">Пандемониум · продолжение следует</p>',
        "</div></footer>",
    ]

    page = Path(template).read_text(encoding="utf-8")
    page = page.replace("{{PAGE_TITLE}}", html.escape(f"Пандемониум · Серия {number} · {title}"))
    page = page.replace("{{CONTENT}}", "\n".join(parts))
    Path(out).write_text(page, encoding="utf-8")
    below = sum(1 for s in sections if s[0] == "below")
    city = sum(1 for s in sections if s[0] == "city")
    print(f"{out}: {words} слов, ≈{minutes} мин чтения, сцен внизу: {below}"
          + (f", вставок «Город»: {city}" if city else ""))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Использование: build_episode.py исходник.txt серия.html [шаблон.html]")
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else HERE / "template.html")
