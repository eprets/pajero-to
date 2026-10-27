import json
from datetime import date, datetime

import pandas as pd
import streamlit as st

from schedule import build_matrix, mileage_for
from storage import load_data, save_data

st.set_page_config(page_title="ТО Pajero IV", page_icon="🚙", layout="wide")

# ---------- Загрузка ----------
@st.cache_data
def load_regulations():
    with open("regulations.json", "r", encoding="utf-8") as f:
        return json.load(f)

regulations = load_regulations()
interval = regulations["interval"]
N = interval["max_to"]
matrix = build_matrix(regulations)

if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data
data.setdefault("to", {})          # {str(to_num): {"date": "...", "fact_km": int, "done_works": [id,...]}}
data.setdefault("manual", {})      # {str(to_num): [ {id, material, catalog, qty_price, done} ]}

# ---------- Заголовок ----------
v = regulations["vehicle"]
st.title(f"🚙 Лист ТО — {v['brand']} {v['model']}, {v['year']}")
st.caption(f"VIN: {v['vin']} · ТО-1 = {interval['first_to_km']:,} км, шаг {interval['step_km']:,} км, всего ТО-{N}".replace(",", " "))

# ---------- Уведомления ----------
st.subheader("🔔 Напоминания")

current_km = st.number_input(
    "Текущий пробег автомобиля, км",
    min_value=0, step=1000,
    value=int(data.get("current_km", 0)),
    key="current_km_input",
)
if current_km != data.get("current_km"):
    data["current_km"] = current_km
    save_data(data)

reminders = []
for to_num in range(1, N + 1):
    info = data["to"].get(str(to_num), {})
    if not info.get("date"):
        continue
    planned_km = mileage_for(to_num, interval)
    if current_km >= planned_km - 1000:
        reminders.append(f"⚠️ ТО-{to_num} ({planned_km:,} км) — пробег уже {current_km:,} км".replace(",", " "))

# Ближайшее будущее ТО
next_to = None
for to_num in range(1, N + 1):
    if not data["to"].get(str(to_num), {}).get("date"):
        next_to = to_num
        break
if next_to:
    planned_km = mileage_for(next_to, interval)
    left = planned_km - current_km
    if left > 0:
        reminders.append(f"📅 Следующее ТО-{next_to}: {planned_km:,} км (осталось ~{left:,} км)".replace(",", " "))

if reminders:
    for r in reminders:
        st.warning(r)
else:
    st.info("Пока нет активных напоминаний. Заполните даты и пробег в таблице ниже.")

st.divider()

# ---------- Выбор ТО ----------
st.subheader("📋 Регламентные работы")
to_options = [f"ТО-{i} — {mileage_for(i, interval):,} км".replace(",", " ") for i in range(1, N + 1)]
selected_label = st.selectbox("Выберите ТО", to_options)
selected_to = int(selected_label.split("—")[0].replace("ТО-", "").strip())

# ---------- Данные выбранного ТО ----------
entry = data["to"].setdefault(str(selected_to), {"date": "", "fact_km": 0, "done_works": []})

col1, col2 = st.columns(2)
with col1:
    d_val = None
    if entry.get("date"):
        try:
            d_val = datetime.fromisoformat(entry["date"]).date()
        except ValueError:
            d_val = None
    new_date = st.date_input("Дата выполнения ТО", value=d_val)
with col2:
    new_km = st.number_input(
        "Фактический пробег, км",
        min_value=0, step=1000,
        value=int(entry.get("fact_km", 0)),
    )

if new_date and new_date.isoformat() != entry.get("date"):
    entry["date"] = new_date.isoformat()
if int(new_km) != int(entry.get("fact_km", 0)):
    entry["fact_km"] = int(new_km)

if st.button("💾 Сохранить дату и пробег"):
    ok, msg = save_data(data)
    st.success(msg) if ok else st.error(msg)

st.markdown(f"**Плановый пробег ТО-{selected_to}:** {mileage_for(selected_to, interval):,} км".replace(",", " "))

# ---------- Работы по выбранному ТО ----------
works = matrix.get(selected_to, [])
if not works:
    st.info("Для этого ТО регламентных работ нет.")
