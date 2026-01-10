import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_segura_123"
# Aumentamos el tiempo de espera para que no desconecte a gente en WhatsApp
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25)

game = {
    "admin_sid": None,
    "jugadores": {}, # Diccionario: {nombre: sid}
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
    <title>Impostor PRO</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; padding: 20px; margin: 0; }
        .box { background: #1c1f33; padding: 20px; border-radius: 15px; max-width: 320px; margin: 40px auto; border: 1px solid #333; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 12px; border-radius: 5px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .btn-exit { position: fixed; bottom: 20px; left: 20px; background: #444; color: white; border: none; padding: 8px 15px; border-radius: 20px; font-size: 13px; }
        .hidden { display: none; }
        #lista { text-align: left; background: #2a2e45; padding: 10px; border-radius: 5px; margin: 15px 0; max-height: 200px; overflow-y: auto; }
        input { width: 85%; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: none; background: #2a2e45; color: white; }
        .status-dot { height: 10px; width: 10px; background-color: #00ff88; border-radius: 50%; display: inline-block; margin-right: 5px; }
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
            <h3>Jugadores (<span id="count">0</span>)</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:black;" onclick="socket.emit('dar_inicio')">INICIAR PARTIDA</button>
            <p style="font-size:10px; color: #666;">Si no ves a alguien, que recargue la página.</p>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado" style="font-size: 20px; margin: 20px 0; font-weight: bold;"></div>
            <p id="pista-imp" style="color: #aaa; font-style: italic;"></p>
            <button id="btn-finalizar" class="btn hidden" style="background:#ffcc00; color:black;" onclick="socket.emit('finalizar_partida')">FINALIZAR Y REVELAR</button>
        </div>

        <div id="sec-revelacion" class="hidden">
            <h2 style="color: #ff4b2b;">PARTIDA FINALIZADA</h2>
            <p id="info-revelacion"></p>
        </div>
    </div>

    <button class="btn-exit" onclick="salir()">✖ Salir del Juego</button>

    <script>
        const socket = io({ reconnection: true, reconnectionAttempts: 5 });
        const isAdmin = new URLSearchParams(window.location.search).get('admin') === 'true';
        let miNombre = "";
        let estadoActual = "registro";

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function unirse() {
            miNombre = document.getElementById('nombre').value;
            if(miNombre) socket.emit('unirse_jugador', {nombre: miNombre, es_admin: isAdmin});
        }

        function salir() {
            if(miNombre) socket.emit('quitar_jugador', {nombre: miNombre});
            location.reload();
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
                document.getElementById('lista').innerHTML = data.jugadores.map(j => '<div><span class="status-dot"></span>' + j + '</div>').join('');
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
                res.innerHTML = 'Tu Palabra es:<br><span style="color:#00ff88; font-size:30px;">' + data.palabra + '</span>';
                pst.innerHTML = "";
            }
            if(isAdmin) document.getElementById('btn-finalizar').classList.remove('hidden');
        });

        socket.on('revelar_final', (data) => {
            estadoActual = "revelacion";
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-revelacion').classList.remove('hidden');
            document.getElementById('info-revelacion').innerHTML = "El Impostor era: <br><b style='font-size:24px; color:#ff4b2b;'>" + data.nombre_impostor + "</b><br><br>Palabra: " + data.palabra;
            
            setTimeout(() => {
                estadoActual = "lobby";
                document.getElementById('sec-revelacion').classList.add('hidden');
                socket.emit('pedir_lista');
            }, 8000); // 8 segundos para que todos lean bien
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
    # Guardamos por NOMBRE, no por ID, para que si cambian de app no se borren
    game["jugadores"][data['nombre']] = request.sid
    if data.get('es_admin'): game["admin_sid"] = request.sid
    actualizar()

@socketio.on('quitar_jugador')
def quitar(data):
    if data['nombre'] in game["jugadores"]:
        del game["jugadores"][data['nombre']]
    actualizar()

@socketio.on('pedir_lista')
def pedir_lista():
    actualizar()

def actualizar():
    nombres = list(game["jugadores"].keys())
    socketio.emit('lista_lobby', {
        'jugadores': nombres, 
        'soy_admin': False # El cliente chequeará esto por URL
    })

@socketio.on('dar_inicio')
def inicio():
    if len(game["jugadores"]) < 2: return
    game["en_partida"] = True
    nombres = list(game["jugadores"].keys())
    nombre_impostor = random.choice(nombres)
    game["palabra"], game["pista"] = random.choice(list(RECURSOS.items()))
    
    # Guardamos quién es para la revelación final
    game["impostor_sid"] = nombre_impostor 

    for nombre, sid in game["jugadores"].items():
        rol = 'impostor' if nombre == nombre_impostor else 'civil'
        socketio.emit('repartir_roles', {
            'rol': rol, 
            'palabra': game["palabra"], 
            'pista': game["pista"]
        }, room=sid)

@socketio.on('finalizar_partida')
def finalizar():
    socketio.emit('revelar_final', {
        'nombre_impostor': game["impostor_sid"], 
        'palabra': game["palabra"]
    })
    game["en_partida"] = False

# IMPORTANTE: Ya no hay función 'disconnect' que borre gente.
# El jugador solo se va si presiona "Salir".

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port)
