import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_v16_final_fix"
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
    "Chamo": "Pana", "Sifrino": "Plata", "Moto": "Casco"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor V16</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; margin: 0; padding: 15px; }
        .box { background: #1c1f33; padding: 25px; border-radius: 20px; max-width: 320px; margin: 10px auto; border: 1px solid #444; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 10px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; font-size: 16px; }
        .hidden { display: none !important; }
        #lista { text-align: left; background: #0b0d17; padding: 12px; border-radius: 10px; margin: 15px 0; border: 1px solid #333; }
        input { width: 88%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #444; background: #2a2e45; color: white; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="color:#ff4b2b;">IMPOSTOR</h2>
        
        <div id="sec-off">
            <p style="color:#ffcc00; font-weight:bold;">SALA CERRADA</p>
        </div>
        
        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:#000;" onclick="socket.emit('activar')">ENCENDER APP</button>
            <button class="btn" style="background:#444;" onclick="socket.emit('cerrar_total')">CERRAR TODO</button>
            <hr style="border:0.5px solid #444; margin:15px 0;">
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="Tu nombre">
            <button class="btn" onclick="registrar()">ENTRAR AL LOBBY</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:#000;" onclick="socket.emit('iniciar')">¡INICIAR PARTIDA!</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-display" style="font-size:22px; font-weight:bold; margin:20px 0;"></div>
            <p id="pista-display" style="color:#aaa; font-size:20px;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#ffcc00; color:#000;" onclick="socket.emit('finalizar')">REVELAR IMPOSTOR</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        let miToken = localStorage.getItem('imp_token_v16');
        let miNombre = localStorage.getItem('imp_name_v16');

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function registrar() {
            const n = document.getElementById('nombre').value.trim();
            if(n) {
                miNombre = n;
                miToken = 'tk_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('imp_token_v16', miToken);
                localStorage.setItem('imp_name_v16', miNombre);
                socket.emit('reconectar', {token: miToken, nombre: miNombre});
            }
        }

        socket.on('connect', () => {
            if(miToken) socket.emit('reconectar', {token: miToken, nombre: miNombre});
            else socket.emit('pedir_estado');
        });

        socket.on('estado_servidor', (data) => {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            
            if(!data.encendido) {
                document.getElementById('sec-off').classList.remove('hidden');
            } else if(!miNombre) {
                document.getElementById('sec-reg').classList.remove('hidden');
            } else {
                socket.emit('reconectar', {token: miToken, nombre: miNombre});
            }
        });

        socket.on('pantalla_lobby', (data) => {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            document.getElementById('sec-lobby').classList.remove('hidden');
            document.getElementById('lista').innerHTML = data.nombres.map(n => '• ' + n).join('<br>');
            if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
        });

        socket.on('ver_rol', (data) => {
            document.querySelectorAll('.box > div:not(#sec-admin)').forEach(d => d.classList.add('hidden'));
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('rol-display');
            const pst = document.getElementById('pista-display');
            if(data.rol === 'impostor') {
                res.innerHTML = '<span style="color:#ff4b2b">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "<b>Pista:</b> " + data.pista;
            } else {
                res.innerHTML = 'Palabra: <br><span style="color:#00ff88">' + data.palabra + '</span>';
                pst.innerHTML = "";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        socket.on('revelar_final', (data) => {
            alert("Impostor: " + data.nombre + "\\nPalabra: " + data.palabra);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_INDEX)

@socketio.on('pedir_estado')
def pedir_estado():
    emit('estado_servidor', {'encendido': game['encendido']})

@socketio.on('activar')
def activar():
    game['encendido'] = True
    # El "grito" global que despierta a todos los celulares
    socketio.emit('estado_servidor', {'encendido': True})

@socketio.on('reconectar')
def handle_reconectar(data):
    token = data.get('token')
    nombre = data.get('nombre')
    
    if not game['encendido']:
        emit('estado_servidor', {'encendido': False})
        return

    if token:
        game['jugadores'][token] = {'nombre': nombre, 'sid': request.sid}
        if game['estado'] == "juego" and nombre in game['roles']:
            emit('ver_rol', game['roles'][nombre])
        else:
            nombres = [j['nombre'] for j in game['jugadores'].values()]
            socketio.emit('pantalla_lobby', {'nombres': nombres})

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
