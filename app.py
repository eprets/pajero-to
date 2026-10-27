import json
from datetime import date, datetime
import io

import pandas as pd
import streamlit as st

from schedule import build_matrix, mileage_for
from storage import load_data, save_data

st.set_page_config(page_title="ТО Pajero IV", page_icon="🚙", layout="wide")

@st.cache_data
def load_regulations():
    with open("regulations.json", "r", encoding="utf-8") as f:
        return json.load(f)

regulations = load_regulations()
interval = regulations["interval"]
N = interval["max_to"]
base_matrix = build_matrix(regulations)

if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data
data.setdefault("to", {})
data.setdefault("manual", {})
data.setdefault("custom_ops", {})
data.setdefault("overrides", {})

v = regulations["vehicle"]
st.title(f"🚙 Лист ТО — {v['brand']} {v['model']}, {v['year']}")
st.caption(f"VIN: {v['vin']}")

# ---------- Легенда ----------
with st.expander("ℹ️ Расшифровка обозначений (I, R, L, C)", expanded=False):
    legend = regulations.get("legend", {})
    st.markdown(f"""
    * **I** — {legend.get('I', 'Проверка, затем при необходимости очистка, регулировка или замена')};
    * **R** — {legend.get('R', 'Замена')};
    * **L** — {legend.get('L', 'Смазка')};
    * **C** — {legend.get('C', 'Очистка')}.
    
    *Таблица сформирована по листу «Регламент»: ТО-0 = 1 000 км, далее шаг 10 000 км; всего 56 ТО (до 550 000 км).*
    """)

# ---------- Уведомления ----------
current_km = st.number_input(
    "Текущий пробег автомобиля, км", min_value=0, step=1000,
    value=int(data.get("current_km", 0)), key="current_km_input"
)
if current_km != data.get("current_km"):
    data["current_km"] = current_km
    save_data(data)

reminders = []
# Цикл от 0 до N-1 (56 штук)
for to_num in range(0, N):
    info = data["to"].get(str(to_num), {})
    if not info.get("date"):
        continue
    planned_km = mileage_for(to_num, interval)
    if current_km >= planned_km - 1000:
        reminders.append(f"⚠️ ТО-{to_num} ({planned_km:,} км) — пробег уже {current_km:,} км".replace(",", " "))

next_to = None
for to_num in range(0, N):
    if not data["to"].get(str(to_num), {}).get("date"):
        next_to = to_num
        break
if next_to is not None:
    planned_km = mileage_for(next_to, interval)
    left = planned_km - current_km
    if left > 0:
        reminders.append(f"📅 Следующее ТО-{next_to}: {planned_km:,} км (осталось ~{left:,} км)".replace(",", " "))

if reminders:
    for r in reminders:
        st.warning(r)
else:
    st.info("Пока нет активных напоминаний.")

st.divider()

# ---------- Вкладки ----------
tab1, tab2, tab3, tab4 = st.tabs(["📋 Выполнение ТО", "⚙️ Мои операции", "📊 Полная сводка", "📥 Экспорт"])

