import streamlit as st
import json
import uuid
import hashlib
import re
import plotly.graph_objects as go
import psycopg2

from our_numbers import yager_method
from intervals import Interval, interval_yager_method
from fuzzy import FuzzyTrapezoid, fuzzy_yager_method
from linguistic import yager_method_linguistic
from sensitivity_numbers import sensitivity_importance_numeric, sensitivity_ratings_numeric
from sensitivity_intervals import sensitivity_importance_interval, sensitivity_ratings_interval
from sensitivity_fuzzy import sensitivity_importance_fuzzy, sensitivity_ratings_fuzzy
from sensitivity_linguistic import sensitivity_importance_linguistic, sensitivity_ratings_linguistic



def get_db_connection():
    try:
        url = st.secrets["connections"]["postgresql"]["url"]
        conn = psycopg2.connect(url)
        return conn
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return False
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            view_code TEXT UNIQUE NOT NULL,
            edit_code TEXT NOT NULL,
            delete_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            room_id TEXT NOT NULL,
            page_num INTEGER NOT NULL,
            type TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    c.close()
    conn.close()
    return True

def create_room():
    room_id = str(uuid.uuid4())[:8]
    view_code = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6]
    edit_code = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6]
    delete_code = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6]
    conn = get_db_connection()
    if not conn:
        return None, None, None, None
    c = conn.cursor()
    c.execute("INSERT INTO rooms (room_id, view_code, edit_code, delete_code) VALUES (%s, %s, %s, %s)", (room_id, view_code, edit_code, delete_code))
    conn.commit()
    c.close()
    conn.close()
    return room_id, view_code, edit_code, delete_code

def get_room(view_code):
    conn = get_db_connection()
    if not conn:
        return None
    c = conn.cursor()
    c.execute("SELECT * FROM rooms WHERE view_code = %s", (view_code,))
    row = c.fetchone()
    c.close()
    conn.close()
    return row

def get_room_by_id(room_id):
    conn = get_db_connection()
    if not conn:
        return None
    c = conn.cursor()
    c.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
    row = c.fetchone()
    c.close()
    conn.close()
    return row