else:
    grouped = {}
    for w in works:
        grouped.setdefault(w["group"], []).append(w)

    done_set = set(entry.get("done_works", []))
    changed = False

    for group, items in grouped.items():
        st.markdown(f"**{group}**")
        for w in items:
            key = f"w_{selected_to}_{w['id']}"
            checked = key in done_set
            new_checked = st.checkbox(
                f"[{w['schedule_code']}] {w['name']}" + (f" — {w['part']}" if w["part"] else ""),
                value=checked,
                key=f"cb_{selected_to}_{w['id']}",
            )
            if new_checked != checked:
                changed = True
                if new_checked:
                    done_set.add(key)
                else:
                    done_set.discard(key)

    if changed:
        entry["done_works"] = list(done_set)
        save_data(data)
        st.rerun()

# ---------- Материалы для замены ----------
replacements = [w for w in works if w["schedule_code"] == "R" and (w["part"] or w["analog"])]
if replacements:
    st.markdown("**📦 Материалы для замены (по регламенту)**")
    rep_rows = []
    for w in replacements:
        rep_rows.append({
            "Работа": w["name"],
            "Каталожный номер": w["part"],
            "Аналог": w["analog"],
        })
    st.dataframe(pd.DataFrame(rep_rows), use_container_width=True, hide_index=True)

# ---------- Ручные строки ----------
st.markdown("**➕ Ручные материалы / запчасти**")
manual_rows = data["manual"].setdefault(str(selected_to), [])

# Удаление
if manual_rows:
    for i, row in enumerate(list(manual_rows)):
        c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 1, 1])
        c1.write(row.get("material", ""))
        c2.write(row.get("catalog", ""))
        c3.write(row.get("qty_price", ""))
        c4.write("✅" if row.get("done") else "")
        if c5.button("❌", key=f"del_{selected_to}_{i}"):
            manual_rows.pop(i)
            save_data(data)
            st.rerun()

with st.form(f"manual_form_{selected_to}", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([3, 3, 2, 1])
    m_mat = c1.text_input("Материал / запчасть")
    m_cat = c2.text_input("Каталожный номер")
    m_qty = c3.text_input("Кол-во / цена")
    m_done = c4.checkbox("Выполнено")
    submitted = st.form_submit_button("Добавить строку")
    if submitted and m_mat:
        manual_rows.append({
            "material": m_mat,
            "catalog": m_cat,
            "qty_price": m_qty,
            "done": bool(m_done),
        })
        save_data(data)
        st.rerun()

st.divider()

# ---------- Экспорт ----------
st.subheader("⬇ Экспорт")

def build_export_df():
    rows = []
    for to_num in range(1, N + 1):
        info = data["to"].get(str(to_num), {})
        works_at = matrix.get(to_num, [])
        works_txt = "; ".join(f"[{w['schedule_code']}] {w['name']}" for w in works_at) or "—"
        reps = [w for w in works_at if w["schedule_code"] == "R" and w["part"]]
        parts_txt = "; ".join(f"{w['name']}: {w['part']}" for w in reps) or "—"
        rows.append({
            "ТО": f"ТО-{to_num}",
            "Дата": info.get("date", ""),
            "План, км": mileage_for(to_num, interval),
            "Факт, км": info.get("fact_km", ""),
            "Работы": works_txt,
            "Материалы": parts_txt,
            "Отмечено работ": len(info.get("done_works", [])),
        })
    return pd.DataFrame(rows)

df_export = build_export_df()
st.download_button(
    "⬇ Скачать CSV (Excel-совместимый)",
    data=df_export.to_csv(index=False).encode("utf-8-sig"),
    file_name="Pajero_TO.csv",
    mime="text/csv",
)
st.download_button(
    "⬇ Скачать XLSX",
    data=__import__("io").BytesIO(
        df_export.to_excel(
            __import__("io").BytesIO(),
            index=False,
            engine="openpyxl",
        ).getvalue()
    ).getvalue() if False else b"",
    file_name="Pajero_TO.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    disabled=True,
    help="Для XLSX нужен openpyxl — используйте CSV выше или добавьте 'openpyxl' в requirements.txt",
)

# ---------- Сброс ----------
with st.expander("⚠️ Служебное"):
    if st.button("Сбросить все отметки"):
        data["to"] = {}
        data["manual"] = {}
        save_data(data)
        st.session_state.data = data
        st.success("Все отметки сброшены.")
        st.rerun()