# ================== ВКЛАДКА 1: ВЫПОЛНЕНИЕ ТО ==================
with tab1:
    st.subheader("Регламентные работы")
    
    # Цикл от 0 до N-1
    to_options = [f"ТО-{i} — {mileage_for(i, interval):,} км".replace(",", " ") for i in range(0, N)]
    selected_label = st.selectbox("Выберите ТО", to_options)
    selected_to = int(selected_label.split("—")[0].replace("ТО-", "").strip())

    entry = data["to"].setdefault(str(selected_to), {"date": "", "fact_km": 0, "done_works": []})

    col1, col2 = st.columns(2)
    with col1:
        d_val = None
        if entry.get("date"):
            try: d_val = datetime.fromisoformat(entry["date"]).date()
            except ValueError: pass
        new_date = st.date_input("Дата выполнения ТО", value=d_val)
    with col2:
        new_km = st.number_input("Фактический пробег, км", min_value=0, step=1000, value=int(entry.get("fact_km", 0)))

    if new_date and new_date.isoformat() != entry.get("date"):
        entry["date"] = new_date.isoformat()
    if int(new_km) != int(entry.get("fact_km", 0)):
        entry["fact_km"] = int(new_km)

    if st.button("💾 Сохранить дату и пробег"):
        ok, msg = save_data(data)
        st.success(msg) if ok else st.error(msg)

    st.markdown(f"**Плановый пробег ТО-{selected_to}:** {mileage_for(selected_to, interval):,} км".replace(",", " "))

    works = list(base_matrix.get(selected_to, []))
    
    for op_id, op in data["custom_ops"].items():
        apply = False
        if op["type"] == "all": apply = True
        elif op["type"] == "positions" and selected_to in op["positions"]: apply = True
        if apply:
            works.append({
                "id": op_id, "group": op["group"], "name": op["name"],
                "part": data["overrides"].get(op_id, {}).get("part", ""),
                "analog": data["overrides"].get(op_id, {}).get("analog", ""),
                "schedule_code": op.get("code", "I")
            })

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
                    value=checked, key=f"cb_{selected_to}_{w['id']}"
                )
                if new_checked != checked:
                    changed = True
                    if new_checked: done_set.add(key)
                    else: done_set.discard(key)

        if changed:
            entry["done_works"] = list(done_set)
            save_data(data)
            st.rerun()

    replacements = [w for w in works if w["schedule_code"] == "R" and (w["part"] or w["analog"] or w["id"] in data["overrides"])]
    if replacements:
        st.markdown("**📦 Материалы для замены (можно редактировать)**")
        st.caption("Впишите свои номера или аналоги в таблицу и нажмите «Сохранить изменения материалов».")
        
        rep_data = []
        for w in replacements:
            ov = data["overrides"].get(w["id"], {})
            rep_data.append({
                "id": w["id"],
                "Работа": w["name"],
                "Каталожный номер": ov.get("part", w["part"]),
                "Аналог": ov.get("analog", w["analog"]),
            })
        
        df_rep = pd.DataFrame(rep_data)
        edited_df = st.data_editor(
            df_rep,
            column_config={
                "id": None,
                "Работа": st.column_config.TextColumn(disabled=True),
                "Каталожный номер": st.column_config.TextColumn("Каталожный номер"),
                "Аналог": st.column_config.TextColumn("Аналог"),
            },
            hide_index=True,
            use_container_width=True,
            key=f"editor_{selected_to}"
        )
        
        if st.button("💾 Сохранить изменения материалов"):
            for _, row in edited_df.iterrows():
                op_id = row["id"]
                data["overrides"].setdefault(op_id, {})
                data["overrides"][op_id]["part"] = row["Каталожный номер"]
                data["overrides"][op_id]["analog"] = row["Аналог"]
            save_data(data)
            st.success("Материалы обновлены!")
            st.rerun()

    st.markdown("**➕ Ручные материалы (только для этого ТО)**")
    manual_rows = data["manual"].setdefault(str(selected_to), [])
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
        if st.form_submit_button("Добавить строку") and m_mat:
            manual_rows.append({"material": m_mat, "catalog": m_cat, "qty_price": m_qty, "done": bool(m_done)})
            save_data(data)
            st.rerun()


