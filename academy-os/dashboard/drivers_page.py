"""Drivers section of the staff dashboard — the RL CRM prototype rebuilt on
the shared Academy OS data layer. All progression rules live in
comms-agent/progression.py; this module only renders and dispatches forms."""

import html
import urllib.parse
from datetime import date

import academy_data as db_mod
import progression as prog

E = html.escape

GROUPS = ["Cadet (7-12)", "Junior (12-15)", "Senior (15+)"]


def _dots(filled, total, color, alert=False):
    dot_color = "#ff3b30" if alert else color
    dots = "".join(
        f'<span class="dot" style="background:{dot_color if i < filled else "rgba(255,255,255,0.07)"};'
        f'{f"box-shadow:0 0 5px {dot_color}90;" if i < filled else ""}"></span>'
        for i in range(total))
    return f'<span class="dots">{dots}</span>'


def _level_badge(level_id):
    lv = prog.LEVELS[level_id]
    return (f'<span class="lvl" style="color:{lv["color"]};'
            f'border-color:{lv["color"]}40;background:{lv["color"]}18">'
            f'{lv["label"]}</span>')


def _alerts_strip(students):
    rows = ""
    for s in students:
        for a in prog.alerts_for(s):
            lv = prog.LEVELS[s["level"]]
            action = (
                f'<a class="btn small" href="#drv-{s["id"]}">Review</a>'
                if a["type"] == "promotion" else
                f'<form method="post" action="/drivers/{s["id"]}/dismiss">'
                f'<input type="hidden" name="type" value="{a["type"]}">'
                f'<button class="ghost small">Dismiss</button></form>')
            rows += (f'<div class="alert-row"><div>'
                     f'<strong style="color:{lv["color"]}">{E(s["name"])}</strong> '
                     f'<span class="muted">{E(a["message"])}</span></div>{action}</div>')
    if not rows:
        return ""
    return f'<div class="card alerts"><h2>Reminders</h2>{rows}</div>'


def _training_history(s, lv):
    if not s.get("training_log"):
        return '<p class="muted">No coached sessions logged yet.</p>'
    rows = ""
    for e in reversed(s["training_log"][-20:]):
        notes = (f'<div class="muted" style="font-style:italic">{E(e.get("notes", ""))}</div>'
                 if e.get("notes") else "")
        rows += (f'<div class="log-row"><div><strong>{E(e["date"])}</strong>{notes}</div>'
                 f'<span class="count" style="color:{lv["color"]};'
                 f'background:{lv["color"]}18">×{e["sessions"]}</span></div>')
    return rows


