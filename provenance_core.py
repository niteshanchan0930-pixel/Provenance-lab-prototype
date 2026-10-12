"""Provenance Lab core: login and roles, SQLite storage, chemical inventory ledger,
dissertation library and admin pages. Imported by Lab_Experiment.py (keep both files
in the same folder)."""
import datetime
import os
import re
import sqlite3

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------
ALLOWED_DOMAIN = "jssuni.edu.in"  # CHANGE to your institute's mail domain
DB_PATH = os.environ.get("PL_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "provenance_lab.db"
)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

ROLES = ["student", "lecturer", "attender", "admin"]
ROLE_LABEL = {
    "student": "Student",
    "lecturer": "Lecturer / mentor",
    "attender": "Lab attender",
    "admin": "Admin",
}
ROLE_ICON = {"student": "🎓", "lecturer": "👩‍🏫", "attender": "🧰", "admin": "🛠️"}

P1 = "1. Protocol & Literature Search"
P2 = "2. Results & Data Upload"
P3 = "3. Checker / Mentor Review"
P4 = "4. Print & Submission Preview"
P5 = "5. Power BI Analytics"
P6 = "6. Daily Report"
P7 = "7. Chemicals & Inventory"
P8 = "8. Dissertation Library"
P9 = "9. Admin"
PAGE_ICONS = {
    P1: "📋", P2: "📊", P3: "👨‍🏫", P4: "📄", P5: "📈",
    P6: "📝", P7: "🧪", P8: "📚", P9: "🛠️",
}
ACCESS = {
    "student": [P1, P2, P4, P6, P7, P8],
    "lecturer": [P1, P2, P3, P4, P5, P6, P7, P8],
    "attender": [P7, P8],
    "admin": [P1, P2, P3, P4, P5, P6, P7, P8, P9],
}


def pages_for(role):
    return ACCESS.get(role, [])


def now_str():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")


# ----------------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------------
def _con():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def q(sql, params=()):
    con = _con()
    try:
        return pd.read_sql_query(sql, con, params=params)
    finally:
        con.close()


def ex(sql, params=()):
    con = _con()
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, name TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
    category TEXT, unit TEXT, min_stock REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS lots(id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER,
    lot_no TEXT, expiry TEXT, location TEXT);
CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
    lot_id INTEGER, kind TEXT, qty REAL, session_id INTEGER, user_email TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS practicals(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
    apparatus TEXT);
CREATE TABLE IF NOT EXISTS practical_items(practical_id INTEGER, item_id INTEGER,
    per_student REAL);
CREATE TABLE IF NOT EXISTS usage_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
    practical_id INTEGER, batch_name TEXT, n_students INTEGER, apparatus TEXT, breakage TEXT,
    user_email TEXT, status TEXT, verified_by TEXT);
CREATE TABLE IF NOT EXISTS usage_lines(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER,
    item_id INTEGER, planned REAL, actual REAL, measured TEXT);
