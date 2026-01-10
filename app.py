import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_elite_v29_final"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- CARGA DEL ARCHIVO DE PALABRAS ---
DICCIONARIO_TOTAL = {}

def cargar_palabras():
    global DICCIONARIO_TOTAL
    dict_temp = {}
    path_archivo = 'palabras.txt'
    if os.path.exists(path_archivo):
        try:
            with open(path_archivo, 'r', encoding='utf-8') as f:
                for linea in f:
                    if ":" in linea:
                        p, pst = linea.strip().split(":", 1)
                        dict_temp[p] = pst
            if dict_temp:
                DICCIONARIO_TOTAL = dict_temp
                print(f"✅ ÉXITO: {len(DICCIONARIO_TOTAL)} palabras cargadas.")
        except Exception as e: print(f"⚠️ ERROR: {e}")
    else:
        DICCIONARIO_TOTAL = {"Error": "Sin archivo .txt", "Avisar": "Admin"}

cargar_palabras()

game = {
    "encendido": False,
    "estado": "lobby",
    "jugadores": {},    
    "roles": {},        
    "palabra_actual": "",
    "pista_actual": "",
    "historial_palabras": [], 
    "ultimo_resultado": None,
    "tickets": {},            
    "historial_impostores": [] 
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor Elite v2.9</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        :root { --bg: #050505; --card: #121212; --primary: #a855f7; --accent: #22d3ee; --text: #f8fafc; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); text-align: center; margin: 0; padding: 15px; }
        .box { background: var(--card); padding: 30px; border-radius: 24px; max-width: 340px; margin: 10px auto; border: 1px solid #222; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h2 { color: var(--primary); letter-spacing: 4px; text-transform: uppercase; font-size: 24px; margin-bottom: 20px; text-shadow: 0 0 10px var(--primary); }
        .btn { background: var(--primary); color: white; border: none; padding: 16px; border-radius: 12px; width: 100%; cursor: pointer; margin-top: 15px; font-weight: bold; font-size: 15px; transition: 0.3s; }
        .btn:active { transform: scale(0.95); }
        .btn-admin { background: transparent; border: 1px solid var(--accent); color: var(--accent); font-size: 11px; margin-top: 5px; }
        .hidden { display: none !important; }
        #lista { text-align: left; background: #000; padding: 15px; border-radius: 15px; margin: 15px 0; border: 1px solid #1a1a1a; line-height: 1.8; color: #ccc; }
        input { width: 90%; padding: 14px; margin-bottom: 10px; border-radius: 10px; border: 1px solid #333; background: #1a1a1a; color: white; outline: none; text-align: center; }
        .res-box { background: rgba(34, 211, 238, 0.1); border: 1px solid var(--accent); padding: 15px; border-radius: 15px; margin-top: 20px; }
        .waiting-msg { color: #facc15; font-size: 14px; padding: 25px; border: 1px dashed #facc15; border-radius: 15px; margin: 10px 0; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }
    </style>
</head>
<body>
    <div class="box">
        <h2>ELITE V2.9</h2>
        
        <div id="sec-admin" class="hidden">
            <button id="btn-on" class="btn btn-admin" onclick="socket.emit('activar')">ENCENDER SERVIDOR</button>
            <button id="btn-off" class="btn btn-admin hidden" style="border-color:#ef4444; color:#ef4444;" onclick="socket.emit('cerrar_total')">CERRAR SALA (RESET)</button>
        </div>

        <div id="sec-off"><p style="color:#ef4444; font-weight:bold;">SALA CERRADA</p></div>
        
        <div id="sec-espera" class="hidden">
            <div class="waiting-msg">PARTIDA EN CURSO<br><br><span style="font-size:11px; color:#aaa;">Espera a que termine...</span></div>
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="TU NOMBRE">
            <button class="btn" onclick="registrar()">ENTRAR A JUGAR</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <p style="color:var(--accent); font-size:13px; font-weight:bold;">LOBBY</p>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:var(--accent); color:black;" onclick="socket.emit('iniciar')">¡INICIAR PARTIDA!</button>
            <div id="resultado-previo" class="res-box hidden">
                <p id="res-txt" style="margin:5px 0 0 0; font-size:14px;"></p>
            </div>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-display" style="font-size:22px; font-weight:bold; margin:20px 0;"></div>
            <p id="pista-display" style="color:var(--accent); font-size:18px;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#eab308; color:black;" onclick="socket.emit('finalizar')">REVELAR IMPOSTOR</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        
        // Función para obtener datos locales actualizados
        const getMiToken = () => localStorage.getItem('elite_tk_v29');
        const getMiNombre = () => localStorage.getItem('elite_nm_v29');

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function registrar() {
            const n = document.getElementById('nombre').value.trim();
            if(n) {
                const tk = 'tk_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('elite_tk_v29', tk);
                localStorage.setItem('elite_nm_v29', n);
                socket.emit('reconectar', {token: tk, nombre: n});
            }
        }

        socket.on('expulsar_todos', () => {
            // Se borra el nombre y token de TODO el mundo
            localStorage.removeItem('elite_tk_v29');
            localStorage.removeItem('elite_nm_v29');
            
            // Forzamos que la página vuelva a pedir el estado inicial
            location.reload(); 
        });

        socket.on('estado_servidor', (data) => {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            
            if(isAdmin) {
                document.getElementById('btn-on').classList.toggle('hidden', data.encendido);
                document.getElementById('btn-off').classList.toggle('hidden', !data.encendido);
            }

            if(!data.encendido) {
                document.getElementById('sec-off').classList.remove('hidden');
            } else {
                let nom = getMiNombre();
                if(!nom) {
                    if(data.estado === 'juego') document.getElementById('sec-espera').classList.remove('hidden');
                    else document.getElementById('sec-reg').classList.remove('hidden');
                } else {
                    socket.emit('reconectar', {token: getMiToken(), nombre: nom});
                }
            }
        });

        socket.on('pantalla_lobby', (data) => {
            if(!getMiNombre()) return;
            mostrarSeccion('sec-lobby');
            document.getElementById('lista').innerHTML = data.nombres.map(n => '• ' + n).join('<br>');
            if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
            if(data.ultimo_res) {
                document.getElementById('resultado-previo').classList.remove('hidden');
                document.getElementById('res-txt').innerHTML = "Impostor: <b style='color:#ef4444'>" + data.ultimo_res.nombre + "</b><br>Palabra: <b>" + data.ultimo_res.palabra + "</b>";
            }
        });

        socket.on('ver_rol', (data) => {
            if(!getMiNombre()) return; 
            mostrarSeccion('sec-juego');
            const res = document.getElementById('rol-display');
            const pst = document.getElementById('pista-display');
            if(data.rol === 'impostor') {
                res.innerHTML = '<span style="color:#ef4444">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "Pista: " + data.pista;
            } else {
                res.innerHTML = 'Tu Palabra: <br><span style="color:#22d3ee">' + data.palabra + '</span>';
                pst.innerHTML = "¡No te descubras!";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        function mostrarSeccion(id) {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            document.getElementById(id).classList.remove('hidden');
        }

        socket.on('connect', () => {
            let tk = getMiToken();
            let nm = getMiNombre();
            if(tk && nm) socket.emit('reconectar', {token: tk, nombre: nm});
            else socket.emit('pedir_estado');
        });
    </script>
</body>
</html>
"""

# --- LÓGICA DE SOCKETIO (Rutas) ---

@app.route('/')
def home(): return render_template_string(HTML_INDEX)

@socketio.on('pedir_estado')
def pedir_estado():
    emit('estado_servidor', {'encendido': game['encendido'], 'estado': game['estado']})

@socketio.on('activar')
def activar():
    game['encendido'] = True
    socketio.emit('estado_servidor', {'encendido': True, 'estado': game['estado']})

@socketio.on('reconectar')
def handle_reconectar(data):
    token, nombre = data.get('token'), data.get('nombre')
    if not game['encendido']:
        emit('estado_servidor', {'encendido': False})
        return
    if token and nombre:
        game['jugadores'][token] = {'nombre': nombre, 'sid': request.sid}
        if game['estado'] == "juego" and nombre in game['roles']:
            emit('ver_rol', game['roles'][nombre])
        else:
            nombres = [j['nombre'] for j in game['jugadores'].values()]
            socketio.emit('pantalla_lobby', {'nombres': nombres, 'ultimo_res': game['ultimo_resultado']})

@socketio.on('iniciar')
def iniciar():
    if len(game['jugadores']) < 2: return
    game['estado'] = "juego"
    game['roles'] = {}
    pool = [p for p in DICCIONARIO_TOTAL.keys() if p not in game['historial_palabras']]
    if not pool:
        game['historial_palabras'] = []
        pool = list(DICCIONARIO_TOTAL.keys())
    game['palabra_actual'] = random.choice(pool)
    game['historial_palabras'].append(game['palabra_actual'])
    game['pista_actual'] = DICCIONARIO_TOTAL[game['palabra_actual']]
    tokens = list(game['jugadores'].keys())
    
    # Sorteo con tickets
    nombres_sorteo, pesos = [], []
    for tk in tokens:
        nom = game['jugadores'][tk]['nombre']
        if nom not in game['tickets']: game['tickets'][nom] = 10.0
        racha = 0
        for imp in reversed(game['historial_impostores']):
            if imp == nom: racha += 1
            else: break
        peso = game['tickets'][nom] if racha == 0 else (1.0 if racha == 1 else 0.1)
        nombres_sorteo.append(tk)
        pesos.append(peso)

    impostor_tk = random.choices(nombres_sorteo, weights=pesos, k=1)[0]
    nombre_imp = game['jugadores'][impostor_tk]['nombre']
    game['historial_impostores'].append(nombre_imp)

    socketio.emit('estado_servidor', {'encendido': True, 'estado': 'juego'})
    for tk in tokens:
        nom = game['jugadores'][tk]['nombre']
        rol = 'impostor' if tk == impostor_tk else 'civil'
        if rol == 'impostor': game['tickets'][nom] = 5.0
        else: game['tickets'][nom] += 5.0
        info = {'rol': rol, 'palabra': game['palabra_actual'], 'pista': game['pista_actual']}
        game['roles'][nom] = info
        socketio.emit('ver_rol', info, room=game['jugadores'][tk]['sid'])

@socketio.on('finalizar')
def finalizar():
    imp_nombre = next((n for n, v in game['roles'].items() if v['rol'] == 'impostor'), "??")
    game['ultimo_resultado'] = {'nombre': imp_nombre, 'palabra': game['palabra_actual']}
    game['estado'] = "lobby"
    game['roles'] = {}
    socketio.emit('estado_servidor', {'encendido': True, 'estado': 'lobby'})
    nombres = [j['nombre'] for j in game['jugadores'].values()]
    socketio.emit('pantalla_lobby', {'nombres': nombres, 'ultimo_res': game['ultimo_resultado']})

@socketio.on('cerrar_total')
def cerrar():
    # 1. Borrado masivo
    socketio.emit('expulsar_todos')
    
    # 2. Reset del servidor
    game.update({
        "encendido": False, "estado": "lobby", "jugadores": {}, 
        "roles": {}, "ultimo_resultado": None, "tickets": {}, 
        "historial_impostores": [], "historial_palabras": []
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