def serialize_data(obj):
    """Преобразует объекты Interval и FuzzyTrapezoid в списки"""
    if isinstance(obj, Interval):
        return [obj.left, obj.right]
    if isinstance(obj, FuzzyTrapezoid):
        return [obj.x1, obj.x2, obj.x3, obj.x4]
    if isinstance(obj, dict):
        return {k: serialize_data(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize_data(item) for item in obj]
    return obj

def serialize_for_json(obj):
    if isinstance(obj, Interval):
        return {'__type__': 'Interval', 'left': obj.left, 'right': obj.right}
    if isinstance(obj, FuzzyTrapezoid):
        return {'__type__': 'FuzzyTrapezoid', 'x1': obj.x1, 'x2': obj.x2, 'x3': obj.x3, 'x4': obj.x4}
    return obj

def deserialize_data(obj):
    """Восстанавливает объекты Interval и FuzzyTrapezoid из списков"""
    if isinstance(obj, list):
        if len(obj) == 2 and all(isinstance(x, (int, float)) for x in obj):
            return Interval(obj[0], obj[1])
        if len(obj) == 4 and all(isinstance(x, (int, float)) for x in obj):
            return FuzzyTrapezoid(obj[0], obj[1], obj[2], obj[3])
        return [deserialize_data(item) for item in obj]
    if isinstance(obj, dict):
        return {k: deserialize_data(v) for k, v in obj.items()}
    return obj

def deserialize_from_json(obj):
    if isinstance(obj, dict) and '__type__' in obj:
        if obj['__type__'] == 'Interval':
            return Interval(obj['left'], obj['right'])
        if obj['__type__'] == 'FuzzyTrapezoid':
            return FuzzyTrapezoid(obj['x1'], obj['x2'], obj['x3'], obj['x4'])
    return obj

def save_page(room_id, page_num, typ, data):
    conn = get_db_connection()
    if not conn:
        return False
    c = conn.cursor()
    if typ in ['interval', 'fuzzy']:
        save_data = serialize_data(data)
    else:
        save_data = data
    c.execute("INSERT INTO pages (room_id, page_num, type, data) VALUES (%s, %s, %s, %s)",
        (room_id, page_num, typ, json.dumps(save_data, default=str)))
    conn.commit()
    c.close()
    conn.close()
    return True

def get_pages(room_id):
    conn = get_db_connection()
    if not conn:
        return []
    c = conn.cursor()
    c.execute("SELECT page_num, type, data FROM pages WHERE room_id = %s ORDER BY page_num", (room_id,))
    rows = c.fetchall()
    c.close()
    conn.close()
    result = []
    for row in rows:
        data = json.loads(row[2])
        if row[1] in ['interval', 'fuzzy']:
            data = deserialize_data(data)
        result.append((row[0], row[1], data))
    return result

def get_max_page(room_id):
    conn = get_db_connection()
    if not conn:
        return 0
    c = conn.cursor()
    c.execute("SELECT MAX(page_num) FROM pages WHERE room_id = %s", (room_id,))
    row = c.fetchone()
    c.close()
    conn.close()
    return row[0] if row[0] else 0

def delete_page(room_id, page_num):
    conn = get_db_connection()
    if not conn:
        return False
    c = conn.cursor()
    c.execute("DELETE FROM pages WHERE room_id = %s AND page_num = %s", (room_id, page_num))
    conn.commit()
    c.close()
    conn.close()
    return True

def delete_room(room_id):
    conn = get_db_connection()
    if not conn:
        return False
    c = conn.cursor()
    c.execute("DELETE FROM pages WHERE room_id = %s", (room_id,))
    c.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
    conn.commit()
    c.close()
    conn.close()
    return True

def main():
    st.set_page_config(page_title="Метод Яджера", layout="wide")
    init_db()
    if 'room_id' not in st.session_state:
        st.session_state.room_id = None
    if 'view_page' not in st.session_state:
        st.session_state.view_page = None
    if 'load_page_to_calc' not in st.session_state:
        st.session_state.load_page_to_calc = None
    if 'calc_result' not in st.session_state:
        st.session_state.calc_result = None
    with st.sidebar:
        st.title("Меню")
        if st.session_state.room_id is None:
            if st.button("Одиночный режим"):
                st.session_state.room_id = "single"
                st.rerun()
            if st.button("Создать комнату"):
                rid, v, e, d = create_room()
                if rid:
                    st.session_state.room_id = rid
                    st.session_state.view_code = v
                    st.session_state.edit_code = e
                    st.session_state.delete_code = d
                    st.session_state.show_codes = True
                    st.rerun()
            code = st.text_input("Код комнаты")
            if st.button("Войти") and code:
                room = get_room(code)
                if room:
                    st.session_state.room_id = room[0]
                    st.session_state.view_code = code
                    st.session_state.edit_code = room[2]
                    st.session_state.delete_code = room[3]
                    st.rerun()
        else:
            if st.session_state.room_id == "single":
                st.success("Одиночный режим")
            else:
                st.success(f"Комната: {st.session_state.view_code}")
                if st.session_state.get('show_codes'):
                    st.warning("СОХРАНИТЕ КОДЫ!")
                    st.code(f"Вход: {st.session_state.view_code}")
                    st.code(f"Редактирование: {st.session_state.edit_code}")
                    st.code(f"Удаление: {st.session_state.delete_code}")
                    if st.button("Скрыть"):
                        st.session_state.show_codes = False
                        st.rerun()
                with st.expander("Меню"):
                    st.markdown("### Экспорт/Импорт комнаты")
                    if st.button("Экспортировать комнату"):
                        room_id = st.session_state.room_id
                        pages = get_pages(room_id)
                        room_info = get_room_by_id(room_id)
                        export_data = {
                            'room_id': room_id,
                            'view_code': st.session_state.view_code,
                            'edit_code': st.session_state.edit_code,
                            'delete_code': st.session_state.delete_code,
                            'pages': pages
                        } 
                        json_str = json.dumps(export_data, default=serialize_for_json, ensure_ascii=False)
                        st.download_button(
                            label="Скачать JSON",
                            data=json_str,
                            file_name=f"room_{st.session_state.view_code}.json",
                            mime="application/json"
                        )
                    uploaded_file = st.file_uploader("Выберите JSON файл", type=['json'])
                    if uploaded_file is not None:
                        if st.button("Подтвердить импорт", key="confirm_import"):
                            import_data = json.load(uploaded_file, object_hook=deserialize_from_json)
                            if 'pages' in import_data and 'view_code' in import_data:
                                new_rid, new_view, new_edit, new_delete = create_room()
                                for page_num, typ, data in import_data['pages']:
                                    save_page(new_rid, page_num, typ, data)
                                st.success(f"Импортировано! Код входа: {new_view}")
                                st.session_state.room_id = new_rid
                                st.session_state.view_code = new_view
                                st.session_state.edit_code = new_edit
                                st.session_state.delete_code = new_delete
                                st.rerun()
                    else:
                        st.error("Неверный формат файла")
                    del_page = st.number_input("Номер страницы", 1, 999, key="del_num")
                    edit_code = st.text_input("Код редактирования", type="password")
                    if st.button("Удалить страницу"):
                        if edit_code == st.session_state.edit_code:
                            delete_page(st.session_state.room_id, del_page)
                            st.rerun()
                    del_code = st.text_input("Код удаления комнаты", type="password")
                    if st.button("Удалить комнату"):
                        if del_code == st.session_state.delete_code:
                            delete_room(st.session_state.room_id)
                            st.session_state.room_id = None
                            st.rerun()
            if st.button("Выйти"):
                st.session_state.room_id = None
                st.rerun()
            if st.session_state.room_id != "single":
                st.markdown("---")
                st.markdown("### История")
                for page_num, typ, data in get_pages(st.session_state.room_id):
                    if st.button(f"Стр.{page_num} - {typ}"):
                        st.session_state.view_page = (page_num, typ, data)
                        st.rerun()
    if st.session_state.room_id is None:
        st.info("Выберите режим")
        return
    st.title("Метод Яджера")
    if st.session_state.view_page:
        page_num, typ, data = st.session_state.view_page
        st.info(f"Просмотр страницы {page_num} (тип: {typ})")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Назад"):
                st.session_state.view_page = None
                st.rerun()
        with col2:
            if st.button("Загрузить данные в новый расчет"):
                st.session_state.load_page_to_calc = (page_num, typ, data)
                st.session_state.view_page = None
                st.rerun()
        st.markdown("### Альтернативы")
        for alt in data['alts']:
            st.write(f"- {alt}")
        st.markdown("### Критерии")
        for name, val in data['crit'].items():
            if typ == 'numeric':
                st.write(f"- {name}: {val:.3f}")
            elif typ == 'interval':
                if isinstance(val, Interval):
                    st.write(f"- {name}: ({val.left:.3f}, {val.right:.3f})")
                else:
                    st.write(f"- {name}: {val}")
            elif typ == 'fuzzy':
                if isinstance(val, FuzzyTrapezoid):
                    st.write(f"- {name}: ({val.x1:.3f}, {val.x2:.3f}, {val.x3:.3f}, {val.x4:.3f})")
                else:
                    st.write(f"- {name}: {val}")
            else:
                st.write(f"- {name}: {val}")
        st.markdown("### Оценки")
        crit_names = list(data['crit'].keys())
        for i, alt in enumerate(data['alts']):
            st.markdown(f"**{alt}**")
            for j, crit in enumerate(crit_names):
                val = data['matrix'][i][j] if i < len(data['matrix']) and j < len(data['matrix'][i]) else "?"
                if typ == 'interval' and isinstance(val, Interval):
                    st.write(f"- {crit}: ({val.left:.3f}, {val.right:.3f})")
                elif typ == 'fuzzy' and isinstance(val, FuzzyTrapezoid):
                    st.write(f"- {crit}: ({val.x1:.3f}, {val.x2:.3f}, {val.x3:.3f}, {val.x4:.3f})")
                else:
                    st.write(f"- {crit}: {val}")
        if 'result' in data:
            st.markdown("### Результат")
            r = data['result']
            if len(r['winners']) > 1:
                st.markdown("## НИЧЬЯ!")
                for alt, score in r['winners'].items():
                    st.markdown(f"<h3 style='color:red'>{alt}: {score}</h3> ", unsafe_allow_html=True)
            else:
                winner = list(r['winners'].keys())[0]
                score = list(r['winners'].values())[0]
                st.markdown(f"<h1 style='color:red'>{winner}: {score}</h1>", unsafe_allow_html=True)
        return
    if st.session_state.load_page_to_calc:
        page_num, typ, data = st.session_state.load_page_to_calc
        st.info(f"Загружены данные со страницы {page_num} (тип: {typ}). Отредактируйте и сохраните как новую.")
        if st.button("Отменить загрузку"):
            st.session_state.load_page_to_calc = None
            st.rerun()
        alternatives = data['alts'].copy()
        criteria = data['crit'].copy()
        matrix = data['matrix'].copy()
        old_result = data.get('result', None)
        if typ == 'linguistic' and 'scale' in data:
            st.session_state.scale = data['scale']
        st.markdown("### Альтернативы")
        alts_text = "\n".join(alternatives)
        new_alts_text = st.text_area("Редактируйте альтернативы (по одной на строку)", alts_text, height=150)
        new_alternatives = [a.strip() for a in new_alts_text.split('\n') if a.strip()]
        if len(new_alternatives) != len(set(new_alternatives)):
            st.error("Дубликаты альтернатив!")
            return
        st.markdown("### Критерии (важности)")
        if typ == 'numeric':
            crit_text = "\n".join([f"{k}:{v}" for k, v in criteria.items()])
            new_crit_text = st.text_area("Редактируйте критерии (название:вес (0<=вес<=1))", crit_text, height=150)
            new_criteria = {}
            for line in new_crit_text.split('\n'):
                if ':' in line:
                    name, val = line.split(':', 1)
                    name = name.strip()
                    val = val.strip()
                    try:
                        weight = float(val)
                        if 0 <= weight <= 1:
                            new_criteria[name] = weight
                    except:
                        pass
        elif typ == 'interval':
            crit_lines = []
            for k, v in criteria.items():
                if isinstance(v, Interval):
                    crit_lines.append(f"{k}:{v.left},{v.right}")
                elif isinstance(v, (list, tuple)):
                    crit_lines.append(f"{k}:{v[0]},{v[1]}")
                else:
                    crit_lines.append(f"{k}:{v}")
            crit_text = "\n".join(crit_lines)
            new_crit_text = st.text_area("Редактируйте критерии (название:от,до)", crit_text, height=150)
            new_criteria = {}
            for line in new_crit_text.split('\n'):
                if ':' in line:
                    name, val = line.split(':', 1)
                    parts = val.split(',')
                    if len(parts) >= 2:
                        try:
                            new_criteria[name.strip()] = (float(parts[0]), float(parts[1]))
                        except:
                            pass
        elif typ == 'fuzzy':
            crit_lines = []
            for k, v in criteria.items():
                if isinstance(v, FuzzyTrapezoid):
                    crit_lines.append(f"{k}:{v.x1},{v.x2},{v.x3},{v.x4}")
                elif isinstance(v, (list, tuple)) and len(v) >= 4:
                    crit_lines.append(f"{k}:{v[0]},{v[1]},{v[2]},{v[3]}")
                else:
                    crit_lines.append(f"{k}:{v}")
            crit_text = "\n".join(crit_lines)
            new_crit_text = st.text_area("Редактируйте критерии (название:x1,x2,x3,x4)", crit_text, height=150)
            new_criteria = {}
            for line in new_crit_text.split('\n'):
                if ':' in line:
                    name, val = line.split(':', 1)
                    parts = val.split(',')
                    if len(parts) >= 4:
                        try:
                            new_criteria[name.strip()] = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
                        except:
                            pass
        else:
            scale = st.session_state.get('scale', ['низкая', 'средняя', 'высокая'])
            crit_text = "\n".join([f"{k}:{v}" for k, v in criteria.items()])
            new_crit_text = st.text_area(f"Редактируйте критерии (название:значение из {scale})", crit_text, height=150)
            new_criteria = {}
            for line in new_crit_text.split('\n'):
                if ':' in line:
                    name, val = line.split(':', 1)
                    if val.strip() in scale:
                        new_criteria[name.strip()] = val.strip()
        if not new_criteria:
            st.warning("Введите критерии")
            return
        st.markdown("### Оценки альтернатив по критериям")
        crit_names = list(new_criteria.keys())
        new_matrix = []
        for i, alt in enumerate(new_alternatives):
            st.markdown(f"**{alt}**")
            row = []
            for j, crit in enumerate(crit_names):
                default = None
                if i < len(matrix) and j < len(matrix[i]):
                    default = matrix[i][j]
                if typ == 'numeric':
                    d = 0.5 if default is None else float(default)
                    val = st.number_input(crit, 0.0, 1.0, d, 0.05, key=f"m_{i}_{j}")
                    row.append(float(val))
                elif typ == 'interval':
                    if default is None:
                        dl, dr = 0.3, 0.7
                    elif isinstance(default, Interval):
                        dl, dr = default.left, default.right
                    elif isinstance(default, (list, tuple)):
                        dl, dr = float(default[0]), float(default[1])
                    elif hasattr(default, 'left'):
                        dl, dr = default.left, default.right
                    else:
                        dl, dr = 0.3, 0.7
                    col1, col2 = st.columns(2)
                    left = col1.number_input(f"{crit} от", 0.0, 1.0, dl, 0.05, key=f"m_{i}_{j}_l")
                    right = col2.number_input(f"{crit} до", 0.0, 1.0, dr, 0.05, key=f"m_{i}_{j}_r")
                    row.append(Interval(left, right))
                elif typ == 'fuzzy':
                    if default is None:
                        d1,d2,d3,d4 = 0.25, 0.4, 0.6, 0.75
                    elif isinstance(default, FuzzyTrapezoid):
                        d1,d2,d3,d4 = default.x1, default.x2, default.x3, default.x4
                    elif isinstance(default, (list, tuple)) and len(default) >= 4:
                        d1,d2,d3,d4 = float(default[0]), float(default[1]), float(default[2]), float(default[3])
                    elif hasattr(default, 'x1'):
                        d1,d2,d3,d4 = default.x1, default.x2, default.x3, default.x4
                    else:
                        d1,d2,d3,d4 = 0.25, 0.4, 0.6, 0.75
                    c1,c2,c3,c4 = st.columns(4)
                    x1 = c1.number_input("x₁", 0.0, 1.0, d1, 0.05, key=f"m_{i}_{j}_1")
                    x2 = c2.number_input("x₂", 0.0, 1.0, d2, 0.05, key=f"m_{i}_{j}_2")
                    x3 = c3.number_input("x₃", 0.0, 1.0, d3, 0.05, key=f"m_{i}_{j}_3")
                    x4 = c4.number_input("x₄", 0.0, 1.0, d4, 0.05, key=f"m_{i}_{j}_4")
                    if x1 <= x2 <= x3 <= x4:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=[x1,x2,x3,x4], y=[0,1,1,0], fill='tozeroy'))
                        fig.update_layout(height=150, margin=dict(l=0,r=0,t=0,b=0))
                        st.plotly_chart(fig, key=f"plot_{i}_{j}")
                        row.append(FuzzyTrapezoid(x1,x2,x3,x4))
                    else:
                        st.error("Ошибка порядка")
                        row.append(None)
                else:
                    scale = st.session_state.get('scale', ['низкая','средняя','высокая'])
                    if default is None:
                        d = scale[1]
                    elif default in scale:
                        d = default
                    else:
                        d = scale[1]
                    idx = scale.index(d)
                    row.append(st.selectbox(crit, scale, index=idx, key=f"m_{i}_{j}"))
            new_matrix.append(row)
        resolve_tie = st.checkbox("Решать ничью", True) if typ in ['interval','fuzzy'] else None
        col1, col2 = st.columns(2)
        with col1:
            if st.button("СОХРАНИТЬ КАК НОВУЮ СТРАНИЦУ", type="primary"):
                try:
                    if typ == 'numeric':
                        imp = {k: float(v) for k, v in new_criteria.items()}
                        w, s, t = yager_method(new_alternatives, imp, new_matrix)
                    elif typ == 'interval':
                        imp = {k: Interval(v[0], v[1]) for k, v in new_criteria.items()}
                        w, s, t = interval_yager_method(new_alternatives, imp, new_matrix, resolve_tie)
                    elif typ == 'fuzzy':
                        imp = {k: FuzzyTrapezoid(v[0], v[1], v[2], v[3]) for k, v in new_criteria.items()}
                        w, s, t = fuzzy_yager_method(new_alternatives, imp, new_matrix, resolve_tie)
                    else:
                        w, s, t = yager_method_linguistic(new_alternatives, new_criteria, new_matrix, st.session_state.scale)
                    result = {'winners': w, 'sorted': s, 'was_tie': t}
                    new_page = get_max_page(st.session_state.room_id) + 1
                    save_data = {'alts': new_alternatives, 'crit': new_criteria, 'matrix': new_matrix, 'result': result}
                    if typ == 'linguistic':
                        save_data['scale'] = st.session_state.scale
                    save_page(st.session_state.room_id, new_page, typ, save_data)
                    st.success(f"СОЗДАНА НОВАЯ СТРАНИЦА {new_page}")
                    st.session_state.calc_result = result
                    st.session_state.calc_type = typ
                    st.session_state.calc_alts = new_alternatives
                    st.session_state.calc_crit = new_criteria
                    st.session_state.calc_mat = new_matrix
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        
        with col2:
            if st.button("Создать новое решение (очистить)"):
                st.session_state.load_page_to_calc = None
                st.session_state.calc_result = None
                st.rerun()
        
        if st.session_state.get('calc_result'):
            st.markdown("---")
            st.markdown("## Результат")
            r = st.session_state.calc_result
            dt = st.session_state.calc_type            
            if len(r['winners']) > 1:
                st.markdown("## НИЧЬЯ!")
                for alt, score in r['winners'].items():
                    if dt == 'numeric':
                        st.markdown(f"<h3 style='color:red'>{alt}: {float(score):.4f}</h3>", unsafe_allow_html=True)
                    elif dt == 'interval':
                        if isinstance(score, tuple) and len(score) == 2:
                            interval, rep = score
                            st.markdown(f"<h3 style='color:red'>{alt}: {interval} (rep={float(rep):.4f})</h3>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<h3 style='color:red'>{alt}: {score}</h3>", unsafe_allow_html=True)
                    elif dt == 'fuzzy':
                        rep = score.overall_rep if hasattr(score, 'overall_rep') else score
                        st.markdown(f"<h3 style='color:red'>{alt}: {rep}</h3>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<h3 style='color:red'>{alt}: {score}</h3>", unsafe_allow_html=True)
            else:
                winner = list(r['winners'].keys())[0]
                score = list(r['winners'].values())[0]
                if dt == 'numeric':
                    st.markdown(f"<h1 style='color:red'>{winner}: {float(score):.4f}</h1>", unsafe_allow_html=True)
                elif dt == 'interval':
                    if isinstance(score, tuple) and len(score) == 2:
                        interval, rep = score
                        st.markdown(f"<h1 style='color:red'>{winner}: {interval} (rep={float(rep):.4f})</h1>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<h1 style='color:red'>{winner}: {score}</h1>", unsafe_allow_html=True)
                elif dt == 'fuzzy':
                    rep = score.overall_rep if hasattr(score, 'overall_rep') else score
                    st.markdown(f"<h1 style='color:red'>{winner}: {rep}</h1>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h1 style='color:red'>{winner}: {score}</h1>", unsafe_allow_html=True)
            st.markdown("### Рейтинг:")
            for i, item in enumerate(r['sorted'][:5]):
                if i == 0 and len(r['winners']) == 1:
                    continue
                if dt == 'numeric':
                    st.write(f"{i+1}. {item[0]}: {item[1]:.4f}")
                elif dt == 'interval':
                    rep = item[2] if len(item) > 2 else 0
                    st.write(f"{i+1}. {item[0]}: {item[1]} rep={rep:.4f}")
                elif dt == 'fuzzy':
                    rep = item[1].overall_rep if hasattr(item[1], 'overall_rep') else item[1]
                    st.write(f"{i+1}. {item[0]}: rep={rep:.4f}")
                else:
                    st.write(f"{i+1}. {item[0]}: {item[1]}")
            
            st.markdown("---")
            st.markdown("## Анализ чувствительности")
            
            col1, col2 = st.columns(2)
            
            if col1.button("По важности критериев"):
                with st.spinner("Анализ"):
                    try:
                        alts = st.session_state.calc_alts
                        crit = st.session_state.calc_crit
                        mat = st.session_state.calc_mat
                        if dt == 'numeric':
                            sens = sensitivity_importance_numeric(alts, crit, mat)
                        elif dt == 'interval':
                            imp = {}
                            for k, v in crit.items():
                                if isinstance(v, (list, tuple)):
                                    imp[k] = Interval(v[0], v[1])
                                else:
                                    imp[k] = Interval(v.left, v.right) if hasattr(v, 'left') else Interval(0.3, 0.7)
                            sens = sensitivity_importance_interval(alts, imp, mat, resolve_tie=True)
                        elif dt == 'fuzzy':
                            imp = {}
                            for k, v in crit.items():
                                if isinstance(v, (list, tuple)):
                                    imp[k] = FuzzyTrapezoid(v[0], v[1], v[2], v[3])
                                elif hasattr(v, 'x1'):
                                    imp[k] = v
                                else:
                                    imp[k] = FuzzyTrapezoid(0.25, 0.4, 0.6, 0.75)
                            sens = sensitivity_importance_fuzzy(alts, imp, mat, resolve_tie=True)
                        else:
                            sens = sensitivity_importance_linguistic(alts, crit, mat, st.session_state.scale)
                        st.success("Стабильно" if sens.get('is_stable') else "Нестабильно")
                        with st.expander("Критические критерии"):
                            st.write(sens.get('significant', []) or "Нет")
                        with st.expander("Неважные критерии"):
                            st.write(sens.get('redundant', []) or "Нет")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            if col2.button("По оценкам альтернатив"):
                with st.spinner("Анализ"):
                    try:
                        alts = st.session_state.calc_alts
                        crit = st.session_state.calc_crit
                        mat = st.session_state.calc_mat
                        
                        if dt == 'numeric':
                            sens = sensitivity_ratings_numeric(alts, crit, mat)
                        elif dt == 'interval':
                            imp = {}
                            for k, v in crit.items():
                                if isinstance(v, (list, tuple)):
                                    imp[k] = Interval(v[0], v[1])
                                else:
                                    imp[k] = Interval(v.left, v.right) if hasattr(v, 'left') else Interval(0.3, 0.7)
                            sens = sensitivity_ratings_interval(alts, imp, mat, resolve_tie=True)
                        elif dt == 'fuzzy':
                            imp = {}
                            for k, v in crit.items():
                                if isinstance(v, (list, tuple)):
                                    imp[k] = FuzzyTrapezoid(v[0], v[1], v[2], v[3])
                                elif hasattr(v, 'x1'):
                                    imp[k] = v
                                else:
                                    imp[k] = FuzzyTrapezoid(0.25, 0.4, 0.6, 0.75)
                            sens = sensitivity_ratings_fuzzy(alts, imp, mat, resolve_tie=True)
                        else:
                            sens = sensitivity_ratings_linguistic(alts, crit, mat, st.session_state.scale)
                        st.success("Стабильно" if sens.get('is_stable') else "Нестабильно")
                        with st.expander("Критические оценки"):
                            items = sens.get('significant', [])
                            st.write(items[:15] if items else "Нет")
                        with st.expander("Неважные оценки"):
                            items = sens.get('redundant', [])
                            st.write(items[:15] if items else "Нет")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
        
        return

    data_type = st.selectbox("Тип данных", ["numeric","interval","fuzzy","linguistic"],
        format_func=lambda x: {"numeric":"Числовые","interval":"Интервалы","fuzzy":"Нечеткие","linguistic":"Лингвистические"}[x])

    if data_type == 'linguistic':
        if 'scale' not in st.session_state:
            scale_input = st.text_area("Шкала (по одной на строку)", "низкая\nсредняя\nвысокая")
            if st.button("Сохранить шкалу"):
                scale = [s.strip() for s in scale_input.split('\n') if s.strip()]
                if len(set(scale)) == len(scale) and len(scale) >= 2:
                    st.session_state.scale = scale
                    st.rerun()
            return
        st.info(f"Шкала: {', '.join(st.session_state.scale)}")
        if st.button("Изменить шкалу"):
            del st.session_state.scale
            st.rerun()

    st.markdown("### Альтернативы")
    alts_input = st.text_area("Альтернативы (по одной на строку)", "Альт1\nАльт2")
    alternatives = [a.strip() for a in alts_input.split('\n') if a.strip()]
    if len(alternatives) != len(set(alternatives)):
        st.error("Дубликаты альтернатив")
        return

    st.markdown("### Критерии")
    if data_type == 'numeric':
        crit_input = st.text_area("Критерии (название:вес (0<=вес<=1))", "Крит1:0.7\nКрит2:0.5")
    elif data_type == 'interval':
        crit_input = st.text_area("Критерии (название:от,до)", "Крит1:0.3,0.7\nКрит2:0.4,0.6")
    elif data_type == 'fuzzy':
        crit_input = st.text_area("Критерии (название:x1,x2,x3,x4)", "Крит1:0.25,0.4,0.6,0.75")
    else:
        scale = st.session_state.get('scale', ['низкая','средняя','высокая'])
        crit_input = st.text_area("Критерии (название:значение)", f"Крит1:{scale[1]}\nКрит2:{scale[2]}")

    criteria = {}
    for line in crit_input.split('\n'):
        if ':' in line:
            name, val = line.split(':',1)
            name = name.strip()
            if data_type == 'numeric':
                val = val.strip()
                try:
                    weight = float(val)
                    if 0 <= weight <= 1:
                        criteria[name] = weight
                except:
                    pass
            elif data_type == 'interval':
                parts = val.split(',')
                if len(parts) >= 2:
                    criteria[name] = (float(parts[0]), float(parts[1]))
            elif data_type == 'fuzzy':
                parts = val.split(',')
                if len(parts) >= 4:
                    criteria[name] = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
            else:
                if val.strip() in st.session_state.get('scale', []):
                    criteria[name] = val.strip()
    if len(criteria) != len(set(criteria.keys())):
        st.error("Дубликаты критериев")
        return

    st.markdown("### Оценки")
    crit_names = list(criteria.keys())
    matrix = []
    for i, alt in enumerate(alternatives):
        st.markdown(f"**{alt}**")
        row = []
        if data_type == 'numeric':
            cols = st.columns(1)
            for j, crit in enumerate(crit_names):
                row.append(cols[0].number_input(crit, 0.0, 1.0, 0.5, 0.05, key=f"m_{i}_{j}"))
        elif data_type == 'interval':
            for j, crit in enumerate(crit_names):
                col1, col2 = st.columns(2)
                left = col1.number_input(f"{crit} от", 0.0, 1.0, 0.3, 0.05, key=f"m_{i}_{j}_l")
                right = col2.number_input(f"{crit} до", 0.0, 1.0, 0.7, 0.05, key=f"m_{i}_{j}_r")
                row.append(Interval(left, right))
        elif data_type == 'fuzzy':
            for j, crit in enumerate(crit_names):
                st.write(f"*{crit}*")
                c1,c2,c3,c4 = st.columns(4)
                x1 = c1.number_input("x₁", 0.0, 1.0, 0.25, 0.05, key=f"m_{i}_{j}_1")
                x2 = c2.number_input("x₂", 0.0, 1.0, 0.4, 0.05, key=f"m_{i}_{j}_2")
                x3 = c3.number_input("x₃", 0.0, 1.0, 0.6, 0.05, key=f"m_{i}_{j}_3")
                x4 = c4.number_input("x₄", 0.0, 1.0, 0.75, 0.05, key=f"m_{i}_{j}_4")
                if x1 <= x2 <= x3 <= x4:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=[x1,x2,x3,x4], y=[0,1,1,0], fill='tozeroy'))
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, key=f"plot_{i}_{j}")
                    row.append(FuzzyTrapezoid(x1,x2,x3,x4))
                else:
                    st.error("Ошибка порядка")
                    row.append(None)
        else:
            scale = st.session_state.get('scale', ['низкая','средняя','высокая'])
            cols = st.columns(1)
            for j, crit in enumerate(crit_names):
                row.append(cols[0].selectbox(crit, scale, key=f"m_{i}_{j}"))
        matrix.append(row)

    resolve_tie = st.checkbox("Решать ничью", True) if data_type in ['interval','fuzzy'] else None

    if st.button("РАССЧИТАТЬ", type="primary"):
        try:
            if data_type == 'numeric':
                imp = {k:float(v) for k,v in criteria.items()}
                w,s,t = yager_method(alternatives, imp, matrix)
            elif data_type == 'interval':
                imp = {k:Interval(v[0], v[1]) for k,v in criteria.items()}
                w,s,t = interval_yager_method(alternatives, imp, matrix, resolve_tie)
            elif data_type == 'fuzzy':
                imp = {k:FuzzyTrapezoid(v[0], v[1], v[2], v[3]) for k,v in criteria.items()}
                w,s,t = fuzzy_yager_method(alternatives, imp, matrix, resolve_tie)
            else:
                w,s,t = yager_method_linguistic(alternatives, criteria, matrix, st.session_state.scale)
            result = {'winners': w, 'sorted': s, 'was_tie': t}
            st.session_state.current_result = result
            st.session_state.current_type = data_type
            st.session_state.current_alts = alternatives
            st.session_state.current_crit = criteria
            st.session_state.current_mat = matrix
            if st.session_state.room_id != "single":
                page_num = get_max_page(st.session_state.room_id) + 1
                save_data = {'alts': alternatives, 'crit': criteria, 'matrix': matrix, 'result': result}
                if data_type == 'linguistic':
                    save_data['scale'] = st.session_state.scale
                save_page(st.session_state.room_id, page_num, data_type, save_data)
                st.success(f"Сохранено на странице {page_num}")
            st.rerun()
        except Exception as e:
            st.error(f"Ошибка: {e}")

    if 'current_result' in st.session_state:
        st.markdown("---")
        r = st.session_state.current_result
        if len(r['winners']) > 1:
            st.markdown("## НИЧЬЯ!")
            for alt, score in r['winners'].items():
                st.markdown(f"<h3 style='color:red'>{alt}: {score} </h3>", unsafe_allow_html=True)
        else:
            winner = list(r['winners'].keys())[0]
            score = list(r['winners'].values())[0]
            st.markdown(f"<h1 style='color:red'>{winner}: {score}</h1>", unsafe_allow_html=True)
        
        st.markdown("### Рейтинг:")
        for i, item in enumerate(r['sorted'][:5]):
            if i == 0 and len(r['winners']) == 1:
                continue
            st.write(f"{i+1}. {item[0]}: {item[1] if len(item)==2 else item[2] if len(item)>2 else item[1]}")
        st.markdown("---")
        col1, col2 = st.columns(2)
        if col1.button("Чувствительность по важности"):
            dt = st.session_state.current_type
            alts = st.session_state.current_alts
            crit = st.session_state.current_crit
            mat = st.session_state.current_mat
            if dt == 'numeric':
                sens = sensitivity_importance_numeric(alts, crit, mat)
            elif dt == 'interval':
                imp = {k: Interval(v[0], v[1]) for k,v in crit.items()}
                sens = sensitivity_importance_interval(alts, imp, mat, resolve_tie=resolve_tie)
            elif dt == 'fuzzy':
                imp = {k: FuzzyTrapezoid(v[0], v[1], v[2], v[3]) for k,v in crit.items()}
                sens = sensitivity_importance_fuzzy(alts, imp, mat, resolve_tie=resolve_tie)
            else:
                sens = sensitivity_importance_linguistic(alts, crit, mat, st.session_state.scale)
            st.success("Стабильно" if sens.get('is_stable') else "Нестабильно")
            with st.expander("Критические критерии"):
                st.write(sens.get('significant', []) or "Нет")
            with st.expander("Неважные критерии"):
                st.write(sens.get('redundant', []) or "Нет")
        if col2.button("Чувствительность по оценкам"):
            dt = st.session_state.current_type
            alts = st.session_state.current_alts
            crit = st.session_state.current_crit
            mat = st.session_state.current_mat
            if dt == 'numeric':
                sens = sensitivity_ratings_numeric(alts, crit, mat)
            elif dt == 'interval':
                imp = {k: Interval(v[0], v[1]) for k,v in crit.items()}
                sens = sensitivity_ratings_interval(alts, imp, mat, resolve_tie=resolve_tie)
            elif dt == 'fuzzy':
                imp = {k: FuzzyTrapezoid(v[0], v[1], v[2], v[3]) for k,v in crit.items()}
                sens = sensitivity_ratings_fuzzy(alts, imp, mat, resolve_tie=resolve_tie)
            else:
                sens = sensitivity_ratings_linguistic(alts, crit, mat, st.session_state.scale)
            st.success("Стабильно" if sens.get('is_stable') else "Нестабильно")
            with st.expander("Критические оценки"):
                items = sens.get('significant', [])
                st.write(items[:10] if items else "Нет")
            with st.expander("Неважные оценки"):
                items = sens.get('redundant', [])
                st.write(items[:10] if items else "Нет")

if __name__ == "__main__":
    main()
