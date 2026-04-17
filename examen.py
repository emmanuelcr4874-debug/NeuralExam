import streamlit as st
import random
import pandas as pd
import PyPDF2
import google.generativeai as genai
import random
import string
import re
import base64
import json
from io import BytesIO
from datetime import datetime, timedelta
from streamlit_mic_recorder import mic_recorder
from streamlit_mic_recorder import mic_recorder
#from streamlit_gsheets import GSheetsConnection # <--- AGREGA ESTA LÍNEA
# Esto crea una memoria compartida para todos los que entren a la web
if "examenes_globales" not in st.session_state:
    @st.cache_resource
    def obtener_memoria_global():
        return {} # Aquí se guardarán los códigos tipo 'XJ92L1'
    
    st.session_state.examenes_globales = obtener_memoria_global()

# --- 1. CONFIGURACIÓN DE IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró la configuración de la API Key en los secretos.")
model = genai.GenerativeModel('models/gemini-flash-latest')# Modelo más rápido para audio y texto

st.set_page_config(page_title="NeuralExam Pro v3.5", page_icon="🧠", layout="wide")

# --- 2. BÚNKER DE MEMORIA (TODO LO TUYO ESTÁ AQUÍ) ---
if 'auth_docente' not in st.session_state:
    st.session_state.update({
        'auth_docente': False, 
        'examen_activo': False, 
        'preguntas_seleccionadas': [],
        'lista_results': [], 
        'correos_usados': [], 
        'examen_cerrado_global': False, 
        'revelar_notas': False,
        'pool_ia': [], 
        'pool_manual': [], 
        'lista_blanca': {}, 
        'modo_acceso': "Abierto (Cualquiera)",
        'feedbacks_privados': {},
        'alumno_actual_correo': "",
        'hora_inicio': None,
        'duracion_minutos': 30,
        'usar_tiempo': False
    })

# --- 3. BANCO COMPLETO (INTACTO) ---
BANCO = {
    "Español": [
        "¿Qué es un ensayo y cuál es su estructura principal?", "Define qué es una ficha de trabajo y para qué sirve.",
        "Explica la diferencia entre lenguaje formal e informal.", "¿Qué es una antología y para qué se realiza?",
        "Define qué es un poema y menciona tres de sus elementos.", "¿Qué es una biografía y en qué se diferencia de una autobiografía?",
        "Explica la función de las oraciones principales y secundarias en un párrafo.", "¿Para qué sirven las comillas en un texto?",
        "Qué es un reporte de encuesta y qué partes lo integran?", "Define qué es un programa de radio y cuál es la función del guion.",
        "¿Qué es el Renacimiento y cómo influyó en la literatura?", "Explica qué es un caligrama.",
        "¿Qué es una mesa redonda y quiénes participan en ella?", "Define qué es el modo imperativo y da un ejemplo.",
        "¿Qué es la publicidad y cuál es su objetivo principal?"
    ],
    "Ciencias (Química)": [
        "¿Qué es la tabla periódica y cómo se organizan los elementos?", "Explica qué es una mezcla homogénea y da un ejemplo.",
        "¿Qué sucede con las moléculas de agua cuando pasan de líquido a gas?", "¿Qué es un enlace químico y cuáles son los tipos principales?",
        "Define qué es la masa y qué es el volumen.", "¿Qué es una reacción química y cómo se representa?",
        "Explica la Ley de Conservación de la Materia de Lavoisier.", "¿Qué es un átomo y cuáles son sus partículas subatómicas?",
        "¿Cuál es la diferencia entre un elemento y un compuesto?", "¿Qué es el pH y qué mide la escala?",
        "Explica qué es un catalizador.", "¿Qué es la energía cinética?",
        "Define qué es un modelo atómico y menciona uno (ej. Bohr).", "¿Cómo se diferencia un ácido de una base?",
        "¿Qué es la oxidación? Da un ejemplo de la vida cotidiana."
    ],
    "Matemáticas": [
        "Resuelve 3x - 5 = 10. Explica paso a paso cómo despejaste la X.", "¿Cómo se calcula el área de un círculo? Escribe la fórmula y un ejemplo.",
        "Un coche recorre 120km en 2 horas, ¿cuál es su velocidad media?", "¿Qué es el Teorema de Pitágoras y para qué sirve?",
        "Si un pantalón cuesta $500 y tiene el 20% de descuento, ¿cuánto pagaré?", "Resuelve la operación: (5 + 3) * 2 - 4. Explica el orden.",
        "¿Qué es una sucesión numérica y cómo se encuentra el siguiente término?", "Define qué es un ángulo agudo, recto y obtuso.",
        "¿Cómo se calcula el volumen de un cubo de 4cm de lado?", "Si tengo 3 canicas rojas y 2 azules, ¿cual es la probabilidad de sacar roja?",
        "¿Qué es una gráfica de barras y para qué se utiliza?", "Resuelve: 2x + 8 = 20. Describe los pasos.",
        "¿Qué es el máximo común divisor (MCD)?", "Explica cómo se suman dos fracciones con diferente denominador.",
        "¿Qué es el perímetro y cómo se calcula en un rectángulo?"
    ],
    "Geografía": [
        "¿Qué son las coordenadas geográficas (latitud y longitud)?", "Explica qué es el ciclo del agua y su importancia.",
        "Menciona las capas internas de la Tierra y describe una.", "¿Qué es el relieve y menciona dos tipos de formaciones?",
        "Explica la diferencia entre clima y estado del tiempo.", "¿Qué es la migración y cuáles son sus causas principales?",
        "Define qué es la biodiversidad.", "¿Qué son los recursos naturales renovables y no renovables?",
        "Explica qué es el efecto invernadero.", "¿Qué es la globalización y cómo afecta a la cultura?",
        "Menciona los tres tipos de límites de las placas tectónicas.", "¿Qué es una cuenca hídrica?",
        "¿Cuál es la función de los mapas y qué elementos deben tener?", "Explica qué es la densidad de población.",
        "¿Qué son las actividades económicas primarias? Da ejemplos."
    ]
}