def _driver_card(s):
    lv = prog.LEVELS[s["level"]]
    filled, size, cycles = prog.cycle_position(s)
    total = prog.total_sessions(s)
    months = prog.months_elapsed(s.get("level_start_date")) + 1
    alerts = {a["type"]: a for a in prog.alerts_for(s)}
    border = "#ff3b3055" if ("monthly" in alerts) else (
        f"{lv['color']}55" if alerts else "rgba(210,255,0,.16)")

    badges = ""
    if "cycle" in alerts:
        badges += f'<span class="flag" style="background:{lv["color"]};color:#000">CYCLE DONE</span>'
    if "monthly" in alerts:
        badges += '<span class="flag" style="background:#ff3b30;color:#fff">MONTH DUE</span>'

    advanced_bar = ""
    if s["level"] == "advanced":
        mth = prog.sessions_this_month(s)
        pct = min(mth / size * 100, 100)
        bar_color = "#4caf50" if mth >= size else lv["color"]
        advanced_bar = (
            f'<div class="advbar"><div class="row"><span class="muted small-caps">This month</span>'
            f'<strong style="color:{bar_color}">{mth} / {size} sessions</strong></div>'
            f'<div class="track"><div class="fill" style="width:{pct}%;background:{bar_color}"></div></div></div>')

    promo = ""
    if "promotion" in alerts:
        next_lv = prog.LEVELS[lv["next"]]
        promo = (
            f'<div class="promo"><div>🏁 <strong style="color:{next_lv["color"]}">'
            f'Ready for {next_lv["label"]}</strong>'
            f'<div class="muted">Level duration complete — promote or extend</div></div>'
            f'<div class="row" style="gap:.5rem">'
            f'<form method="post" action="/drivers/{s["id"]}/promote">'
            f'<button class="btn small">Move to {next_lv["label"]}</button></form>'
            f'<form method="post" action="/drivers/{s["id"]}/extend">'
            f'<button class="ghost small">Extend +1 month</button></form></div></div>')

    today = date.today().isoformat()
    return f"""
    <div class="card drv" id="drv-{s['id']}" style="border-color:{border}">
      <div class="drv-head">
        <div class="drv-id">
          <div><strong class="drv-name">{E(s['name'])}</strong> {_level_badge(s['level'])} {badges}</div>
          <div class="muted">{E(s.get('kart', ''))} kart · {E(s.get('group', ''))} ·
            Month {months} · {E(s.get('parent_phone', ''))}</div>
        </div>
        <div class="total"><div class="n" style="color:{lv['color']}">{total}</div>
          <div class="muted small-caps">total</div></div>
      </div>
      <div class="row" style="margin-top:.8rem">
        <div>
          <div class="muted small-caps">Session cycle · every {size}
            {f'· {cycles} complete' if cycles else ''}</div>
          {_dots(filled, size, lv['color'], 'cycle' in alerts)}
        </div>
        <span class="muted">{size - filled if filled < size else 0} left</span>
      </div>
      {advanced_bar}{promo}
      <details><summary>Log session</summary>
        <form method="post" action="/drivers/{s['id']}/log" class="inline-form">
          <input type="date" name="date" value="{today}" required>
          <select name="sessions">{''.join(f'<option>{n}</option>' for n in range(1, 6))}</select>
          <input type="text" name="notes" placeholder="Notes — braking, corner entry...">
          <button class="btn small">Log</button>
        </form>
      </details>
      <details><summary>History ({len(s.get('training_log', []))})</summary>
        {_training_history(s, lv)}
      </details>
      <details><summary>Edit / remove</summary>
        <form method="post" action="/drivers/{s['id']}/edit" class="inline-form wrap">
          <input type="text" name="name" value="{E(s['name'])}" required>
          <input type="text" name="parent_phone" value="{E(s.get('parent_phone', ''))}">
          <select name="group">{''.join(f'<option{" selected" if g == s.get("group") else ""}>{g}</option>' for g in GROUPS)}</select>
          <select name="kart">{''.join(f'<option{" selected" if k == s.get("kart") else ""}>{k}</option>' for k in prog.KART_CATEGORIES)}</select>
          <select name="level">{''.join(f'<option value="{k}"{" selected" if k == s["level"] else ""}>{v["label"]}</option>' for k, v in prog.LEVELS.items())}</select>
          <button class="btn small">Save</button>
        </form>
        <form method="post" action="/drivers/{s['id']}/delete"
              onsubmit="return confirm('Remove {E(s['name'])} and their bookings?')">
          <button class="ghost small danger">Remove driver</button>
        </form>
      </details>
    </div>"""


