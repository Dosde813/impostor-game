import os
import random
from flask import Flask, render_template_string, request, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_maestra_impostor"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

game = {
    "admin_sid": None,
    "jugadores": {}, 
    "impostor_sid": None,
    "palabra": "",
    "estado": "lobby",
    "encendido": False  # Nueva lógica: el juego empieza apagado
}

PALABRAS = ["Arepa", "Sifrino", "Chamo", "Monitor", "Teclado", "Cerveza", "Plátano", "Metro"]

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impostor App</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Arial', sans-serif; background: #0b0d17; color: white; text-align: center; padding: 20px; }
        .box { background: #1c1f33; padding: 25px; border-radius: 15px; max-width: 350px; margin: auto; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 12px; border-radius: 8px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .btn-gray { background: #555; }
        .hidden { display: none; }
        #lista { background: #2a2e45; padding: 10px; border-radius: 8px; text-align: left; margin: 10px 0; }
        .status-off { color: #ffcc00; font-weight: bold; }
    </style>
</head>
<body>
    <div class="box">
        <h1>IMPOSTOR 🕵️</h1>
        
        <div id="sec-off" class="hidden">
            <p class="status-off">EL ANFITRIÓN NO HA ENCENDIDO EL JUEGO</p>
            <p>Espera a que tu amigo inicie la aplicación en su teléfono.</p>
        </div>

        <div id="sec-admin-control" class="hidden">
            <button class="btn" style="background: #00ff88; color: black;" onclick="encenderJuego()">ENCENDER APP</button>
            <hr>
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Tu Apodo..." style="width:90%; padding:10px; margin-bottom:10px;">
            <button class="btn" onclick="unirse()">ENTRAR AL LOBBY</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Lobby</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" onclick="iniciarJuego()">INICIAR PARTIDA</button>
            <button class="btn btn-gray" onclick="retirarse()">RETIRARSE</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado"></div>
            <button id="btn-reset" class="btn btn-gray hidden" onclick="volverAlLobby()">NUEVA PARTIDA (ADMIN)</button>
        </div>
    </div>

    <script>
        const socket = io();
        // Detectar si es el anfitrión por un parámetro en la URL (ej: ?admin=true)
        const urlParams = new URLSearchParams(window.location.search);
        const isAdminDevice = urlParams.get('admin') === 'true';

        if(isAdminDevice) {
            document.getElementById('sec-admin-control').classList.remove('hidden');
        }

        function encenderJuego() {
            socket.emit('encender_sistema');
            document.getElementById('sec-admin-control').classList.add('hidden');
        }

        function unirse() {
            const n = document.getElementById('nombre').value;
            if(n) socket.emit('unirse', {nombre: n});
        }

        function iniciarJuego() { socket.emit('iniciar_juego'); }
        function volverAlLobby() { socket.emit('reset'); }
        function retirarse() { location.reload(); } // Al recargar se desconecta solo

        socket.on('estado_sistema', (data) => {
            if(!data.encendido) {
                document.getElementById('sec-off').classList.remove('hidden');
                document.getElementById('sec-registro').classList.add('hidden');
            } else {
                document.getElementById('sec-off').classList.add('hidden');
                document.getElementById('sec-registro').classList.remove('hidden');
            }
        });

        socket.on('actualizar_lobby', (data) => {
            document.getElementById('sec-registro').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
            const l = document.getElementById('lista');
            l.innerHTML = data.jugadores.map(n => `• ${n}`).join('<br>');
            
            if(data.es_admin) document.getElementById('btn-iniciar').classList.remove('hidden');
        });

        socket.on('comenzar', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            document.getElementById('resultado').innerHTML = data.rol === 'impostor' ? 'Eres IMPOSTOR' : 'Palabra: ' + data.palabra;
            
            // Solo el admin ve el botón de reiniciar
            if(isAdminDevice) document.getElementById('btn-reset').classList.remove('hidden');
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
def handle_encender():
    game["encendido"] = True
    socketio.emit('estado_sistema', {"encendido": True})

@socketio.on('unirse')
def handle_unirse(data):
    if not game["encendido"]: return
    sid = request.sid
    game["jugadores"][sid] = data['nombre']
    if not game["admin_sid"]: game["admin_sid"] = sid
    enviar_lobby()

def enviar_lobby():
    nombres = list(game["jugadores"].values())
    for sid in game["jugadores"]:
        socketio.emit('actualizar_lobby', {'jugadores': nombres, 'es_admin': sid == game["admin_sid"]}, room=sid)

@socketio.on('iniciar_juego')
def handle_iniciar():
    if request.sid != game["admin_sid"]: return
    sids = list(game["jugadores"].keys())
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
        if sid == game["admin_sid"] and game["jugadores"]:
            game["admin_sid"] = list(game["jugadores"].keys())[0]
        enviar_lobby()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