def main():
    # --- 1. LOGO Y ESTILOS (INTACTOS) ---
    izq, centro, der = st.columns([2, 1, 2])
    with centro:
        st.markdown("""
            <div style="text-align: center; margin-bottom: -15px;">
                <div class="logo-neural">🧠</div>
            </div>
            <style>
                .logo-neural { font-size: 80px; filter: drop-shadow(0 0 15px #58a6ff); animation: pulse 2.5s infinite ease-in-out; }
                @keyframes pulse {
                    0% { transform: scale(1); filter: drop-shadow(0 0 10px #58a6ff); }
                    50% { transform: scale(1.1); filter: drop-shadow(0 0 25px #bc8cff); }
                    100% { transform: scale(1); filter: drop-shadow(0 0 10px #58a6ff); }
                }
            </style>
        """, unsafe_allow_html=True)

    # --- 2. DISEÑO CYBERPUNK (INTACTO) ---
    st.markdown("""
        <style>
        .stApp {
            background-color: #030303 !important;
            background-image: 
                linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03)),
                radial-gradient(circle at center, #001a33 0%, #030303 100%) !important;
            background-size: 100% 3px, 2px 100%, 100% 100% !important;
            background-attachment: fixed !important;
        }
        .status-bar {
            display: flex; justify-content: space-around; background: rgba(88, 166, 255, 0.05);
            border: 1px solid rgba(88, 166, 255, 0.2); border-radius: 4px; padding: 4px;
            margin: 10px auto 25px auto; max-width: 850px; font-family: 'Courier New', monospace;
            font-size: 0.75rem; color: #58a6ff;
        }
        .online-dot { height: 7px; width: 7px; background-color: #00ff41; border-radius: 50%; display: inline-block; margin-right: 5px; animation: blink 1.2s infinite; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
        .titulo-cyber { background: linear-gradient(90deg, #58a6ff, #bc8cff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5rem; font-weight: 800; text-align: center; text-shadow: 0 0 20px rgba(88, 166, 255, 0.4); margin-bottom: 0px; }
        div.stButton > button:hover { box-shadow: 0 0 20px #58a6ff !important; transform: skewX(-3deg); transition: 0.1s; }
        [data-testid="stSidebar"] { display: none !important; }
        header {visibility: hidden;} footer {visibility: hidden;}
        </style>

        <h1 class="titulo-cyber">NEURAL EXAM PRO</h1>
        
        <div class="status-bar">
            <span><span class="online-dot"></span> 📡 NODE-IA: ONLINE</span>
            <span>🕒 SYS-TIME: """ + datetime.now().strftime("%H:%M") + """</span>
            <span>🔋 PWR: 98% [AC-CONN]</span>
            <span>🌐 LATENCY: 14ms</span>
        </div>
    """, unsafe_allow_html=True)

    tab_alumno, tab_docente = st.tabs(["🎓 PORTAL ALUMNO", "🛡️ PANEL DOCENTE"])

    with tab_alumno:
        st.markdown('<h2 style="color: #58a6ff; font-family: monospace;">⚡ TERMINAL_ESTUDIANTE</h2>', unsafe_allow_html=True)
        
       # --- PASO 1: VALIDACIÓN DE CÓDIGO CORTO ---
        if not st.session_state.examen_activo:
            st.info("Sincronización requerida. Por favor, ingresa el código de 6 caracteres proporcionado por el docente.")
            
            # Usamos text_input porque ahora el código es corto (Ej: A97X2L)
            codigo_input = st.text_input("🔑 Código de Examen:", key="input_codigo_corto").upper().strip()
            
            if st.button("Sincronizar Dispositivo"):
                # Verificamos si el código existe en la memoria global compartida
                if "examenes_globales" in st.session_state and codigo_input in st.session_state.examenes_globales:
                    # Traemos las preguntas desde la memoria del profe
                    st.session_state.preguntas_seleccionadas = st.session_state.examenes_globales[codigo_input]
                    st.session_state.examen_activo = True
                    st.success("✅ Examen cargado correctamente.")
                    st.rerun()
                else:
                    st.error("❌ Código no válido o el examen aún no ha sido publicado.")
                    # 3. Guardamos para el Profesor (PC1) y para el Alumno
                    reg = {
                                "Nombre": n_in.title(), 
                                "Correo": c_in, 
                                "Calificación": puntos,
                                "Observaciones": respuesta_ia[:500], # Limitamos para el Excel
                                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                            }
                            
                    st.session_state.lista_results.append(reg)
                    st.session_state.correos_usados.append(c_in)
                    st.session_state.feedbacks_privados[c_in] = respuesta_ia

                            # --- NUEVO: ENVÍO A GOOGLE SHEETS ---
                    try:
                                #conn = st.connection("gsheets", type=GSheetsConnection)
                                df_existente = conn.read(spreadsheet="https://docs.google.com/spreadsheets/d/1Xl6vTuBSLHqWpHlOM4gWiEDFVRo8B6ttEtUEC2jzSOw/edit?usp=sharing")
                                # Leemos datos actuales para anexar
                                df_existente = conn.read()
                                df_nuevo = pd.DataFrame([reg])
                                df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
                                # Actualizamos la nube
                                conn.update(data=df_final)
                                st.info("☁️ Sincronizado con la base de datos central.")
                    except Exception as e:
                                st.warning(f"Nota guardada localmente, pero hubo un detalle con la nube: {e}")

        # --- PASO 2: REGISTRO Y PREGUNTAS ---
        else:
            st.markdown("### 📝 Registro de Identidad")
            col_id1, col_id2 = st.columns(2)
            with col_id1:
                n_in = st.text_input("Nombre Completo:", placeholder="Ej. Emmanuel", key="reg_nombre")
            with col_id2:
                c_in = st.text_input("Correo Electrónico:", placeholder="correo@ejemplo.com", key="reg_correo").lower().strip()

            if not n_in or not c_in:
                st.warning("⚠️ Ingresa tu nombre y correo para desbloquear las preguntas.")
            
            elif c_in in st.session_state.correos_usados:
                st.error("SISTEMA: Este correo ya registró un envío.")
            
            else:
                st.divider()
                st.markdown(f"#### 📑 Examen en curso: {len(st.session_state.preguntas_seleccionadas)} preguntas")
                
                respuestas = []
                for i, p in enumerate(st.session_state.preguntas_seleccionadas):
                    st.markdown(f"**{i+1}. {p}**")
                    col_txt, col_mic = st.columns([0.85, 0.15])
                    
                    transcripcion_actual = ""
                    with col_mic:
                        audio_data = mic_recorder(start_prompt="🎤", stop_prompt="🛑", key=f"mic_alumno_{i}")
                        if audio_data:
                            try:
                                res_audio = model.generate_content([
                                    "Transcribe este audio.",
                                    {"mime_type": "audio/wav", "data": audio_data['bytes']}
                                ])
                                transcripcion_actual = res_audio.text
                            except:
                                st.error("Error de audio.")

                    with col_txt:
                        # ESTO ES LO QUE NO TE APARECÍA:
                        r_text = st.text_area("Respuesta:", value=transcripcion_actual, key=f"ans_alumno_{i}", label_visibility="collapsed")
                        respuestas.append(r_text)

                if st.button("🚀 FINALIZAR EXAMEN"):
                    if all(r.strip() != "" for r in respuestas):
                        with st.spinner("El profesor IA está revisando tus respuestas..."):
                            raw = "\n".join([f"P: {p} | R: {r}" for p, r in zip(st.session_state.preguntas_seleccionadas, respuestas)])
                            
                            prompt_profesor = f"""
                            Actúa como un profesor calificador. Revisa este examen y para CADA pregunta:
                            1. Indica si es Correcta, Parcial o Incorrecta.
                            2. Explica brevemente por qué (qué estuvo bien o qué faltó).
                            Al final, escribe: NOTA_NUMERICA: X (donde X es de 0 a 100).
                            Examen:
                            {raw}
                            """
                            
                            respuesta_ia = model.generate_content(prompt_profesor).text
                            nota = re.search(r"NOTA_NUMERICA:\s*(\d+)", respuesta_ia)
                            puntos = nota.group(1) if nota else "0"

                            reg = {
                                "Nombre": n_in.title(), 
                                "Correo": c_in, 
                                "Calificación": puntos,
                                "Observaciones": respuesta_ia[:500],
                                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                            }
                            
                            st.session_state.lista_results.append(reg)
                            st.session_state.correos_usados.append(c_in)
                            st.session_state.feedbacks_privados[c_in] = respuesta_ia

                            # Sincronización con Google Sheets
                            try:
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                df_existente = conn.read()
                                df_nuevo = pd.DataFrame([reg])
                                df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
                                conn.update(data=df_final)
                                st.info("☁️ Sincronizado con la base de datos central.")
                            except Exception as e:
                                st.warning(f"Guardado localmente. Error de nube: {e}")

                            st.success(f"✅ ¡Examen enviado! Tu nota es: {puntos}/100")
                            st.balloons()
                    else:
                        st.warning("⚠️ Por favor, responde todas las preguntas.")

                if c_in in st.session_state.feedbacks_privados:
                    st.divider()
                    st.markdown("### 📝 Retroalimentación de tu Profesor IA")
                    st.info(st.session_state.feedbacks_privados[c_in])
    with tab_docente:
        st.header("👨‍🏫 Panel de Gestión Docente")
        if not st.session_state.auth_docente:
            if st.text_input("Llave Maestra:", type="password", key="llave_docente") == "profe2026": 
                st.session_state.auth_docente = True; st.rerun()
        
        if st.session_state.auth_docente:
            # --- NUEVO: GENERADOR DE CÓDIGO CORTO (6 CARACTERES) ---
            st.divider()
            st.subheader("📡 Publicar Examen")
            st.write("Genera un código sencillo para que los alumnos entren desde su celular.")

            if st.button("🎲 Generar Código de Acceso"):
                if st.session_state.preguntas_seleccionadas:
                    # Creamos el código corto (Ejemplo: A97X2L)
                    nuevo_codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    # Lo guardamos en la memoria global para que los celulares lo encuentren
                    st.session_state.examenes_globales[nuevo_codigo] = st.session_state.preguntas_seleccionadas
                    st.session_state.codigo_actual = nuevo_codigo
                    st.success(f"✅ ¡Código generado con éxito!")
                else:
                    st.warning("⚠️ Primero selecciona o genera preguntas en la sección de arriba.")

            # Si ya hay un código activo, lo mostramos en grande
            if "codigo_actual" in st.session_state:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; border: 2px dashed #4CAF50; border-radius: 10px;">
                    <h2 style="margin: 0;">CÓDIGO DEL EXAMEN:</h2>
                    <h1 style="color: #4CAF50; font-size: 50px; margin: 10px 0;">{st.session_state.codigo_actual}</h1>
                    <p>Escribe este código en el pizarrón</p>
                </div>
                """, unsafe_allow_html=True) # <-- Solo cambia 'stdio' por 'html'
            
            # --- CONTROL DE ALUMNOS (RESTAURADO) ---
            st.divider()
            st.subheader("👥 Control de Alumnos")
            st.session_state.modo_acceso = st.radio("Configuración de Acceso:", ["Abierto (Cualquiera)", "Lista Blanca (Excel/Manual)"])
            if st.session_state.modo_acceso == "Lista Blanca (Excel/Manual)":
                c1, c2 = st.columns(2)
                with c1:
                    n_m = st.text_input("Nombre:")
                    c_m = st.text_input("Correo:").lower().strip()
                    if st.button("➕ Registrar Alumno"): 
                        st.session_state.lista_blanca[c_m] = n_m.strip()
                        st.success("Registrado.")
                with c2:
                    f_a = st.file_uploader("Cargar Alumnos (.xlsx):", type=["xlsx"])
                    if f_a:
                        df_a = pd.read_excel(f_a)
                        for _, f in df_a.iterrows(): 
                            st.session_state.lista_blanca[str(f['Correo']).lower().strip()] = str(f['Nombre']).strip()
                        st.success("Lista cargada.")

            # --- TIEMPO Y CIERRE (RESTAURADO) ---
            st.divider()
            st.subheader("🕒 Tiempo y Resultados")
            st.session_state.usar_tiempo = st.toggle("Habilitar Cronómetro", value=st.session_state.usar_tiempo)
            if st.session_state.usar_tiempo:
                st.session_state.duracion_minutos = st.select_slider("Duración (Min):", options=[30, 45, 60], value=st.session_state.duracion_minutos)
            
            if st.session_state.examen_activo:
                if st.button("🛑 CERRAR EXAMEN AHORA"):
                    st.session_state.examen_cerrado_global = True
                    st.session_state.examen_activo = False; st.rerun()

            st.session_state.revelar_notas = st.toggle("🔓 Revelar Calificaciones", value=st.session_state.revelar_notas)
            
            # --- CREACIÓN DE EXAMEN Y PDF (TODO INTACTO) ---
            st.divider()
            st.subheader("📝 Creación de Examen")
            modo = st.radio("Origen de preguntas:", ["Banco de 60 Preguntas", "Texto Manual", "Generar desde PDF"])
            pool_final = []

            if modo == "Banco de 60 Preguntas":
                mats = st.multiselect("Materias:", list(BANCO.keys()))
                for m in mats: pool_final.extend(BANCO[m])
            elif modo == "Texto Manual":
                t_area = st.text_area("Una pregunta por línea:")
                if st.button("💾 Guardar Manuales"):
                    st.session_state.pool_manual = [p.strip() for p in t_area.split('\n') if len(p.strip()) > 3]
                pool_final = st.session_state.pool_manual
            elif modo == "Generar desde PDF":
                arc = st.file_uploader("Subir PDF:", type=["pdf"])
                if arc and st.button("🤖 IA: Generar"):
                    reader = PyPDF2.PdfReader(arc)
                    texto = "".join([p.extract_text() for p in reader.pages])
                    res = model.generate_content(f"Genera 10 preguntas sobre: {texto[:4000]}. Una por línea.").text
                    lineas = [p.strip() for p in res.split('\n') if len(p.strip()) > 10]
                    st.session_state.pool_ia = [re.sub(r'^[\d\s\.\-\)\(]+', '', p) for p in lineas]
                pool_final = st.session_state.pool_ia

            if st.button("🚀 LANZAR EXAMEN"):
                if pool_final:
                    st.session_state.preguntas_seleccionadas = random.sample(pool_final, min(len(pool_final), 10))
                    st.session_state.examen_activo, st.session_state.examen_cerrado_global = True, False
                    st.session_state.hora_inicio = datetime.now(); st.balloons()
                else: st.warning("Pool vacío.")

            # --- REPORTE Y EXCEL (RESTAURADO) ---
            if st.session_state.lista_results:
                st.subheader("📊 Reporte")
                df = pd.DataFrame(st.session_state.lista_results)
                st.dataframe(df)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
                st.download_button("📥 Descargar Excel", data=output.getvalue(), file_name="Resultados.xlsx")
            
            if st.button("⚠️ REINICIAR TODO"):
                st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()
