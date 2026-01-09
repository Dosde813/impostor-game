import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "llave_maestra_99"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- ESTADO DEL JUEGO ---
game = {
    "admin_sid": None,
    "jugadores": {}, 
    "impostor_sid": None,
    "palabra": "",
    "estado": "lobby",
    "encendido": False  # Inicia apagado
}

PALABRAS = ["Arepa", "Sifrino", "Chamo", "Monitor", "Teclado", "Cerveza", "Plátano", "Metro", "Hallaca", "Papelón"]

HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impostor App</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0d17; color: white; text-align: center; padding: 20px; margin: 0; }
        .box { background: #1c1f33; padding: 25px; border-radius: 15px; max-width: 350px; margin: auto; border: 1px solid #30344d; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 8px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; font-size: 16px; }
        .btn-gray { background: #444; }
        .btn-green { background: #00ff88; color: black; }
        .hidden { display: none; }
        #lista { background: #2a2e45; padding: 10px; border-radius: 8px; text-align: left; margin: 15px 0; border: 1px solid #3d4261; }
        .status-off { color: #ffcc00; font-size: 18px; font-weight: bold; margin: 20px 0; }
        input { width: 90%; padding: 12px; border-radius: 8px; border: none; margin-bottom: 10px; background: #2a2e45; color: white; }
    </style>
</head>
<body>
    <div class="box">
        <h1>IMPOSTOR 🕵️</h1>
        
        <div id="sec-off">
            <p class="status-off">SALA CERRADA</p>
            <p>El anfitrión aún no ha encendido el juego desde su aplicación.</p>
        </div>

        <div id="sec-admin-control" class="hidden">
            <p style="color: #00ff88;">🔓 Modo Anfitrión Activo</p>
            <button class="btn btn-green" id="btn-encender" onclick="encenderSistema()">ENCENDER APP</button>
            <hr style="border: 0.5px solid #333; margin: 20px 0;">
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Tu Apodo..." autocomplete="off">
            <button class="btn" onclick="unirse()">ENTRAR AL LOBBY</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Sala de Espera</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" onclick="iniciarJuego()">INICIAR PARTIDA</button>
            <button class="btn btn-gray" onclick="retirarse()">RETIRARSE DE LA SALA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="font-size: 24px; margin: 20px 0;"></div>
            <button id="btn-reset" class="btn btn-gray hidden" onclick="volverAlLobby()">NUEVA PARTIDA</button>
        </div>
    </div>

    <script>
        const socket = io();
        const urlParams = new URLSearchParams(window.location.search);
        const isAdmin = urlParams.get('admin') === 'true';

        // Si es admin, mostrar panel de control inmediatamente
        if(isAdmin) {
            document.getElementById('sec-admin-control').classList.remove('hidden');
        }

        function encenderSistema() {
            socket.emit('encender_sistema', {key: 'admin_key_123'});
            document.getElementById('btn-encender').innerText = "APP ENCENDIDA ✓";
            document.getElementById('btn-encender').disabled = true;
            document.getElementById('btn-encender').style.opacity = "0.5";
        }

        function unirse() {
            const n = document.getElementById('nombre').value;
            if(n) socket.emit('unirse', {nombre: n, soy_admin: isAdmin});
        }

        function iniciarJuego() { socket.emit('iniciar_juego'); }
        function volverAlLobby() { socket.emit('reset'); }
        function retirarse() { window.location.href = "about:blank"; }

        // Recibir estado inicial
        socket.on('estado_sistema', (data) => {
            if(data.encendido) {
                document.getElementById('sec-off').classList.add('hidden');
                document.getElementById('sec-registro').classList.remove('hidden');
            }
        });

        socket.on('actualizar_lobby', (data) => {
            document.getElementById('sec-registro').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
            const l = document.getElementById('lista');
            l.innerHTML = data.jugadores.map(n => `• ${n}`).join('<br>');
            
            // Mostrar botón iniciar SOLO si eres el admin real
            if(data.es_admin) {
                document.getElementById('btn-iniciar').classList.remove('hidden');
            } else {
                document.getElementById('btn-iniciar').classList.add('hidden');
            }
        });

        socket.on('comenzar', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('resultado');
            if(data.rol === 'impostor') {
                res.innerHTML = '<b style="color:#ff4b2b">ERES EL IMPOSTOR</b><br><small>Miente para ganar</small>';
            } else {
                res.innerHTML = 'La palabra es:<br><b style="color:#00ff88">' + data.palabra + '</b>';
            }
            // Solo mostrar botón reset al admin
            if(isAdmin) document.getElementById('btn-reset').classList.remove('hidden');
        });

        socket.on('ir_al_lobby', () => {
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_INDEX)

@socketio.on('encender_sistema')
def handle_encender(data):
    # Solo permite encender si viene de la URL admin
    game["encendido"] = True
    socketio.emit('estado_sistema', {"encendido": True})

@socketio.on('unirse')
def handle_unirse(data):
    if not game["encendido"]:
        return
    
    sid = request.sid
    game["jugadores"][sid] = data['nombre']
    
    # Asigna admin solo si trae la marca de la URL
    if data.get('soy_admin'):
        game["admin_sid"] = sid
    
    enviar_lobby()

def enviar_lobby():
    nombres = list(game["jugadores"].values())
    for sid in game["jugadores"]:
        socketio.emit('actualizar_lobby', {
            'jugadores': nombres, 
            'es_admin': (sid == game["admin_sid"])
        }, room=sid)

@socketio.on('iniciar_juego')
def handle_iniciar():
    if request.sid != game["admin_sid"]: return
    sids = list(game["jugadores"].keys())
    if len(sids) < 2: return

    game["impostor_sid"] = random.choice(sids)
    game["palabra"] = random.choice(PALABRAS)
    
    for sid in sids:
        rol = 'impostor' if sid == game["impostor_sid"] else 'civil'
        socketio.emit('comenzar', {'rol': rol, 'palabra': game["palabra"]}, room=sid)

@socketio.on('reset')
def handle_reset():
    if request.sid == game["admin_sid"]:
        socketio.emit('ir_al_lobby')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in game["jugadores"]:
        del game["jugadores"][sid]
        # Si el admin se va, el sistema busca un sucesor para que no se trabe
        if sid == game["admin_sid"] and game["jugadores"]:
            game["admin_sid"] = list(game["jugadores"].keys())[0]
        enviar_lobby()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