CREATE TABLE IF NOT EXISTS flags(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, item_id INTEGER,
    kind TEXT, note TEXT, user_email TEXT, resolved INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS dissertations(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT,
    author TEXT, year INTEGER, guide TEXT, keywords TEXT, abstract TEXT, access TEXT,
    sample INTEGER DEFAULT 0);
"""

# Sample data: placeholders for the demo. Replace with the lab's real data.
SAMPLE_ITEMS = [
    # name, category, unit, min stock, [(lot no, expiry in days from today, quantity, location)]
    ("Paracetamol", "API", "g", 50, [("PCM-A1", 540, 500, "Shelf A1")]),
    ("Metformin HCl", "API", "g", 40, [("MET-B2", 420, 120, "Shelf A2")]),
    ("Diltiazem HCl", "API", "g", 20, [("DIL-C1", 300, 8, "Shelf A3")]),
    ("Curcumin", "API", "g", 10, [("CUR-D1", 200, 0, "Shelf A4")]),
    ("HPMC K4M", "Excipient", "g", 50, [("HPM-E1", 600, 200, "Shelf B1")]),
    ("Microcrystalline cellulose", "Excipient", "g", 100, [("MCC-F1", 700, 1000, "Shelf B2")]),
    ("Magnesium stearate", "Excipient", "g", 20, [("MGS-G1", 500, 100, "Shelf B3")]),
    ("Lactose monohydrate", "Excipient", "g", 100,
     [("LAC-H1", -30, 150, "Shelf B4"), ("LAC-H2", 365, 400, "Shelf B4")]),
    ("Sodium hydroxide", "Reagent", "g", 100, [("NAO-I1", 800, 250, "Shelf C1")]),
    ("Potassium dihydrogen phosphate", "Reagent", "g", 100, [("KDP-J1", 800, 250, "Shelf C2")]),
    ("Ethanol", "Solvent", "mL", 500, [("ETH-K1", 500, 2000, "Solvent cabinet")]),
    ("Methanol", "Solvent", "mL", 500, [("MTH-L1", 500, 1500, "Solvent cabinet")]),
]
SAMPLE_PRACTICALS = [
    ("Tablet formulation by direct compression",
     "Weighing balance, Mortar and pestle, Tablet punching machine, Hardness tester, Friability tester",
     [("Paracetamol", 0.5), ("Microcrystalline cellulose", 1.0),
      ("Magnesium stearate", 0.05), ("Lactose monohydrate", 0.5)]),
    ("Dissolution study of matrix tablets",
     "Dissolution apparatus, UV spectrophotometer, pH meter, Magnetic stirrer, Weighing balance",
     [("Metformin HCl", 0.5), ("HPMC K4M", 0.3),
      ("Potassium dihydrogen phosphate", 0.7), ("Sodium hydroxide", 0.1)]),
    ("Solid dispersion by solvent evaporation",
     "Weighing balance, Magnetic stirrer, Hot air oven, Mortar and pestle",
     [("Diltiazem HCl", 0.2), ("Ethanol", 20.0)]),
]
SAMPLE_DISSERTATIONS = [
    ("Formulation and evaluation of sustained release matrix tablets (sample entry)",
     "Sample Author A", 2024, "Sample Guide 1",
     "sustained release, matrix tablet, HPMC, dissolution kinetics",
     "Sample abstract. Hydrophilic matrix tablets were prepared and release kinetics were compared."),
    ("Nanoparticle-based nose-to-brain delivery (sample entry)",
     "Sample Author B", 2023, "Sample Guide 2",
     "nanoparticles, intranasal, brain delivery, blood brain barrier",
     "Sample abstract. Nanocarriers for intranasal delivery were prepared and characterised."),
    ("Solid dispersion to enhance solubility of a BCS class II drug (sample entry)",
     "Sample Author C", 2025, "Sample Guide 1",
     "solid dispersion, solubility, BCS class II, solvent evaporation",
     "Sample abstract. Solid dispersions were made by solvent evaporation and dissolution was compared."),
    ("Topical gel for psoriasis: formulation and in vitro release (sample entry)",
     "Sample Author D", 2022, "Sample Guide 3",
     "psoriasis, topical gel, in vitro release, skin delivery",
     "Sample abstract. A topical gel was formulated and drug release was evaluated in vitro."),
    ("QbD-based optimisation of a nanoemulsion using Box-Behnken design (sample entry)",
     "Sample Author E", 2024, "Sample Guide 2",
     "QbD, Box-Behnken, nanoemulsion, DoE, optimisation",
     "Sample abstract. Critical process parameters were optimised using a Box-Behnken design."),
]


def _seed_users():
    if int(q("SELECT COUNT(*) AS n FROM users").n[0]) > 0:
        return
    for local, name, role in [
        ("student", "Demo Student", "student"),
        ("lecturer", "Demo Lecturer", "lecturer"),
        ("attender", "Demo Attender", "attender"),
        ("admin", "Demo Admin", "admin"),
    ]:
        ex("INSERT INTO users(email,name,role) VALUES (?,?,?)",
           (f"{local}@{ALLOWED_DOMAIN}", name, role))


def _seed_inventory():
    if int(q("SELECT COUNT(*) AS n FROM items").n[0]) > 0:
        return
    today = datetime.date.today()
    con = _con()
    try:
        ids = {}
        for name, cat, unit, mn, lots in SAMPLE_ITEMS:
            cur = con.execute(
                "INSERT INTO items(name,category,unit,min_stock) VALUES (?,?,?,?)",
                (name, cat, unit, mn))
            ids[name] = cur.lastrowid
            for lot_no, days, qty, loc in lots:
                exp = (today + datetime.timedelta(days=days)).isoformat()
                lcur = con.execute(
                    "INSERT INTO lots(item_id,lot_no,expiry,location) VALUES (?,?,?,?)",
                    (ids[name], lot_no, exp, loc))
                con.execute(
                    "INSERT INTO transactions(ts,lot_id,kind,qty,user_email,note) "
                    "VALUES (?,?,?,?,?,?)",
                    (now_str(), lcur.lastrowid, "opening", qty,
                     f"attender@{ALLOWED_DOMAIN}", "Sample opening stock"))
        for pname, app, lines in SAMPLE_PRACTICALS:
            cur = con.execute("INSERT INTO practicals(name,apparatus) VALUES (?,?)", (pname, app))
            for iname, per in lines:
                con.execute(
                    "INSERT INTO practical_items(practical_id,item_id,per_student) VALUES (?,?,?)",
                    (cur.lastrowid, ids[iname], per))
        con.commit()
    finally:
        con.close()


def _seed_library():
    if int(q("SELECT COUNT(*) AS n FROM dissertations").n[0]) > 0:
        return
    for title, author, year, guide, kw, ab in SAMPLE_DISSERTATIONS:
        ex("INSERT INTO dissertations(title,author,year,guide,keywords,abstract,access,sample) "
           "VALUES (?,?,?,?,?,?,?,1)",
           (title, author, year, guide, kw, ab, "Metadata only"))


def init_db():
    con = _con()
    try:
        con.executescript(SCHEMA)
        con.commit()
    finally:
        con.close()
    _seed_users()
    _seed_inventory()
    _seed_library()


def reset_demo_data():
    con = _con()
    try:
        for t in ("transactions", "lots", "practical_items", "practicals", "usage_lines",
                  "usage_sessions", "flags", "items", "dissertations"):
            con.execute(f"DELETE FROM {t}")
        con.commit()
    finally:
        con.close()
    _seed_inventory()
    _seed_library()


# ----------------------------------------------------------------------------
# Login and roles (prototype: no password; real version = Google sign-in)
# ----------------------------------------------------------------------------
def _name_from_email(email):
    local = email.split("@")[0]
    return " ".join(w.capitalize() for w in re.split(r"[._\-]+", local) if w) or email


def _sign_in(email):
    email = email.strip().lower()
    row = q("SELECT * FROM users WHERE email=?", (email,))
    if row.empty:
        ex("INSERT INTO users(email,name,role) VALUES (?,?,?)",
           (email, _name_from_email(email), "student"))
        row = q("SELECT * FROM users WHERE email=?", (email,))
    r = row.iloc[0]
    st.session_state["user"] = {"email": r["email"], "name": r["name"], "role": r["role"]}
    st.rerun()


def login_gate():
    init_db()
    user = st.session_state.get("user")
    if user:
        return user
    st.subheader("🔐 Sign in")
    st.caption(
        f"Use your institutional mail id (@{ALLOWED_DOMAIN}). Prototype: no password is checked. "
        "The real version would use Google sign-in restricted to the institute domain."
    )
    email = st.text_input("Institutional email", key="login_email",
                          placeholder=f"name@{ALLOWED_DOMAIN}")
    if st.button("Sign in", type="primary", key="login_btn"):
        e = email.strip().lower()
        if not re.fullmatch(r"[a-z0-9._+\-]+@" + re.escape(ALLOWED_DOMAIN), e):
            st.error(f"Use your institutional mail id ending with @{ALLOWED_DOMAIN}.")
        else:
            _sign_in(e)
    st.markdown("---")
    st.markdown("**Quick demo login** (prototype only)")
    cols = st.columns(4)
    for col, role in zip(cols, ROLES):
        if col.button(f"{ROLE_ICON[role]} {ROLE_LABEL[role]}", key=f"demo_{role}"):
            _sign_in(f"{role}@{ALLOWED_DOMAIN}")
    st.stop()


def sidebar_user_box(user):
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"👤 **{user['name']}**  \n{ROLE_ICON[user['role']]} {ROLE_LABEL[user['role']]}"
    )
    if st.sidebar.button("Sign out", key="logout_btn"):
        st.session_state.pop("user", None)
        st.rerun()


# ----------------------------------------------------------------------------
# Inventory ledger
# ----------------------------------------------------------------------------
def available_qty(item_id):
    today = datetime.date.today().isoformat()
    df = q(
        "SELECT COALESCE(SUM(t.qty),0) AS bal FROM lots l "
        "LEFT JOIN transactions t ON t.lot_id=l.id WHERE l.item_id=? AND l.expiry>=?",
        (int(item_id), today))
    return float(df.bal[0])


def lots_df():
    return q(
        "SELECT l.id AS lot_id, i.name AS item, i.unit, l.lot_no, l.expiry, l.location, "
        "COALESCE(SUM(t.qty),0) AS balance FROM lots l JOIN items i ON i.id=l.item_id "
        "LEFT JOIN transactions t ON t.lot_id=l.id GROUP BY l.id ORDER BY i.name, l.expiry")


def stock_overview_df():
    today = datetime.date.today().isoformat()
    items = q("SELECT * FROM items ORDER BY category, name")
    bal = q(
        "SELECT l.id AS lot_id, l.item_id, l.expiry, COALESCE(SUM(t.qty),0) AS balance "
        "FROM lots l LEFT JOIN transactions t ON t.lot_id=l.id GROUP BY l.id")
    ver = q(
        "SELECT l.item_id, MAX(t.ts) AS last_verified FROM transactions t "
        "JOIN lots l ON l.id=t.lot_id WHERE t.kind IN ('opening','count','adjust') "
        "GROUP BY l.item_id")
    fl = q("SELECT item_id, COUNT(*) AS n FROM flags WHERE resolved=0 GROUP BY item_id")
    rows = []
    for it in items.itertuples():
        il = bal[bal.item_id == it.id]
        valid = il[il.expiry >= today]
        total = float(valid.balance.sum())
        expired = float(il[il.expiry < today].balance.sum())
        live = valid[valid.balance > 0]
        nearest = live.expiry.min() if not live.empty else "-"
        if total <= 0:
            status = "🔴 Empty"
        elif total <= it.min_stock:
            status = "🟡 Low"
        else:
            status = "🟢 In stock"
        if expired > 0:
            status += " ⚠️ expired lot"
        v = ver[ver.item_id == it.id].last_verified
        rows.append({
            "id": it.id, "Item": it.name, "Category": it.category, "Unit": it.unit,
            "Balance": round(total, 3), "Min stock": it.min_stock, "Status": status,
            "Nearest expiry": nearest, "Last verified": v.iloc[0] if not v.empty else "-",
            "Open flags": int(fl[fl.item_id == it.id].n.sum()),
        })
    return pd.DataFrame(rows)


def record_usage(practical_id, batch, n_students, apparatus, breakage, user_email, lines):
    """lines: [(item_id, planned, actual, measured)]. All-or-nothing. FIFO by earliest expiry.
    Returns (True, session_id) or (False, [(item_id, needed, available)])."""
    today = datetime.date.today().isoformat()
    lot_sql = (
        "SELECT l.id, COALESCE(SUM(t.qty),0) AS bal FROM lots l "
        "LEFT JOIN transactions t ON t.lot_id=l.id WHERE l.item_id=? AND l.expiry>=? "
        "GROUP BY l.id HAVING bal>0 ORDER BY l.expiry")
    con = _con()
    try:
        need = {}
        for item_id, _planned, actual, _m in lines:
            need[item_id] = need.get(item_id, 0.0) + float(actual)
        short = []
        for item_id, total in need.items():
            avail = sum(r["bal"] for r in con.execute(lot_sql, (item_id, today)).fetchall())
            if total > avail + 1e-9:
                short.append((item_id, total, avail))
        if short:
            return False, short
        sid = con.execute(
            "INSERT INTO usage_sessions(ts,practical_id,batch_name,n_students,apparatus,breakage,"
            "user_email,status) VALUES (?,?,?,?,?,?,?,?)",
            (now_str(), practical_id, batch, n_students, apparatus, breakage, user_email,
             "Recorded")).lastrowid
        for item_id, planned, actual, measured in lines:
            con.execute(
                "INSERT INTO usage_lines(session_id,item_id,planned,actual,measured) "
                "VALUES (?,?,?,?,?)", (sid, item_id, planned, actual, measured))
        for item_id, total in need.items():
            remaining = total
            for r in con.execute(lot_sql, (item_id, today)).fetchall():
                take = min(r["bal"], remaining)
                con.execute(
                    "INSERT INTO transactions(ts,lot_id,kind,qty,session_id,user_email,note) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (now_str(), r["id"], "use", -take, sid, user_email, batch))
                remaining -= take
                if remaining <= 1e-9:
                    break
        con.commit()
        return True, sid
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ----------------------------------------------------------------------------
# Inventory page and its tabs
# ----------------------------------------------------------------------------
def inventory_page(user):
    role = user["role"]
    st.header("🧪 Chemicals & Inventory")
    spec = [("📦 Stock overview", _tab_overview), ("🧫 Record practical usage", _tab_record)]
    if role in ("lecturer", "attender", "admin"):
        spec += [("✅ Verify usage", _tab_verify), ("📊 Reports & forecast", _tab_reports)]
    if role in ("lecturer", "admin"):
        spec += [("📝 Practical templates", _tab_templates)]
    if role in ("attender", "admin"):
        spec += [("🧰 Attender: stock & counts", _tab_attender)]
    if role == "attender":
        spec.insert(0, spec.pop())
    tabs = st.tabs([s[0] for s in spec])
    for tab, (_label, fn) in zip(tabs, spec):
        with tab:
            fn(user)


def _tab_overview(user):
    df = stock_overview_df()
    if df.empty:
        st.info("No items yet.")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Items", len(df))
    c2.metric("🔴 Empty", int(df.Status.str.contains("Empty").sum()))
    c3.metric("🟡 Low", int(df.Status.str.contains("Low").sum()))
    c4.metric("⚠️ With expired lot", int(df.Status.str.contains("expired").sum()))
    f1, f2 = st.columns(2)
    cats = sorted(df.Category.unique())
    sel = f1.multiselect("Category", cats, default=cats, key="ov_cat")
    text = f2.text_input("Search item", key="ov_search")
    view = df[df.Category.isin(sel)]
    if text.strip():
        view = view[view.Item.str.contains(text.strip(), case=False, regex=False)]
    st.dataframe(view.drop(columns=["id"]), hide_index=True)
    st.caption("Status counts non-expired lots only. 'Last verified' is the last physical count "
               "or opening entry. Sample stock numbers are placeholders.")

    st.subheader("🚩 Report a problem with an item")
    c1, c2 = st.columns(2)
    item = c1.selectbox("Item", df.Item.tolist(), key="fl_item")
    kind = c2.radio("Problem", ["Container empty", "Running low", "Damaged or expired"],
                    horizontal=True, key="fl_kind")
    note = st.text_input("Note (optional)", key="fl_note")
    if st.button("Send flag to the attender", key="fl_send"):
        iid = int(df[df.Item == item].id.iloc[0])
        ex("INSERT INTO flags(ts,item_id,kind,note,user_email) VALUES (?,?,?,?,?)",
           (now_str(), iid, kind, note.strip(), user["email"]))
        st.toast("Flag sent to the lab attender", icon="🚩")
        st.success(f"Flag sent for {item}: {kind}")
    open_flags = q(
        "SELECT f.ts AS Time, i.name AS Item, f.kind AS Problem, f.note AS Note, "
        "f.user_email AS 'Reported by' FROM flags f JOIN items i ON i.id=f.item_id "
        "WHERE f.resolved=0 ORDER BY f.id DESC LIMIT 10")
    if not open_flags.empty:
        st.write("Open flags:")
        st.dataframe(open_flags, hide_index=True)


def _tab_record(user):
    pr = q("SELECT * FROM practicals ORDER BY name")
    if pr.empty:
        st.info("No practical templates yet. Ask a lecturer to add one.")
        return
    pname = st.selectbox("Practical", pr.name.tolist(), key="ru_practical")
    prow = pr[pr.name == pname].iloc[0]
    pid = int(prow["id"])
    c1, c2 = st.columns(2)
    batch = c1.text_input("Batch name (for example Batch A or Group 3)", key="ru_batch")
    n = int(c2.number_input("Number of students in the batch", min_value=1, max_value=60,
                            value=10, step=1, key="ru_n"))
    tmpl = q(
        "SELECT pi.item_id, i.name, i.unit, pi.per_student FROM practical_items pi "
        "JOIN items i ON i.id=pi.item_id WHERE pi.practical_id=?", (pid,))

    st.markdown("**Chemicals used.** The planned quantity is pre-filled from the template; "
                "edit the actual quantity.")
    h = st.columns([3, 2, 2.5, 2.5, 2.5])
    for col, label in zip(h, ["Item", "Planned", "Actual used", "Measured", "Available"]):
        col.caption(label)
    inputs = []
    for r in tmpl.itertuples():
        planned = round(float(r.per_student) * n, 4)
        avail = available_qty(r.item_id)
        c = st.columns([3, 2, 2.5, 2.5, 2.5])
        c[0].write(f"{r.name} ({r.unit})")
        c[1].write(f"{planned:g}")
        actual = c[2].number_input("Actual", min_value=0.0, value=float(planned), step=0.01,
                                   format="%.2f", key=f"ru_a_{pid}_{r.item_id}_{n}",
                                   label_visibility="collapsed")
        measured = c[3].selectbox("Measured", ["Weighed", "Estimated"],
                                  key=f"ru_m_{pid}_{r.item_id}", label_visibility="collapsed")
        c[4].write(f"{'🟢' if avail >= actual else '🔴'} {avail:g}")
        inputs.append((int(r.item_id), planned, float(actual), measured))

    items_all = q("SELECT id, name, unit FROM items ORDER BY name")
    extra = st.selectbox("Another item used, not in the template (optional)",
                         ["- none -"] + items_all.name.tolist(), key=f"ru_extra_{pid}")
    extra_line = None
    if extra != "- none -":
        erow = items_all[items_all.name == extra].iloc[0]
        e1, e2 = st.columns(2)
        eq = e1.number_input(f"Quantity of {extra} ({erow['unit']})", min_value=0.0, value=0.0,
                             step=0.01, format="%.2f", key=f"ru_eq_{pid}_{erow['id']}")
        em = e2.selectbox("Measured", ["Weighed", "Estimated"], key=f"ru_em_{pid}")
        if eq > 0:
            extra_line = (int(erow["id"]), 0.0, float(eq), em)

    opts = [a.strip() for a in str(prow["apparatus"] or "").split(",") if a.strip()]
    used = st.multiselect("Apparatus and equipment used", opts, default=opts, key=f"ru_app_{pid}")
    breakage = st.text_input("Breakage or problems (optional)", key="ru_break")

    if st.button("💾 Save usage record", type="primary", key="ru_save"):
        lines = [x for x in inputs if x[2] > 0]
        if extra_line:
            lines.append(extra_line)
        dup = q("SELECT id FROM usage_sessions WHERE practical_id=? AND batch_name=? "
                "AND user_email=? AND ts=?", (pid, batch.strip(), user["email"], now_str()))
        if not batch.strip():
            st.error("Enter a batch name.")
        elif not lines:
            st.error("Enter at least one quantity.")
        elif not dup.empty:
            st.warning("This record was just saved. Change the batch name to save another.")
        else:
            ok, res = record_usage(pid, batch.strip(), n, ", ".join(used), breakage.strip(),
                                   user["email"], lines)
            if ok:
                st.success(f"Saved record #{res} for {batch.strip()}. Stock updated.")
                st.toast("Usage recorded and stock updated", icon="🧪")
                st.balloons()
            else:
                names = {int(r.id): (r.name, r.unit) for r in items_all.itertuples()}
                for iid, need_q, avail in res:
                    nm, un = names[iid]
                    st.error(f"{nm}: need {need_q:g} {un}, only {avail:g} {un} available. "
                             "Nothing was saved. Report it from Stock overview and tell the attender.")

    mine = q("SELECT s.id AS ID, s.ts AS Time, p.name AS Practical, s.batch_name AS Batch, "
             "s.status AS Status FROM usage_sessions s JOIN practicals p ON p.id=s.practical_id "
             "WHERE s.user_email=? ORDER BY s.id DESC LIMIT 5", (user["email"],))
    if not mine.empty:
        st.subheader("Your recent records")
        st.dataframe(mine, hide_index=True)


def _tab_verify(user):
    st.caption("Check recorded usage against what was issued, then verify. Verified records are final.")
    ss = q("SELECT s.id, s.ts, p.name AS practical, s.batch_name, s.n_students, s.user_email, "
           "s.status, s.breakage, s.apparatus FROM usage_sessions s "
           "JOIN practicals p ON p.id=s.practical_id ORDER BY s.id DESC LIMIT 20")
    if ss.empty:
        st.info("No usage records yet.")
        return
    for r in ss.itertuples():
        icon = "✅" if r.status == "Verified" else "🕒"
        with st.expander(f"{icon} #{r.id} · {r.practical} · {r.batch_name} · {r.ts}"):
            st.write(f"Recorded by {r.user_email} · {r.n_students} students · {r.status}")
            lines = q("SELECT i.name AS Item, i.unit AS Unit, l.planned AS Planned, "
                      "l.actual AS Actual, ROUND(l.actual-l.planned,3) AS Variance, "
                      "l.measured AS Measured FROM usage_lines l JOIN items i ON i.id=l.item_id "
                      "WHERE l.session_id=?", (int(r.id),))
            st.dataframe(lines, hide_index=True)
            if r.apparatus:
                st.write(f"Apparatus: {r.apparatus}")
            if r.breakage:
                st.write(f"Breakage or problems: {r.breakage}")
            if r.status != "Verified" and st.button("Verify this record", key=f"ver_{r.id}"):
                ex("UPDATE usage_sessions SET status='Verified', verified_by=? WHERE id=?",
                   (user["email"], int(r.id)))
                st.rerun()


def _tab_reports(user):
    df = q("SELECT s.ts AS Time, p.name AS Practical, s.batch_name AS Batch, "
           "s.n_students AS Students, i.name AS Item, i.unit AS Unit, l.planned AS Planned, "
           "l.actual AS Actual, ROUND(l.actual-l.planned,3) AS Variance, l.measured AS Measured, "
           "s.status AS Status FROM usage_lines l JOIN usage_sessions s ON s.id=l.session_id "
           "JOIN practicals p ON p.id=s.practical_id JOIN items i ON i.id=l.item_id "
           "ORDER BY s.id DESC")
    st.subheader("Usage by batch")
    if df.empty:
        st.info("No usage recorded yet. Record a practical first.")
    else:
        pracs = sorted(df.Practical.unique())
        sel = st.multiselect("Practical", pracs, default=pracs, key="rp_pr")
        view = df[df.Practical.isin(sel)]
        st.dataframe(view, hide_index=True)
        tot = view.groupby(["Item", "Unit"], as_index=False)[["Planned", "Actual"]].sum()
        tot["Variance"] = (tot.Actual - tot.Planned).round(3)
        st.write("Total consumption by item:")
        st.dataframe(tot, hide_index=True)
        st.download_button("Download usage (.csv)", df.to_csv(index=False),
                           file_name="Chemical_Usage.csv", mime="text/csv")
        st.caption("Variance is actual minus planned. Large positive values mean wastage or "
                   "a wrong template; check them with the batch.")

    st.subheader("🔮 Forecast: will stock last?")
    pr = q("SELECT id, name FROM practicals ORDER BY name")
    if pr.empty:
        return
    pname = st.selectbox("Practical", pr.name.tolist(), key="fc_pr")
    c1, c2 = st.columns(2)
    batches = int(c1.number_input("Batches still to run", min_value=1, max_value=50, value=6,
                                  step=1, key="fc_b"))
    students = int(c2.number_input("Students per batch", min_value=1, max_value=60, value=10,
                                   step=1, key="fc_s"))
    pid = int(pr[pr.name == pname].id.iloc[0])
    tm = q("SELECT i.name, i.unit, pi.per_student FROM practical_items pi "
           "JOIN items i ON i.id=pi.item_id WHERE pi.practical_id=?", (pid,))
    ov = stock_overview_df().set_index("Item")
    rows = []
    for r in tm.itertuples():
        need = float(r.per_student) * students * batches
        have = float(ov.loc[r.name, "Balance"])
        short = max(0.0, need - have)
        rows.append({"Item": r.name, "Unit": r.unit, "Needed": round(need, 3),
                     "In stock": round(have, 3), "Shortfall": round(short, 3),
                     "Check": "⚠️ Order more" if short > 0 else "✅ Enough"})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Forecast covers this practical only; other practicals draw on the same stock.")


def _tab_templates(user):
    st.caption("Sample templates and quantities are placeholders. Replace them with your lab's real ones.")
    tm = q("SELECT p.id, p.name, p.apparatus FROM practicals p ORDER BY p.name")
    rows = []
    for r in tm.itertuples():
        li = q("SELECT i.name, i.unit, pi.per_student FROM practical_items pi "
               "JOIN items i ON i.id=pi.item_id WHERE pi.practical_id=?", (int(r.id),))
        rows.append({"Practical": r.name, "Apparatus": r.apparatus,
                     "Chemicals per student": "; ".join(
                         f"{x.name} {x.per_student:g} {x.unit}" for x in li.itertuples())})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.subheader("Add a practical template")
    name = st.text_input("Practical name", key="pt_name")
    app = st.text_input("Apparatus and equipment (comma separated)", key="pt_app")
    lines = st.text_area("Chemicals, one per line: item name, quantity per student",
                         key="pt_lines", placeholder="Paracetamol, 0.5\nEthanol, 20")
    if st.button("Save template", key="pt_save"):
        items = q("SELECT id, name FROM items")
        lookup = {r.name.lower(): int(r.id) for r in items.itertuples()}
        parsed, errors = [], []
        for ln in [x for x in lines.splitlines() if x.strip()]:
            parts = ln.rsplit(",", 1)
            try:
                nm, qty = parts[0].strip(), float(parts[1])
                if nm.lower() not in lookup:
                    errors.append(f"Unknown item: {nm}")
                elif qty <= 0:
                    errors.append(f"Quantity must be above 0: {ln}")
                else:
                    parsed.append((lookup[nm.lower()], qty))
            except (IndexError, ValueError):
                errors.append(f"Could not read: {ln}")
        if not name.strip():
            errors.append("Enter a practical name.")
        if not parsed and not errors:
            errors.append("Add at least one chemical.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                pid = ex("INSERT INTO practicals(name,apparatus) VALUES (?,?)",
                         (name.strip(), app.strip()))
                for iid, qty in parsed:
                    ex("INSERT INTO practical_items(practical_id,item_id,per_student) "
                       "VALUES (?,?,?)", (pid, iid, qty))
                st.success("Template saved.")
                st.toast("Practical template added", icon="📝")
            except sqlite3.IntegrityError:
                st.error("A practical with this name already exists.")


def _tab_attender(user):
    st.caption("The attender sets opening stock, receives new lots and reconciles with physical counts. "
               "Every change is a logged transaction; nothing is overwritten.")
    with st.expander("➕ Add a new item"):
        c1, c2, c3, c4 = st.columns(4)
        nm = c1.text_input("Item name", key="at_in")
        cat = c2.selectbox("Category", ["API", "Excipient", "Reagent", "Solvent", "Other"], key="at_ic")
        unit = c3.selectbox("Unit", ["g", "mL", "mg", "L"], key="at_iu")
        mn = c4.number_input("Minimum stock", min_value=0.0, value=0.0, step=1.0, key="at_im")
        if st.button("Add item", key="at_iadd"):
            if not nm.strip():
                st.error("Enter an item name.")
            else:
                try:
                    ex("INSERT INTO items(name,category,unit,min_stock) VALUES (?,?,?,?)",
                       (nm.strip(), cat, unit, float(mn)))
                    st.success(f"Added {nm.strip()}. Now receive a lot to give it stock.")
                except sqlite3.IntegrityError:
                    st.error("This item already exists.")

    items = q("SELECT id, name, unit FROM items ORDER BY name")
    with st.expander("📥 Receive stock or set opening quantity (new lot)"):
        if items.empty:
            st.info("Add an item first.")
        else:
            c1, c2 = st.columns(2)
            it = c1.selectbox("Item", items.name.tolist(), key="at_ri")
            lot_no = c2.text_input("Lot or batch number", key="at_rl")
            c3, c4, c5 = st.columns(3)
            exp = c3.date_input("Expiry date", value=datetime.date.today() + datetime.timedelta(days=365),
                                key="at_re")
            qty = c4.number_input("Quantity received", min_value=0.0, value=0.0, step=1.0, key="at_rq")
            loc = c5.text_input("Location", key="at_rloc")
            if st.button("Save lot", key="at_rsave"):
                if not lot_no.strip() or qty <= 0:
                    st.error("Enter a lot number and a quantity above 0.")
                else:
                    iid = int(items[items.name == it].id.iloc[0])
                    lid = ex("INSERT INTO lots(item_id,lot_no,expiry,location) VALUES (?,?,?,?)",
                             (iid, lot_no.strip(), exp.isoformat(), loc.strip()))
                    ex("INSERT INTO transactions(ts,lot_id,kind,qty,user_email,note) "
                       "VALUES (?,?,?,?,?,?)",
                       (now_str(), lid, "receive", float(qty), user["email"], "Stock received"))
                    st.success(f"Added lot {lot_no.strip()} of {it}.")
                    st.toast("Stock updated", icon="📥")

    lots = lots_df()
    labels = {f"{r.item} · lot {r.lot_no} · exp {r.expiry}": r for r in lots.itertuples()}
    with st.expander("🔢 Physical count (reconcile)", expanded=True):
        if not labels:
            st.info("No lots yet.")
        else:
            pick = st.selectbox("Lot", list(labels), key="at_cl")
            lot = labels[pick]
            st.write(f"Expected balance: **{lot.balance:g} {lot.unit}**")
            counted = st.number_input(f"Counted quantity ({lot.unit})", min_value=0.0,
                                      value=float(lot.balance), step=0.01, format="%.2f",
                                      key=f"at_cq_{lot.lot_id}_{lot.balance}")
            diff = round(float(counted) - float(lot.balance), 6)
            if abs(diff) > 1e-9:
                st.warning(f"Difference: {diff:+g} {lot.unit}. A reason is required.")
            reason = st.text_input("Reason for the difference", key="at_cr")
            if st.button("Save count", key="at_csave"):
                if abs(diff) < 1e-9:
                    ex("INSERT INTO transactions(ts,lot_id,kind,qty,user_email,note) "
                       "VALUES (?,?,?,?,?,?)",
                       (now_str(), int(lot.lot_id), "count", 0.0, user["email"], "Count matched"))
                    st.success("Count matched the ledger. Verification date updated.")
                    st.toast("Verified", icon="✅")
                elif not reason.strip():
                    st.error("Enter a reason for the difference.")
                else:
                    ex("INSERT INTO transactions(ts,lot_id,kind,qty,user_email,note) "
                       "VALUES (?,?,?,?,?,?)",
                       (now_str(), int(lot.lot_id), "adjust", diff, user["email"], reason.strip()))
                    st.success(f"Adjusted by {diff:+g} {lot.unit}. Ledger now matches the count.")
                    st.toast("Stock adjusted", icon="🔢")

    with st.expander("🗑️ Discard expired or damaged stock"):
        if labels:
            pick = st.selectbox("Lot", list(labels), key="at_dl")
            lot = labels[pick]
            dq = st.number_input(f"Quantity to discard ({lot.unit})", min_value=0.0, value=0.0,
                                 step=0.01, format="%.2f", key="at_dq")
            dr = st.text_input("Reason", key="at_dr")
            if st.button("Discard", key="at_dsave"):
                if dq <= 0 or not dr.strip():
                    st.error("Enter a quantity above 0 and a reason.")
                elif dq > lot.balance + 1e-9:
                    st.error(f"Only {lot.balance:g} {lot.unit} in this lot.")
                else:
                    ex("INSERT INTO transactions(ts,lot_id,kind,qty,user_email,note) "
                       "VALUES (?,?,?,?,?,?)",
                       (now_str(), int(lot.lot_id), "discard", -float(dq), user["email"], dr.strip()))
                    st.success("Discard recorded.")

    st.subheader("🚩 Open flags")
    fl = q("SELECT f.id, f.ts, i.name AS item, f.kind, f.note, f.user_email FROM flags f "
           "JOIN items i ON i.id=f.item_id WHERE f.resolved=0 ORDER BY f.id DESC")
    if fl.empty:
        st.info("No open flags.")
    for r in fl.itertuples():
        c1, c2 = st.columns([5, 1])
        c1.write(f"🚩 **{r.item}** · {r.kind} · {r.note or 'no note'} · {r.user_email} · {r.ts}")
        if c2.button("Resolve", key=f"fl_res_{r.id}"):
            ex("UPDATE flags SET resolved=1 WHERE id=?", (int(r.id),))
            st.rerun()


# ----------------------------------------------------------------------------
# Dissertation library
# ----------------------------------------------------------------------------
_STOP = {"and", "the", "for", "with", "from", "that", "this", "are", "was", "not", "but"}


def search_dissertations(query, df=None):
    df = q("SELECT * FROM dissertations") if df is None else df
    terms = [t for t in re.split(r"[^a-z0-9]+", str(query).lower())
             if len(t) > 2 and t not in _STOP]
    if not terms:
        return df

    def score(r):
        title, kw, ab = r.title.lower(), (r.keywords or "").lower(), (r.abstract or "").lower()
        return sum(3 * (t in title) + 2 * (t in kw) + (t in ab) for t in terms)

    out = df.assign(score=df.apply(score, axis=1))
    return out[out.score > 0].sort_values("score", ascending=False)


def related_dissertations(text, limit=3):
    res = search_dissertations(text)
    if "score" not in res.columns or res.empty:
        st.caption("No related dissertations found yet.")
        return
    for r in res.head(limit).itertuples():
        st.markdown(f"- 📄 **{r.title}** ({r.year}) · {r.author}")


def library_page(user):
    role = user["role"]
    st.header("📚 Dissertation Library")
    st.caption("Past dissertations of the department. Prototype: keyword search over title, "
               "keywords and abstract. Semantic search is the next step. Visible to signed-in "
               "institutional users only.")
    df = q("SELECT * FROM dissertations ORDER BY year DESC, title")
    if df.empty:
        st.info("No dissertations yet.")
    else:
        query = st.text_input("🔎 Search (topic, drug, technique)", key="lib_q")
        c1, c2 = st.columns(2)
        years = sorted({int(y) for y in df.year}, reverse=True)
        guides = sorted({g for g in df.guide.dropna()})
        ysel = c1.multiselect("Year", years, default=years, key="lib_y")
        gsel = c2.multiselect("Guide", guides, default=guides, key="lib_g")
        view = df[df.year.isin(ysel) & df.guide.isin(gsel)]
        if query.strip():
            view = search_dissertations(query, view)
        st.write(f"{len(view)} result(s)")
        for r in view.itertuples():
            with st.expander(f"📄 {r.title} ({r.year})"):
                st.write(f"👤 {r.author} · 🎓 Guide: {r.guide}")
                st.write(f"🏷️ {r.keywords}")
                st.write(r.abstract)
                st.write("🔒 Metadata only" if r.access == "Metadata only" else "📬 Full text on request")
                if r.sample:
                    st.caption("Sample entry")
    if role in ("lecturer", "admin"):
        st.subheader("➕ Add a dissertation")
        st.caption("Add real entries only with the department's and author's permission. "
                   "Start with metadata and abstract.")
        title = st.text_input("Title", key="lib_t")
        c1, c2, c3 = st.columns(3)
        author = c1.text_input("Author", key="lib_a")
        year = int(c2.number_input("Year", min_value=2000, max_value=datetime.date.today().year + 1,
                                   value=datetime.date.today().year, step=1, key="lib_yr"))
        guide = c3.text_input("Guide", key="lib_gd")
        kw = st.text_input("Keywords (comma separated)", key="lib_k")
        ab = st.text_area("Abstract", key="lib_ab")
        acc = st.selectbox("Access", ["Metadata only", "Full text on request"], key="lib_ac")
        if st.button("Save dissertation", key="lib_save"):
            if not title.strip() or not author.strip():
                st.error("Title and author are required.")
            else:
                ex("INSERT INTO dissertations(title,author,year,guide,keywords,abstract,access,sample) "
                   "VALUES (?,?,?,?,?,?,?,0)",
                   (title.strip(), author.strip(), year, guide.strip(), kw.strip(), ab.strip(), acc))
                st.success("Dissertation added.")
                st.toast("Added to the library", icon="📚")
    if role == "admin":
        if st.button("Remove all sample entries", key="lib_rmsample"):
            ex("DELETE FROM dissertations WHERE sample=1")
            st.rerun()


# ----------------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------------
def admin_page(user):
    st.header("🛠️ Admin")
    st.subheader("👥 Users and roles")
    st.dataframe(q("SELECT email AS Email, name AS Name, role AS Role FROM users ORDER BY role, email"),
                 hide_index=True)
    st.caption("Anyone who signs in with a valid institutional mail id becomes a student. "
               "Change roles here.")
    c1, c2, c3 = st.columns(3)
    email = c1.text_input("Email", key="ad_email", placeholder=f"name@{ALLOWED_DOMAIN}")
    name = c2.text_input("Name", key="ad_name")
    role = c3.selectbox("Role", ROLES, key="ad_role")
    if st.button("Add or update user", key="ad_save"):
        e = email.strip().lower()
        if not re.fullmatch(r"[a-z0-9._+\-]+@" + re.escape(ALLOWED_DOMAIN), e):
            st.error(f"Email must end with @{ALLOWED_DOMAIN}.")
        elif e == user["email"] and role != "admin":
            st.error("You cannot remove your own admin role.")
        else:
            ex("INSERT INTO users(email,name,role) VALUES (?,?,?) "
               "ON CONFLICT(email) DO UPDATE SET name=excluded.name, role=excluded.role",
               (e, name.strip() or _name_from_email(e), role))
            st.success(f"Saved {e} as {ROLE_LABEL[role]}.")
            st.rerun()

    st.subheader("⚠️ Demo data")
    st.caption("Reload the sample stock, practicals and dissertations before a demo.")
    confirm = st.checkbox("I understand this erases all inventory, usage, flags and dissertation data",
                          key="ad_confirm")
    if st.button("Reset to sample data", key="ad_reset", disabled=not confirm):
        reset_demo_data()
        st.success("Sample data reloaded.")
        st.toast("Demo data reset", icon="♻️")
