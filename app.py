import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_elite_final"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

game = {
    "encendido": False,
    "estado": "lobby",
    "jugadores": {},    # token: {nombre, sid}
    "roles": {},        # nombre: {rol, palabra, pista}
    "palabra_actual": "",
    "pista_actual": ""
}

RECURSOS = {
    "Arepa": "Maíz", "Hallaca": "Pabilo", "Cerveza": "Cebada", 
    "Malta": "Gas", "Tequeño": "Queso", "Empanada": "Harina",
    "Metro": "Riel", "Béisbol": "Guante", "Plátano": "Frito", 
    "Chamo": "Pana", "Sifrino": "Plata", "Moto": "Pirueta"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor Elite</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        :root { --bg: #050505; --card: #121212; --primary: #a855f7; --accent: #22d3ee; --text: #f8fafc; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); text-align: center; margin: 0; padding: 15px; }
        .box { background: var(--card); padding: 30px; border-radius: 24px; max-width: 340px; margin: 20px auto; border: 1px solid #222; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h2 { color: var(--primary); letter-spacing: 2px; text-transform: uppercase; font-size: 28px; margin-bottom: 25px; }
        .btn { background: var(--primary); color: white; border: none; padding: 16px; border-radius: 12px; width: 100%; cursor: pointer; margin-top: 15px; font-weight: bold; font-size: 15px; transition: 0.3s; }
        .btn:active { transform: scale(0.98); opacity: 0.8; }
        .btn-admin { background: transparent; border: 1px solid var(--accent); color: var(--accent); font-size: 12px; }
        .hidden { display: none !important; }
        #lista { text-align: left; background: #000; padding: 15px; border-radius: 15px; margin: 20px 0; border: 1px solid #1a1a1a; line-height: 2; }
        input { width: 90%; padding: 14px; margin-bottom: 15px; border-radius: 10px; border: 1px solid #333; background: #1a1a1a; color: white; outline: none; }
        input:focus { border-color: var(--primary); }
        .status-tag { font-size: 12px; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>ELITE</h2>
        
        <div id="sec-off">
            <p style="color:#ef4444; font-weight:bold;">SALA CERRADA</p>
            <p class="status-tag">El administrador activará la partida pronto.</p>
        </div>
        
        <div id="sec-admin" class="hidden">
            <button class="btn btn-admin" onclick="socket.emit('activar')">ENCENDER SERVIDOR</button>
            <button class="btn btn-admin" style="border-color:#ef4444; color:#ef4444;" onclick="socket.emit('cerrar_total')">CERRAR TODO</button>
            <hr style="border:0.5px solid #222; margin:20px 0;">
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="Escribe tu nombre...">
            <button class="btn" onclick="registrar()">UNIRSE AL JUEGO</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <p style="color:var(--accent); font-size:14px;">Jugadores conectados:</p>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:var(--accent); color:black;" onclick="socket.emit('iniciar')">EMPEZAR AHORA</button>
            <p class="status-tag">Esperando al líder...</p>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-display" style="font-size:24px; font-weight:bold; margin:30px 0;"></div>
            <p id="pista-display" style="color:var(--accent); font-size:20px; font-style:italic;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#eab308; color:black;" onclick="socket.emit('finalizar')">TERMINAR JUEGO</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        let miToken = localStorage.getItem('elite_token');
        let miNombre = localStorage.getItem('elite_name');

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function registrar() {
            const n = document.getElementById('nombre').value.trim();
            if(n) {
                miNombre = n;
                miToken = 'tk_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('elite_token', miToken);
                localStorage.setItem('elite_name', miNombre);
                socket.emit('reconectar', {token: miToken, nombre: miNombre});
            }
        }

        socket.on('connect', () => {
            if(miToken) socket.emit('reconectar', {token: miToken, nombre: miNombre});
            else socket.emit('pedir_estado');
        });

        socket.on('estado_servidor', (data) => {
            if(!data.encendido) {
                mostrarSeccion('sec-off');
                localStorage.clear();
                miNombre = null;
            } else {
                if(!miNombre) mostrarSeccion('sec-reg');
                else socket.emit('reconectar', {token: miToken, nombre: miNombre});
            }
        });

        socket.on('pantalla_lobby', (data) => {
            if(!miNombre) return; // SI NO SE HA REGISTRADO, NO ENTRA AL LOBBY
            mostrarSeccion('sec-lobby');
            document.getElementById('lista').innerHTML = data.nombres.map(n => '• ' + n).join('<br>');
            if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
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
                res.innerHTML = 'Palabra: <br><span style="color:#22d3ee">' + data.palabra + '</span>';
                pst.innerHTML = "¡Cuidado con el impostor!";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        function mostrarSeccion(id) {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            document.getElementById(id).classList.remove('hidden');
        }

        socket.on('revelar_final', (data) => {
            alert("IMPOSTOR: " + data.nombre + "\\nPALABRA: " + data.palabra);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML_INDEX)

@socketio.on('pedir_estado')
def pedir_estado():
    emit('estado_servidor', {'encendido': game['encendido']})

@socketio.on('activar')
def activar():
    game['encendido'] = True
    socketio.emit('estado_servidor', {'encendido': True})

@socketio.on('reconectar')
def handle_reconectar(data):
    token = data.get('token')
    nombre = data.get('nombre')
    
    if not game['encendido']:
        emit('estado_servidor', {'encendido': False})
        return

    if token and nombre:
        game['jugadores'][token] = {'nombre': nombre, 'sid': request.sid}
        
        # SI LA PARTIDA YA EMPEZÓ
        if game['estado'] == "juego" and nombre in game['roles']:
            emit('ver_rol', game['roles'][nombre])
        # SI ESTÁ EN EL LOBBY
        else:
            nombres = [j['nombre'] for j in game['jugadores'].values()]
            socketio.emit('pantalla_lobby', {'nombres': nombres})
    else:
        # Si no tiene nombre ni token, se queda en registro
        emit('estado_servidor', {'encendido': True})

@socketio.on('iniciar')
def iniciar():
    if len(game['jugadores']) < 2: return
    game['estado'] = "juego"
    game['roles'] = {}
    tokens = list(game['jugadores'].keys())
    impostor_token = random.choice(tokens)
    game['palabra_actual'], game['pista_actual'] = random.choice(list(RECURSOS.items()))
    
    for tk in tokens:
        nombre = game['jugadores'][tk]['nombre']
        rol = 'impostor' if tk == impostor_token else 'civil'
        info = {'rol': rol, 'palabra': game['palabra_actual'], 'pista': game['pista_actual']}
        game['roles'][nombre] = info
        socketio.emit('ver_rol', info, room=game['jugadores'][tk]['sid'])

@socketio.on('finalizar')
def finalizar():
    imp_nombre = next((n for n, v in game['roles'].items() if v['rol'] == 'impostor'), "??")
    socketio.emit('revelar_final', {'nombre': imp_nombre, 'palabra': game['palabra_actual']})
    game['estado'] = "lobby"
    game['roles'] = {}
    nombres = [j['nombre'] for j in game['jugadores'].values()]
    socketio.emit('pantalla_lobby', {'nombres': nombres})

@socketio.on('cerrar_total')
def cerrar():
    game.update({"encendido": False, "estado": "lobby", "jugadores": {}, "roles": {}})
    socketio.emit('estado_servidor', {'encendido': False})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