# ================== ВКЛАДКА 2: МОИ ОПЕРАЦИИ ==================
with tab2:
    st.subheader("Добавить свою операцию в регламент")
    st.info("Здесь вы можете добавить операцию, которой нет в заводском регламенте.")

    c3, c4 = st.columns(2)
    op_type = c3.radio("Когда выполнять?", ["Каждое ТО", "Только на выбранных ТО"], key="op_type_radio")
    
    code_options = {
        "I — Проверка, затем при необходимости очистка, регулировка или замена": "I",
        "R — Замена": "R",
        "L — Смазка": "L",
        "C — Очистка": "C"
    }
    selected_code_label = c4.selectbox("Тип отметки", list(code_options.keys()), key="op_code_radio")
    op_code = code_options[selected_code_label]
    
    to_selection = []
    if op_type == "Только на выбранных ТО":
        to_selection = st.multiselect("Выберите номера ТО (можно несколько)", list(range(0, N)), default=[0])

    with st.form("add_custom_op"):
        c1, c2 = st.columns(2)
        op_name = c1.text_input("Название операции")
        op_group = c2.selectbox("Группа", ["Операции под капотом", "Операции под автомобилем", "Операции внутри автомобиля", "Дополнительные операции", "Свои операции"])
        
        part = st.text_input("Каталожный номер (если есть)")
        analog = st.text_input("Аналог (если есть)")

        if st.form_submit_button("Добавить операцию") and op_name:
            op_id = f"custom_{len(data['custom_ops'])}_{date.today().strftime('%Y%m%d%H%M%S')}"
            data["custom_ops"][op_id] = {
                "name": op_name,
                "group": op_group,
                "type": "all" if op_type == "Каждое ТО" else "positions",
                "positions": to_selection if op_type != "Каждое ТО" else [],
                "code": op_code
            }
            if part or analog:
                data["overrides"][op_id] = {"part": part, "analog": analog}
            save_data(data)
            st.success(f"Операция «{op_name}» добавлена!")
            st.rerun()

    st.divider()
    st.subheader("Мои добавленные операции")
    if not data["custom_ops"]:
        st.write("Пока нет добавленных операций.")
    else:
        for op_id, op in list(data["custom_ops"].items()):
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.write(f"**[{op['code']}] {op['name']}** *(Группа: {op['group']})*")
            schedule_txt = "Каждое ТО" if op["type"] == "all" else f"ТО: {', '.join(map(str, op['positions']))}"
            c2.write(schedule_txt)
            if c3.button("Удалить", key=f"del_op_{op_id}"):
                del data["custom_ops"][op_id]
                for to_info in data["to"].values():
                    done = to_info.get("done_works", [])
                    to_info["done_works"] = [w for w in done if not w.endswith(op_id)]
                save_data(data)
                st.rerun()