def page_drivers(query=""):
    params = urllib.parse.parse_qs(query)
    q = params.get("q", [""])[0].lower()
    level_filter = params.get("level", [""])[0]

    db = db_mod.load()
    students = db["students"]
    shown = [s for s in students
             if (not q or q in s["name"].lower())
             and (not level_filter or s["level"] == level_filter)]

    n_alerts = sum(len(prog.alerts_for(s)) for s in students)
    tiles = f"""
    <div class="tiles">
      <div class="tile"><div class="label">Drivers</div><div class="value">{len(students)}</div></div>
      {''.join(f'<div class="tile"><div class="label">{lv["label"].title()}</div>'
               f'<div class="value" style="color:{lv["color"]}">'
               f'{sum(1 for s in students if s["level"] == k)}</div></div>'
               for k, lv in prog.LEVELS.items())}
      <div class="tile{' alert' if n_alerts else ''}"><div class="label">Alerts</div>
        <div class="value">{n_alerts}</div></div>
    </div>"""

    filters = '<div class="row" style="margin-bottom:1rem;justify-content:flex-start;gap:.5rem;flex-wrap:wrap">'
    filters += ('<form method="get" action="/drivers" style="display:inline">'
                f'<input type="text" name="q" value="{E(q)}" placeholder="Search drivers..." '
                'style="padding:.45em .8em;border-radius:6px;border:1px solid rgba(210,255,0,.16);'
                'background:#141B06;color:#fff"></form>')
    for key, label in [("", "All levels")] + [(k, v["label"]) for k, v in prog.LEVELS.items()]:
        active = "btn" if key == level_filter else "ghost"
        filters += f'<a class="{active} small" href="/drivers?level={key}">{label}</a>'
    filters += '<a class="btn small" href="/drivers/new" style="margin-left:auto">+ Add driver</a></div>'

    cards = "".join(_driver_card(s) for s in shown) or \
        '<div class="card muted">No drivers match.</div>'
    return tiles + _alerts_strip(students) + filters + cards


def page_new_driver():
    today = date.today().isoformat()
    levels = "".join(
        f'<label class="lvl-opt"><input type="radio" name="level" value="{k}"'
        f'{" checked" if k == "intro" else ""}> <strong style="color:{v["color"]}">'
        f'{v["label"]}</strong> <span class="muted">{v["description"]}</span></label>'
        for k, v in prog.LEVELS.items())
    return f"""
    <div class="card" style="max-width:480px">
      <form method="post" action="/drivers/new" class="stacked">
        <label>Driver name <input type="text" name="name" required></label>
        <label>Parent phone / WhatsApp <input type="text" name="parent_phone" placeholder="+20..."></label>
        <label>Age group <select name="group">{''.join(f'<option>{g}</option>' for g in GROUPS)}</select></label>
        <label>Kart category <select name="kart">{''.join(f'<option>{k}</option>' for k in prog.KART_CATEGORIES)}</select></label>
        <div class="small-caps muted" style="margin:.4rem 0">Academy level</div>{levels}
        <label>Level start date <input type="date" name="level_start_date" value="{today}"></label>
        <button class="btn">Add driver</button>
      </form>
    </div>"""


def handle_post(path, form):
    """Dispatch /drivers/... POSTs. Returns redirect path or None."""
    db = db_mod.load()

    if path == "/drivers/new":
        db_mod.add_student(
            db, form.get("name", [""])[0], form.get("parent_phone", [""])[0],
            form.get("group", [GROUPS[0]])[0], form.get("kart", ["Junior"])[0],
            form.get("level", ["intro"])[0],
            form.get("level_start_date", [date.today().isoformat()])[0])
        return "/drivers"

    parts = path.strip("/").split("/")
    if len(parts) != 3 or parts[0] != "drivers":
        return None
    student_id, action = parts[1], parts[2]
    student = next((s for s in db["students"] if s["id"] == student_id), None)
    if student is None:
        return "/drivers"

    if action == "log":
        prog.log_training(student, form.get("sessions", ["1"])[0],
                          form.get("date", [None])[0],
                          form.get("notes", [""])[0])
        db_mod.save(db)
    elif action == "dismiss":
        student.setdefault("dismissed", {})[form.get("type", [""])[0]] = True
        db_mod.save(db)
    elif action == "promote":
        prog.promote(student)
        db_mod.save(db)
    elif action == "extend":
        prog.extend_level(student)
        db_mod.save(db)
    elif action == "edit":
        db_mod.update_student(db, student_id,
                              name=form.get("name", [""])[0],
                              parent_phone=form.get("parent_phone", [""])[0],
                              group=form.get("group", [""])[0],
                              kart=form.get("kart", [""])[0],
                              level=form.get("level", [""])[0])
    elif action == "delete":
        db_mod.delete_student(db, student_id)
    return "/drivers"
