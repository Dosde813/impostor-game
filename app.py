import os
import random
from flask import Flask, render_template_string, request, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "clave_super_secreta_123"

# Configuración para que funcione en la nube (Render)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- ESTADO DEL JUEGO ---
game = {
    "admin_sid": None,
    "jugadores": {},  # {sid: nombre}
    "impostor_sid": None,
    "palabra": "",
    "estado": "lobby"
}

PALABRAS = ["Pizza", "Dinosaurio", "Internet", "Marte", "Cine", "YouTube", "WhatsApp", "Venezuela", "Avión", "Fútbol"]

HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impostor Online</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0d17; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .box { background: #1c1f33; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 90%; max-width: 350px; text-align: center; border: 2px solid #30344d; }
        h1 { color: #ff4b2b; letter-spacing: 2px; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 8px; width: 100%; font-size: 18px; cursor: pointer; margin-top: 15px; font-weight: bold; }
        .hidden { display: none; }
        #lista-jugadores { background: #2a2e45; padding: 15px; border-radius: 10px; text-align: left; margin: 15px 0; border: 1px solid #3d4261; }
        .rol-impostor { color: #ff4b2b; font-size: 28px; font-weight: bold; text-shadow: 0 0 10px rgba(255,75,43,0.5); }
        .rol-palabra { color: #00ff88; font-size: 28px; font-weight: bold; text-shadow: 0 0 10px rgba(0,255,136,0.5); }
        input { width: 90%; padding: 12px; border-radius: 8px; border: none; margin-bottom: 10px; background: #2a2e45; color: white; font-size: 16px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>IMPOSTOR</h1>
        
        <div id="sec-registro">
            <input type="text" id="nombre" placeholder="Tu Apodo..." autocomplete="off">
            <button class="btn" onclick="unirse()">ENTRAR</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Sala de Espera</h3>
            <div id="lista-jugadores"></div>
            <p id="msg-espera">Esperando al anfitrión...</p>
            <button id="btn-iniciar" class="btn hidden" onclick="iniciarJuego()">INICIAR PARTIDA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="resultado"></div>
            <button class="btn" style="background:#444" onclick="volverAlLobby()">NUEVA PARTIDA</button>
        </div>
    </div>

    <script>
        const socket = io();

        function unirse() {
            const nom = document.getElementById('nombre').value;
            if(nom) {
                socket.emit('unirse', {nombre: nom});
                document.getElementById('sec-registro').classList.add('hidden');
                document.getElementById('sec-lobby').classList.remove('hidden');
            }
        }

        function iniciarJuego() {
            socket.emit('iniciar_juego');
        }

        function volverAlLobby() {
            socket.emit('reset');
        }

        socket.on('actualizar_lobby', (data) => {
            const lista = document.getElementById('lista-jugadores');
            lista.innerHTML = data.jugadores.map(n => `• ${n}`).join('<br>');
            
            if(data.es_admin) {
                document.getElementById('btn-iniciar').classList.remove('hidden');
                document.getElementById('msg-espera').classList.add('hidden');
            }
        });

        socket.on('comenzar', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('resultado');
            
            if(data.rol === 'impostor') {
                res.innerHTML = '<p>Tu rol es:</p><div class="rol-impostor">¡IMPOSTOR!</div><p>No conoces la palabra. ¡Miente!</p>';
            } else {
                res.innerHTML = `<p>La palabra es:</p><div class="rol-palabra">${data.palabra}</div><p>Encuentra al impostor.</p>`;
            }
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

@socketio.on('unirse')
def handle_unirse(data):
    sid = request.sid
    game["jugadores"][sid] = data['nombre']
    
    # El primero que entra es el administrador
    if not game["admin_sid"] or game["admin_sid"] not in game["jugadores"]:
        game["admin_sid"] = sid
    
    # Avisar a todos para actualizar la lista de nombres
    enviar_lobby_actualizado()

def enviar_lobby_actualizado():
    lista_nombres = list(game["jugadores"].values())
    for sid in game["jugadores"]:
        socketio.emit('actualizar_lobby', {
            'jugadores': lista_nombres,
            'es_admin': (sid == game["admin_sid"])
        }, room=sid)

@socketio.on('iniciar_juego')
def handle_iniciar():
    if request.sid != game["admin_sid"]:
        return
    
    sids = list(game["jugadores"].keys())
    if len(sids) < 2:
        return

    game["impostor_sid"] = random.choice(sids)
    game["palabra"] = random.choice(PALABRAS)
    game["estado"] = "jugando"
    
    for sid in sids:
        rol = 'impostor' if sid == game["impostor_sid"] else 'civil'
        socketio.emit('comenzar', {'rol': rol, 'palabra': game["palabra"]}, room=sid)

@socketio.on('reset')
def handle_reset():
    game["estado"] = "lobby"
    socketio.emit('ir_al_lobby')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in game["jugadores"]:
        del game["jugadores"][sid]
        if sid == game["admin_sid"] and game["jugadores"]:
            game["admin_sid"] = list(game["jugadores"].keys())[0]
        enviar_lobby_actualizado()

if __name__ == '__main__':
    # Render asigna el puerto automáticamente mediante la variable de entorno PORT
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)