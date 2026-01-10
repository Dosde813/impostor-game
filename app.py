import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_maestra_impostor"
# Configuración de alta disponibilidad para móviles
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=120, ping_interval=25)

game = {
    "admin_sid": None,
    "jugadores": {}, # Almacena {sid: nombre}
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
    "Papelón": "Bebida de caña", "Béisbol": "Deporte con bate", "Café": "Bebida negra caliente"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor PRO</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0d17; color: white; text-align: center; margin: 0; padding: 10px; overflow-x: hidden; }
        .box { background: #1c1f33; padding: 20px; border-radius: 20px; max-width: 350px; margin: 20px auto; border: 1px solid #444; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 10px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; font-size: 16px; }
        .btn-admin { background: #00ff88; color: #000; }
        .btn-exit { position: fixed; bottom: 15px; left: 15px; background: #333; color: #eee; border: none; padding: 10px 20px; border-radius: 30px; font-size: 12px; z-index: 1000; }
        #lista { text-align: left; background: #0b0d17; padding: 15px; border-radius: 10px; margin: 15px 0; max-height: 250px; overflow-y: auto; border: 1px solid #333; }
        .jugador-item { padding: 8px; border-bottom: 1px solid #222; display: flex; align-items: center; }
        .dot { height: 8px; width: 8px; background: #00ff88; border-radius: 50%; margin-right: 10px; }
        input { width: 90%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #444; background: #0b0d17; color: white; font-size: 16px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="box">
        <h1 style="letter-spacing: 2px; color: #ff4b2b;">IMPOSTOR</h1>
        
        <div id="sec-off">
            <p style="color: #ffcc00; font-weight: bold;">SALA CERRADA</p>
            <p style="font-size: 14px;">El anfitrión debe activar el juego.</p>
        </div>

        <div id="sec-admin" class="hidden">
            <p style="color: #00ff88; font-size: 12px;">MODO ANFITRIÓN ACTIVO</p>
            <button class="btn btn-admin" onclick="socket.emit('activar_servidor')">ENCENDER SERVIDOR</button>
            <hr style="border: 0.5px solid #333; margin: 15px 0;">
        </div>

        <div id="sec-registro" class="hidden">
            <input type="text" id="nombre" placeholder="Escribe tu apodo..." autocomplete="off">
            <button class="btn" onclick="unirse()">ENTRAR AL LOBBY</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3 style="margin-bottom: 5px;">Jugadores (<span id="count">0</span>)</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn btn-admin hidden" onclick="socket.emit('dar_inicio')">¡INICIAR PARTIDA!</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="margin: 20px 0;"></div>
            <p id="pista-imp" style="color: #aaa; font-style: italic; font-size: 14px;"></p>
            <button id="btn-finalizar" class="btn hidden" style="background:#ffcc00; color:#000;" onclick="socket.emit('finalizar_partida')">REVELAR IMPOSTOR</button>
        </div>

        <div id="sec-revelacion" class="hidden">
            <h2 style="color: #ff4b2b;">RESULTADOS</h2>
            <div id="info-revelacion" style="background: #0b0d17; padding: 20px; border-radius: 10px;"></div>
            <p style="font-size: 11px; margin-top: 15px; color: #666;">Preparando siguiente ronda...</p>
        </div>
    </div>

    <button class="btn-exit" onclick="location.reload()">✖ SALIR</button>

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
                document.getElementById('count').innerText = data.jugadores.length;
                document.getElementById('lista').innerHTML = data.jugadores.map(j => 
                    `<div class="jugador-item"><div class="dot"></div>\${j}</div>`).join('');
                
                if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
            }
        });

        socket.on('repartir_roles', (data) => {
            estadoActual = "juego";
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            
            const res = document.getElementById('resultado');
            const pst = document.getElementById('pista-imp');
            
            if(data.rol === 'impostor') {
                res.innerHTML = '<h2 style="color:red; margin:0;">ERES EL IMPOSTOR</h2>';
                pst.innerHTML = "Tu pista: <b>" + data.pista + "</b>";
            } else {
                res.innerHTML = 'Tu palabra es:<br><b style="color:#00ff88; font-size:35px;">' + data.palabra + '</b>';
                pst.innerHTML = "¡No dejes que el impostor la descubra!";
            }
            if(isAdmin) document.getElementById('btn-finalizar').classList.remove('hidden');
        });

        socket.on('revelar_final', (data) => {
            estadoActual = "revelacion";
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-revelacion').classList.remove('hidden');
            document.getElementById('info-revelacion').innerHTML = 
                `<p>El impostor era:</p><h1 style="color:#ff4b2b;">\${data.nombre_impostor}</h1><p>La palabra secreta:</p><h2 style="color:#00ff88;">\${data.palabra}</h2>`;
            
            setTimeout(() => {
                estadoActual = "lobby";
                document.getElementById('sec-revelacion').classList.add('hidden');
                socket.emit('pedir_lista');
            }, 8000);
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
    socketio.emit('estado', {"encendido": True}, broadcast=True)

@socketio.on('unirse_jugador')
def unirse(data):
    game["jugadores"][request.sid] = data['nombre']
    if data.get('es_admin'): game["admin_sid"] = request.sid
    actualizar_todos()

@socketio.on('pedir_lista')
def pedir_lista():
    actualizar_todos()

def actualizar_todos():
    nombres = list(game["jugadores"].values())
    socketio.emit('lista_lobby', {'jugadores': nombres}, broadcast=True)

@socketio.on('dar_inicio')
def inicio():
    if len(game["jugadores"]) < 2: return
    game["en_partida"] = True
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
    }, broadcast=True)
    game["en_partida"] = False

@socketio.on('disconnect')
def disconnect():
    if request.sid in game["jugadores"]:
        del game["jugadores"][request.sid]
        if not game["en_partida"]:
            actualizar_todos()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)