# ================== ВКЛАДКА 3: ПОЛНАЯ СВОДКА ==================
with tab3:
    st.subheader("Сводная таблица по всем ТО")
    
    view_mode = st.radio(
        "Что показывать?",
        ["Весь регламент", "Только заполненные ТО (где есть дата)", "Только выполненные работы"],
        horizontal=True
    )
    
    search_query = st.text_input("🔍 Поиск по работам, материалам или номерам ТО", placeholder="Например: Ремень, Масло, ТО-9...")

    export_rows = []
    found_any = False

    # Цикл от 0 до N-1
    for to_num in range(0, N):
        info = data["to"].get(str(to_num), {})
        done_set = set(info.get("done_works", []))
        
        works = list(base_matrix.get(to_num, []))
        for op_id, op in data["custom_ops"].items():
            apply = False
            if op["type"] == "all": apply = True
            elif op["type"] == "positions" and to_num in op["positions"]: apply = True
            if apply:
                works.append({
                    "id": op_id, "group": op["group"], "name": op["name"],
                    "part": data["overrides"].get(op_id, {}).get("part", ""),
                    "analog": data["overrides"].get(op_id, {}).get("analog", ""),
                    "schedule_code": op.get("code", "I")
                })

        if view_mode == "Только заполненные ТО (где есть дата)" and not info.get("date"):
            continue
            
        works_to_show = works
        if view_mode == "Только выполненные работы":
            works_to_show = [w for w in works if f"w_{to_num}_{w['id']}" in done_set]
            if not works_to_show:
                continue

        grouped = {}
        for w in works_to_show:
            grouped.setdefault(w["group"], []).append(w)

        text_works = ""
        for group, items in grouped.items():
            text_works += f"== {group} ==\n"
            for w in items:
                mark = "X" if f"w_{to_num}_{w['id']}" in done_set else " "
                text_works += f"[{mark}] [{w['schedule_code']}] {w['name']}\n"
            text_works += "\n"

        search_text = f"ТО-{to_num} {text_works}".lower()
        if search_query and search_query.lower() not in search_text:
            continue

        found_any = True
        export_rows.append({
            "ТО": f"ТО-{to_num}",
            "План, км": mileage_for(to_num, interval),
            "Дата": info.get("date", ""),
            "Факт, км": info.get("fact_km", ""),
            "Работы (выполнено [X] / не выполнено [ ])": text_works.strip()
        })

        with st.container(border=True):
            col_h1, col_h2, col_h3, col_h4 = st.columns(4)
            col_h1.markdown(f"#### **ТО-{to_num}**")
            col_h2.markdown(f"**План:** {mileage_for(to_num, interval):,} км".replace(",", " "))
            col_h3.markdown(f"**Дата:** {info.get('date', '—')}")
            col_h4.markdown(f"**Факт:** {info.get('fact_km', '—')} км")
            
            col_w, col_m = st.columns([3, 2])
            
            with col_w:
                st.markdown("**Регламентные работы:**")
                changed = False
                for group, items in grouped.items():
                    st.markdown(f"<span style='color: #2f75b5; font-weight: bold; font-size: 14px;'>{group}</span>", unsafe_allow_html=True)
                    for w in items:
                        key = f"w_{to_num}_{w['id']}"
                        checked = key in done_set
                        new_checked = st.checkbox(
                            f"[{w['schedule_code']}] {w['name']}", 
                            value=checked, 
                            key=f"sum_cb_{to_num}_{w['id']}"
                        )
                        if new_checked != checked:
                            changed = True
                            if new_checked: done_set.add(key)
                            else: done_set.discard(key)

                if changed:
                    entry = data["to"].setdefault(str(to_num), {"date": "", "fact_km": 0, "done_works": []})
                    entry["done_works"] = list(done_set)
                    save_data(data)
                    st.rerun()
            
            with col_m:
                st.markdown("**Замены / материалы:**")
                has_materials = False
                for w in works_to_show:
                    if w["schedule_code"] == "R" and (w.get("part") or w.get("analog")):
                        has_materials = True
                        ov = data["overrides"].get(w["id"], {})
                        part = ov.get("part", w["part"])
                        analog = ov.get("analog", w["analog"])
                        st.markdown(f"<div style='margin-bottom: 5px;'><b>{w['name']}</b><br><span style='color: gray; font-size: 12px;'>{part or '—'} {(' / ' + analog) if analog else ''}</span></div>", unsafe_allow_html=True)
                if not has_materials:
                    st.markdown("<span style='color: gray;'>—</span>", unsafe_allow_html=True)

    st.divider()
    df_export = pd.DataFrame(export_rows)
    
    if not found_any:
        st.warning("По вашему запросу ничего не найдено.")
    else:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='ТО Сводка')
        
        st.download_button(
            label="⬇ Экспорт этой сводки в Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="Pajero_TO_Summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ================== ВКЛАДКА 4: ЭКСПОРТ ==================
with tab4:
    st.subheader("Краткий экспорт (только отметки)")
    
    def build_export_df():
        rows = []
        # Цикл от 0 до N-1
        for to_num in range(0, N):
            info = data["to"].get(str(to_num), {})
            works = list(base_matrix.get(to_num, []))
            for op_id, op in data["custom_ops"].items():
                apply = False
                if op["type"] == "all": apply = True
                elif op["type"] == "positions" and to_num in op["positions"]: apply = True
                if apply:
                    works.append({"name": op["name"], "schedule_code": op["code"]})
            
            works_txt = "; ".join(f"[{w['schedule_code']}] {w['name']}" for w in works) or "—"
            
            rows.append({
                "ТО": f"ТО-{to_num}",
                "Дата": info.get("date", ""),
                "План, км": mileage_for(to_num, interval),
                "Факт, км": info.get("fact_km", ""),
                "Работы": works_txt,
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

    with st.expander("⚠️ Служебное"):
        if st.button("Сбросить абсолютно все данные (включая свои операции)"):
            st.session_state.data = {}
            save_data({})
            st.success("Все данные удалены.")
            st.rerun()