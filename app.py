import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_elite_v2_5_externo"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- CARGA DINÁMICA DE PALABRAS ---
DICCIONARIO_TOTAL = {}

def cargar_palabras():
    global DICCIONARIO_TOTAL
    dict_temp = {}
    try:
        # Intentamos leer el archivo palabras.txt
        with open('palabras.txt', 'r', encoding='utf-8') as f:
            for linea in f:
                if ":" in linea:
                    palabra, pista = linea.strip().split(":")
                    dict_temp[palabra] = pista
        if dict_temp:
            DICCIONARIO_TOTAL = dict_temp
            print(f"✅ Éxito: {len(DICCIONARIO_TOTAL)} palabras cargadas.")
        else:
            raise ValueError("El archivo está vacío")
    except Exception as e:
        # Si el archivo no existe o falla, carga este mini-respaldo para que el juego no muera
        print(f"⚠️ Error cargando archivo: {e}. Usando respaldo.")
        DICCIONARIO_TOTAL = {"Error": "Archivo no encontrado", "Avisar": "Al Administrador"}

# Cargar al iniciar
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

# (El HTML es exactamente el mismo de la v2.4, lo mantengo intacto)
HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor Elite v2.5</title>
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
        <h2>ELITE V2.5</h2>
        <div id="sec-off"><p style="color:#ef4444; font-weight:bold;">SALA CERRADA</p></div>
        <div id="sec-admin" class="hidden">
            <button class="btn btn-admin" onclick="socket.emit('activar')">ENCENDER</button>
            <button class="btn btn-admin" style="border-color:#ef4444; color:#ef4444;" onclick="socket.emit('cerrar_total')">APAGAR</button>
        </div>
        <div id="sec-espera" class="hidden">
            <div class="waiting-msg">PARTIDA EN CURSO<br><br><span style="font-size:11px; color:#aaa;">Espera a que termine para unirte...</span></div>
        </div>
        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="TU NOMBRE">
            <button class="btn" onclick="registrar()">UNIRSE</button>
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
        let miToken = localStorage.getItem('elite_tk_v25');
        let miNombre = localStorage.getItem('elite_nm_v25');
        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');
        function registrar() {
            const n = document.getElementById('nombre').value.trim();
            if(n) {
                miNombre = n;
                miToken = 'tk_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('elite_tk_v25', miToken);
                localStorage.setItem('elite_nm_v25', miNombre);
                socket.emit('reconectar', {token: miToken, nombre: miNombre});
            }
        }
        socket.on('connect', () => {
            if(miToken) socket.emit('reconectar', {token: miToken, nombre: miNombre});
            else socket.emit('pedir_estado');
        });
        socket.on('estado_servidor', (data) => {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            if(!data.encendido) { document.getElementById('sec-off').classList.remove('hidden'); }
            else {
                if(!miNombre) {
                    if(data.estado === 'juego') document.getElementById('sec-espera').classList.remove('hidden');
                    else document.getElementById('sec-reg').classList.remove('hidden');
                } else { socket.emit('reconectar', {token: miToken, nombre: miNombre}); }
            }
        });
        socket.on('pantalla_lobby', (data) => {
            if(!miNombre) return;
            mostrarSeccion('sec-lobby');
            document.getElementById('lista').innerHTML = data.nombres.map(n => '• ' + n).join('<br>');
            if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
            if(data.ultimo_res) {
                document.getElementById('resultado-previo').classList.remove('hidden');
                document.getElementById('res-txt').innerHTML = "Impostor: <b style='color:#ef4444'>" + data.ultimo_res.nombre + "</b><br>Palabra: <b>" + data.ultimo_res.palabra + "</b>";
            }
        });
        socket.on('ver_rol', (data) => {
            if(!miNombre) return; 
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
    </script>
</body>
</html>
"""

# --- LÓGICA DE SOCKETS (Mantiene todo lo definido antes) ---

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
    else:
        emit('estado_servidor', {'encendido': True, 'estado': game['estado']})

@socketio.on('iniciar')
def iniciar():
    if len(game['jugadores']) < 2: return
    game['estado'] = "juego"
    game['roles'] = {}
    
    # 1. Rotación de Palabras (Ahora lee del diccionario cargado del archivo)
    pool = [p for p in DICCIONARIO_TOTAL.keys() if p not in game['historial_palabras']]
    if not pool:
        game['historial_palabras'] = []
        pool = list(DICCIONARIO_TOTAL.keys())
    game['palabra_actual'] = random.choice(pool)
    game['historial_palabras'].append(game['palabra_actual'])
    game['pista_actual'] = DICCIONARIO_TOTAL[game['palabra_actual']]
    
    # 2. SISTEMA MÍSTICO (Pesos)
    tokens = list(game['jugadores'].keys())
    nombres_para_sorteo, pesos = [], []
    for tk in tokens:
        nombre = game['jugadores'][tk]['nombre']
        if nombre not in game['tickets']: game['tickets'][nombre] = 10.0
        racha = 0
        for imp in reversed(game['historial_impostores']):
            if imp == nombre: racha += 1
            else: break
        if racha == 0: peso = game['tickets'][nombre]
        elif racha == 1: peso = 1.0
        elif racha == 2: peso = 0.1
        else: peso = 0.01
        nombres_para_sorteo.append(tk)
        pesos.append(peso)

    impostor_token = random.choices(nombres_para_sorteo, weights=pesos, k=1)[0]
    nombre_impostor = game['jugadores'][impostor_token]['nombre']
    game['historial_impostores'].append(nombre_impostor)

    socketio.emit('estado_servidor', {'encendido': True, 'estado': 'juego'})

    # 3. Asignar Roles
    for tk in tokens:
        nombre = game['jugadores'][tk]['nombre']
        if tk == impostor_token:
            rol = 'impostor'
            game['tickets'][nombre] = 5.0
        else:
            rol = 'civil'
            game['tickets'][nombre] += 5.0
        info = {'rol': rol, 'palabra': game['palabra_actual'], 'pista': game['pista_actual']}
        game['roles'][nombre] = info
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
    game.update({"encendido": False, "estado": "lobby", "jugadores": {}, "roles": {}, "ultimo_resultado": None, "tickets": {}, "historial_impostores": []})
    socketio.emit('estado_servidor', {'encendido': False, 'estado': 'lobby'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
