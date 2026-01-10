import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_impostor_v3"
# Configuración optimizada para respuesta inmediata
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=False, engineio_logger=False)

game = {
    "admin_sid": None,
    "jugadores": {}, 
    "impostor_sid": None,
    "palabra": "",
    "pista": "",
    "encendido": False,
    "en_partida": False
}

RECURSOS = {
    "Arepa": "Comida de maíz", "Sifrino": "Persona creída", "Chamo": "Un joven",
    "Monitor": "Pantalla", "Teclado": "Para escribir", "Cerveza": "Bebida con espuma",
    "Plátano": "Fruta amarilla", "Metro": "Tren bajo tierra", "Hallaca": "Navidad",
    "Papelón": "Bebida de caña"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor Realtime</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; margin: 0; padding: 15px; }
        .box { background: #1c1f33; padding: 20px; border-radius: 15px; max-width: 320px; margin: 20px auto; border: 1px solid #444; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 8px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .hidden { display: none; }
        #lista { text-align: left; background: #0b0d17; padding: 10px; border-radius: 8px; margin: 15px 0; border: 1px solid #333; min-height: 50px; }
        input { width: 85%; padding: 12px; margin-bottom: 10px; border-radius: 5px; border: none; background: #2a2e45; color: white; font-size: 16px; }
    </style>
</head>
<body>
    <div class="box">
        <h1 style="color: #ff4b2b;">IMPOSTOR</h1>
        
        <div id="sec-off">
            <p style="color: #ffcc00;">SALA CERRADA</p>
        </div>

        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:#000;" onclick="encender()">ENCENDER SERVIDOR</button>
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Tu apodo...">
            <button class="btn" onclick="unirse()">ENTRAR AL JUEGO</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Jugadores: <span id="count">0</span></h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:#000;" onclick="iniciar()">INICIAR PARTIDA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="font-size: 20px; margin: 20px 0;"></div>
            <p id="pista-imp" style="color: #aaa; font-style: italic;"></p>
            <button id="btn-finalizar" class="btn hidden" style="background:#ffcc00; color:#000;" onclick="finalizar()">REVELAR Y TERMINAR</button>
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
        function finalizar() { socket.emit('finalizar_partida'); }

        socket.on('estado', (data) => {
            if(data.encendido) {
                document.getElementById('sec-off').classList.add('hidden');
                document.getElementById('sec-registro').classList.remove('hidden');
            }
        });

        socket.on('lista_lobby', (data) => {
            document.getElementById('sec-registro').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
            document.getElementById('count').innerText = data.jugadores.length;
            document.getElementById('lista').innerHTML = data.jugadores.map(j => '• ' + j).join('<br>');
            
            // Verificación de Admin para el botón de inicio
            if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
        });

        socket.on('repartir_roles', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('resultado');
            const pst = document.getElementById('pista-imp');
            
            if(data.rol === 'impostor') {
                res.innerHTML = '<span style="color:red">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "Pista: " + data.pista;
            } else {
                res.innerHTML = 'Palabra: <br><span style="color:#00ff88">' + data.palabra + '</span>';
                pst.innerHTML = "";
            }
            if(isAdmin) document.getElementById('btn-finalizar').classList.remove('hidden');
        });

        socket.on('revelar_final', (data) => {
            alert("EL IMPOSTOR ERA: " + data.nombre_impostor + "\\nPALABRA: " + data.palabra);
            location.reload(); // Recarga para limpiar todo y volver al lobby
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_INDEX)

@socketio.on('connect')
def connect():
    emit('estado', {"encendido": game["encendido"]})

@socketio.on('activar_servidor')
def activar():
    game["encendido"] = True
    socketio.emit('estado', {"encendido": True})

@socketio.on('unirse_jugador')
def unirse(data):
    game["jugadores"][request.sid] = data['nombre']
    if data.get('es_admin'): game["admin_sid"] = request.sid
    
    nombres = list(game["jugadores"].values())
    socketio.emit('lista_lobby', {'jugadores': nombres}, include_self=True)

@socketio.on('dar_inicio')
def inicio():
    if len(game["jugadores"]) < 2: return
    sids = list(game["jugadores"].keys())
    game["impostor_sid"] = random.choice(sids)
    game["palabra"], game["pista"] = random.choice(list(RECURSOS.items()))
    
    for sid in sids:
        rol = 'impostor' if sid == game["impostor_sid"] else 'civil'
        socketio.emit('repartir_roles', {
            'rol': rol, 
            'palabra': game["palabra"], 
            'pista': game["pista"]
        }, room=sid)

@socketio.on('finalizar_partida')
def finalizar():
    nombre_imp = game["jugadores"].get(game["impostor_sid"], "Desconocido")
    socketio.emit('revelar_final', {
        'nombre_impostor': nombre_imp, 
        'palabra': game["palabra"]
    })

@socketio.on('disconnect')
def disconnect():
    if request.sid in game["jugadores"]:
        del game["jugadores"][request.sid]
        nombres = list(game["jugadores"].values())
        socketio.emit('lista_lobby', {'jugadores': nombres})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)
