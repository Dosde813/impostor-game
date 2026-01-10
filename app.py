import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_segura_123"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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
    "Arepa": "Comida típica hecha de maíz",
    "Sifrino": "Persona que cree tener mucha clase",
    "Chamo": "Persona joven",
    "Monitor": "Pantalla de computadora",
    "Teclado": "Periférico para escribir",
    "Cerveza": "Bebida fría con alcohol",
    "Plátano": "Fruta tropical amarilla",
    "Metro": "Tren subterráneo",
    "Hallaca": "Plato navideño",
    "Papelón": "Bebida dulce de caña"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impostor</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; padding: 20px; margin: 0; }
        .box { background: #1c1f33; padding: 20px; border-radius: 15px; max-width: 320px; margin: 40px auto; border: 1px solid #333; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 12px; border-radius: 5px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .btn-exit { position: fixed; bottom: 20px; left: 20px; background: rgba(255, 255, 255, 0.1); color: #aaa; border: 1px solid #444; padding: 8px 15px; border-radius: 20px; font-size: 13px; cursor: pointer; }
        .hidden { display: none; }
        #lista { text-align: left; background: #2a2e45; padding: 10px; border-radius: 5px; margin: 15px 0; }
        input { width: 85%; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: none; background: #2a2e45; color: white; }
    </style>
</head>
<body>
    <div class="box">
        <h1>IMPOSTOR</h1>
        
        <div id="sec-off">
            <p style="color: #ffcc00;">SALA CERRADA</p>
        </div>

        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:black;" onclick="socket.emit('activar_servidor')">ENCENDER APP</button>
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Tu Apodo...">
            <button class="btn" onclick="unirse()">ENTRAR</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Lobby</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:black;" onclick="socket.emit('dar_inicio')">INICIAR PARTIDA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="font-size: 20px; margin: 20px 0; font-weight: bold;"></div>
            <p id="pista-imp" style="color: #aaa; font-style: italic;"></p>
            <button id="btn-finalizar" class="btn hidden" style="background:#ffcc00; color:black;" onclick="socket.emit('finalizar_partida')">FINALIZAR</button>
        </div>

        <div id="sec-revelacion" class="hidden">
            <h2 style="color: #ff4b2b;">FINAL</h2>
            <p id="info-revelacion"></p>
        </div>
    </div>

    <button class="btn-exit" onclick="location.reload()">✖ Salir</button>

    <script>
        const socket = io();
        const isAdmin = new URLSearchParams(window.location.search).get('admin') === 'true';
        let estadoActual = "registro";

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function unirse() {
            const n = document.getElementById('nombre').value;
            if(n) socket.emit('unirse_jugador', {nombre: n, es_admin: isAdmin});
        }

        socket.on('estado', (data) => {
            if(data.encendido && estadoActual === "registro") {
                document.getElementById('sec-off').classList.add('hidden');
                document.getElementById('sec-registro').classList.remove('hidden');
            }
        });

        socket.on('lista_lobby', (data) => {
            if(estadoActual === "registro" || estadoActual === "lobby") {
                estadoActual = "lobby";
                document.getElementById('sec-registro').classList.add('hidden');
                document.getElementById('sec-revelacion').classList.add('hidden');
                document.getElementById('sec-lobby').classList.remove('hidden');
                document.getElementById('lista').innerHTML = data.jugadores.map(j => '• ' + j).join('<br>');
                if(data.soy_admin) document.getElementById('btn-iniciar').classList.remove('hidden');
            }
        });

        socket.on('repartir_roles', (data) => {
            estadoActual = "juego";
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
            estadoActual = "revelacion";
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-revelacion').classList.remove('hidden');
            document.getElementById('info-revelacion').innerHTML = "Impostor: <b>" + data.nombre_impostor + "</b><br>Palabra: " + data.palabra;
            
            setTimeout(() => {
                estadoActual = "lobby";
                document.getElementById('sec-revelacion').classList.add('hidden');
                socket.emit('pedir_lista');
            }, 5000);
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
    actualizar()

@socketio.on('pedir_lista')
def pedir_lista():
    actualizar()

def actualizar():
    nombres = list(game["jugadores"].values())
    for sid, nombre in game["jugadores"].items():
        socketio.emit('lista_lobby', {'jugadores': nombres, 'soy_admin': (sid == game["admin_sid"])}, room=sid)

@socketio.on('dar_inicio')
def inicio():
    if request.sid != game["admin_sid"] or len(game["jugadores"]) < 2: return
    game["en_partida"] = True
    sids = list(game["jugadores"].keys())
    game["impostor_sid"] = random.choice(sids)
    game["palabra"], game["pista"] = random.choice(list(RECURSOS.items()))
    
    socketio.emit('repartir_roles', {
        'impostor_sid': game["impostor_sid"], # Solo para control interno
        'palabra': game["palabra"], 
        'pista': game["pista"]
    }) # Nota: Enviamos a todos, pero el JS filtra quién es quién

    # Re-enviamos específicamente para asegurar roles
    for sid in sids:
        rol = 'impostor' if sid == game["impostor_sid"] else 'civil'
        socketio.emit('repartir_roles', {'rol': rol, 'palabra': game["palabra"], 'pista': game["pista"]}, room=sid)

@socketio.on('finalizar_partida')
def finalizar():
    if request.sid != game["admin_sid"]: return
    nombre_imp = game["jugadores"].get(game["impostor_sid"], "Desconocido")
    socketio.emit('revelar_final', {'nombre_impostor': nombre_imp, 'palabra': game["palabra"]})
    game["en_partida"] = False

@socketio.on('disconnect')
def disconnect():
    if request.sid in game["jugadores"]:
        del game["jugadores"][request.sid]
        if not game["en_partida"]:
            actualizar()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)
