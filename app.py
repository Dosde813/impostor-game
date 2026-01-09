import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "secret_key_123"
# Volvemos a la configuración simple que te funcionaba antes
socketio = SocketIO(app, cors_allowed_origins="*")

game = {
    "admin_sid": None,
    "jugadores": {}, 
    "impostor_sid": None,
    "palabra": "",
    "encendido": False # Esta es la variable que ahora sí se queda guardada
}

PALABRAS = ["Arepa", "Sifrino", "Chamo", "Monitor", "Teclado", "Cerveza", "Plátano", "Metro", "Hallaca", "Papelón"]

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>¿Quién es el Impostor?</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; padding: 20px; }
        .box { background: #1c1f33; padding: 20px; border-radius: 15px; max-width: 300px; margin: auto; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 12px; border-radius: 5px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .hidden { display: none; }
        #lista { text-align: left; background: #2a2e45; padding: 10px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="box">
        <h1>¿QUIÉN ES EL IMPOSTOR?</h1>
        
        <div id="sec-off">
            <p style="color: #ffcc00;">SALA CERRADA</p>
            <p>Esperando al anfitrión...</p>
        </div>

        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:black;" id="btn-on" onclick="encender()">ENCENDER APP</button>
            <hr>
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Tu nombre..." style="width:80%; padding:10px; margin-bottom:10px;">
            <button class="btn" onclick="unirse()">ENTRAR</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Jugadores:</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" onclick="iniciar()">INICIAR JUEGO</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="font-size: 20px; margin: 20px 0;"></div>
            <button id="btn-reset" class="btn hidden" onclick="reset()">NUEVA PARTIDA</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = new URLSearchParams(window.location.search).get('admin') === 'true';

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function encender() { socket.emit('activar_servidor'); }
        function unirse() {
            const n = document.getElementById('nombre').value;
            if(n) socket.emit('unirse_jugador', {nombre: n, es_admin: isAdmin});
        }
        function iniciar() { socket.emit('dar_inicio'); }
        function reset() { socket.emit('volver_lobby'); }

        socket.on('estado', (data) => {
            if(data.encendido) {
                document.getElementById('sec-off').classList.add('hidden');
                if(document.getElementById('sec-lobby').classList.contains('hidden') && 
                   document.getElementById('sec-juego').classList.contains('hidden')) {
                    document.getElementById('sec-registro').classList.remove('hidden');
                }
            }
        });

        socket.on('lista_lobby', (data) => {
            document.getElementById('sec-registro').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
            document.getElementById('lista').innerHTML = data.jugadores.join('<br>');
            if(data.soy_admin) document.getElementById('btn-iniciar').classList.remove('hidden');
        });

        socket.on('repartir_roles', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            document.getElementById('resultado').innerHTML = data.rol === 'impostor' ? 'ERES EL IMPOSTOR' : 'Palabra: ' + data.palabra;
            if(isAdmin) document.getElementById('btn-reset').classList.remove('hidden');
        });

        socket.on('limpiar', () => {
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
        });
    </script>
</body>
</html>
"""

@socketio.on('connect')
def connect():
    # Cuando alguien entra, le decimos si ya está encendido o no
    emit('estado', {"encendido": game["encendido"]})

@socketio.on('activar_servidor')
def activar():
    game["encendido"] = True
    socketio.emit('estado', {"encendido": True})

@socketio.on('unirse_jugador')
def unirse(data):
    if not game["encendido"]: return
    game["jugadores"][request.sid] = data['nombre']
    if data.get('es_admin'): game["admin_sid"] = request.sid
    actualizar()

def actualizar():
    nombres = list(game["jugadores"].values())
    for sid in game["jugadores"]:
        socketio.emit('lista_lobby', {'jugadores': nombres, 'soy_admin': (sid == game["admin_sid"])}, room=sid)

@socketio.on('dar_inicio')
def inicio():
    if request.sid != game["admin_sid"]: return
    sids = list(game["jugadores"].keys())
    game["impostor_sid"] = random.choice(sids)
    game["palabra"] = random.choice(PALABRAS)
    for sid in sids:
        rol = 'impostor' if sid == game["impostor_sid"] else 'civil'
        socketio.emit('repartir_roles', {'rol': rol, 'palabra': game["palabra"]}, room=sid)

@socketio.on('volver_lobby')
def volver():
    if request.sid == game["admin_sid"]:
        socketio.emit('limpiar')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    # Usamos la forma de arranque que NO te daba error antes
    socketio.run(app, host='0.0.0.0', port=port)
