import eventlet
eventlet.monkey_patch()

import os
import random
import time
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_segura_123"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Base de datos del juego
game = {
    "admin_sid": None,
    "jugadores": {}, 
    "impostor_sid": None,
    "palabra": "",
    "pista": "",
    "encendido": False 
}

# Diccionario de palabras con sus pistas para el impostor
RECURSOS = {
    "Arepa": "Comida típica hecha de maíz",
    "Sifrino": "Persona que cree tener mucho dinero o clase",
    "Chamo": "Palabra para referirse a un joven",
    "Monitor": "Parte de la computadora que muestra imagen",
    "Teclado": "Se usa para escribir en la computadora",
    "Cerveza": "Bebida alcohólica con espuma",
    "Plátano": "Fruta amarilla que se fríe o se sancochos",
    "Metro": "Transporte público subterráneo",
    "Hallaca": "Comida típica de diciembre",
    "Papelón": "Bebida dulce hecha de caña"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>¿Quién es el Impostor?</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; padding: 20px; margin: 0; min-height: 100vh; }
        .box { background: #1c1f33; padding: 20px; border-radius: 15px; max-width: 320px; margin: 40px auto; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .btn { background: #ff4b2b; color: white; border: none; padding: 12px; border-radius: 5px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .btn-exit { position: fixed; bottom: 20px; left: 20px; background: rgba(255, 255, 255, 0.1); color: #aaa; border: 1px solid #444; padding: 8px 15px; border-radius: 20px; font-size: 13px; cursor: pointer; }
        .hidden { display: none; }
        #lista { text-align: left; background: #2a2e45; padding: 10px; border-radius: 5px; margin: 15px 0; line-height: 1.6; }
        input { width: 85%; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: none; background: #2a2e45; color: white; }
        .pista { font-size: 14px; color: #aaa; margin-top: 10px; font-style: italic; }
    </style>
</head>
<body>
    <div class="box">
        <h1>IMPOSTOR</h1>
        
        <div id="sec-off">
            <p style="color: #ffcc00; font-weight: bold;">SALA CERRADA</p>
            <p>Esperando al jefe...</p>
        </div>

        <div id="sec-admin" class="hidden">
            <p style="color: #00ff88;">🔓 MODO JEFE</p>
            <button class="btn" style="background:#00ff88; color:black;" onclick="socket.emit('activar_servidor')">ENCENDER APP</button>
            <hr style="border: 0.1px solid #333; margin: 15px 0;">
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Tu Apodo..." autocomplete="off">
            <button class="btn" onclick="unirse()">ENTRAR</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Jugadores conectados:</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:black;" onclick="socket.emit('dar_inicio')">INICIAR PARTIDA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="font-size: 20px; margin: 20px 0;"></div>
            <div id="pista-impostor" class="pista"></div>
            <button id="btn-finalizar" class="btn hidden" style="background:#ffcc00; color:black;" onclick="socket.emit('finalizar_partida')">FINALIZAR Y REVELAR</button>
        </div>

        <div id="sec-revelacion" class="hidden">
            <h2 style="color: #ff4b2b;">PARTIDA FINALIZADA</h2>
            <p id="info-revelacion"></p>
            <p style="font-size: 12px; color: #888;">Volviendo al lobby en 5 segundos...</p>
        </div>
    </div>

    <button class="btn-exit" onclick="location.reload()">✖ Salir</button>

    <script>
        const socket = io();
        const isAdmin = new URLSearchParams(window.location.search).get('admin') === 'true';
        let miNombre = "";

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function unirse() {
            miNombre = document.getElementById('nombre').value;
            if(miNombre) socket.emit('unirse_jugador', {nombre: miNombre, es_admin: isAdmin});
        }

        socket.on('estado', (data) => {
            if(data.encendido) {
                document.getElementById('sec-off').classList.add('hidden');
                if(document.getElementById('sec-lobby').classList.contains('hidden') && 
                   document.getElementById('sec-juego').classList.contains('hidden') &&
                   document.getElementById('sec-revelacion').classList.contains('hidden')) {
                    document.getElementById('sec-registro').classList.remove('hidden');
                }
            }
        });

        socket.on('lista_lobby', (data) => {
            document.getElementById('sec-registro').classList.add('hidden');
            document.getElementById('sec-revelacion').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
            document.getElementById('lista').innerHTML = data.jugadores.map(j => '• ' + j).join('<br>');
            if(data.soy_admin) document.getElementById('btn-iniciar').classList.remove('hidden');
        });

        socket.on('repartir_roles', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('resultado');
            const pst = document.getElementById('pista-impostor');
            
            if(data.rol === 'impostor') {
                res.innerHTML = '<span style="color:red">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "Pista de la palabra: " + data.pista;
            } else {
                res.innerHTML = 'Palabra: <br><span style="color:#00ff88">' + data.palabra + '</span>';
                pst.innerHTML = "";
            }
            if(isAdmin) document.getElementById('btn-finalizar').classList.remove('hidden');
        });

        socket.on('revelar_final', (data) => {
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-revelacion').classList.remove('hidden');
            document.getElementById('info-revelacion').innerHTML = "El Impostor era: <br><b style='font-size:24px; color:#ff4b2b;'>" + data.nombre_impostor + "</b><br><br>Palabra: " + data.palabra;
        });

        socket.on('volver_lobby_auto', () => {
            setTimeout(() => {
                document.getElementById('sec-revelacion').classList.add('hidden');
                socket.emit('pedir_lista'); // Forzar actualización de lista
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
    if not game["encendido"]: return
    game["jugadores"][request.sid] = data['nombre']
    if data.get('es_admin'): game["admin_sid"] = request.sid
    actualizar()

@socketio.on('pedir_lista')
def pedir_lista():
    actualizar()

def actualizar():
    nombres = list(game["jugadores"].values())
    for sid in game["jugadores"]:
        socketio.emit('lista_lobby', {'jugadores': nombres, 'soy_admin': (sid == game["admin_sid"])}, room=sid)

@socketio.on('dar_inicio')
def inicio():
    if request.sid != game["admin_sid"] or len(game["jugadores"]) < 2: return
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
    if request.sid != game["admin_sid"]: return
    nombre_imp = game["jugadores"].get(game["impostor_sid"], "Desconocido")
    socketio.emit('revelar_final', {
        'nombre_impostor': nombre_imp,
        'palabra': game["palabra"]
    })
    socketio.emit('volver_lobby_auto')

# Eliminamos la limpieza automática al desconectarse para evitar que se borren por error
# Solo se borran si el usuario cierra o el servidor se reinicia manualmente

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)
