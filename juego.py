from flask import Flask, render_template_string, request, session
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
app.secret_key = "clave_secreta_pro"
socketio = SocketIO(app, cors_allowed_origins="*")

# --- ESTADO DEL JUEGO ---
game = {
    "admin_id": None,
    "jugadores": {},  # {sid: nombre}
    "impostor_id": None,
    "palabra": "",
    "estado": "lobby"
}

PALABRAS = ["Pizza", "Dinosaurio", "Internet", "Marte", "Cine", "YouTube", "WhatsApp", "Venezuela"]

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <title>Impostor Realtime</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Arial', sans-serif; background: #121212; color: white; text-align: center; margin: 0; padding: 20px; }
        .box { background: #1e1e1e; padding: 20px; border-radius: 15px; max-width: 400px; margin: auto; border: 2px solid #333; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 8px; width: 100%; font-size: 18px; cursor: pointer; margin-top: 10px; }
        .hidden { display: none; }
        #lista-jugadores { background: #252525; padding: 10px; border-radius: 8px; text-align: left; }
        .rol-impostor { color: #ff4b2b; font-size: 30px; font-weight: bold; }
        .rol-palabra { color: #00ff88; font-size: 30px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="box">
        <h1>IMPOSTOR 🕵️</h1>
        
        <div id="sec-registro">
            <input type="text" id="nombre" placeholder="Tu nombre..." style="width:90%; padding:10px; margin-bottom:10px; border-radius:5px;">
            <button class="btn" onclick="unirse()">Unirse al Lobby</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>Sala de Espera</h3>
            <div id="lista-jugadores"></div>
            <p id="msg-espera">Esperando al anfitrión...</p>
            <button id="btn-iniciar" class="btn hidden" onclick="iniciarJuego()">INICIAR PARTIDA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <p>Tu rol es:</p>
            <div id="resultado"></div>
            <button class="btn" style="background:#444" onclick="volverAlLobby()">Volver al Lobby</button>
        </div>
    </div>

    <script>
        const socket = io();
        let miNombre = "";

        function unirse() {
            miNombre = document.getElementById('nombre').value;
            if(miNombre) {
                socket.emit('unirse', {nombre: miNombre});
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

        // ESCUCHAR EVENTOS DEL SERVIDOR
        socket.on('actualizar_lobby', (data) => {
            const lista = document.getElementById('lista-jugadores');
            lista.innerHTML = data.jugadores.map(n => `• ${n}`).join('<br>');
            
            // Si soy el primero (admin), veo el botón
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
                res.innerHTML = '<span class="rol-impostor">¡ERES EL IMPOSTOR!</span><br><p>No sabes la palabra. ¡Miente!</p>';
            } else {
                res.innerHTML = `<p>La palabra es:</p><span class="rol-palabra">${data.palabra}</span>`;
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
    if game["admin_id"] is None:
        game["admin_id"] = sid
    
    emit('actualizar_lobby', {
        'jugadores': list(game["jugadores"].values()),
        'es_admin': (sid == game["admin_id"])
    })
    # Avisar a todos que alguien se unió
    socketio.emit('actualizar_lobby', {'jugadores': list(game["jugadores"].values()), 'es_admin': False}, include_self=False)

@socketio.on('iniciar_juego')
def handle_iniciar():
    if request.sid != game["admin_id"]: return
    
    sids = list(game["jugadores"].keys())
    game["impostor_id"] = random.choice(sids)
    game["palabra"] = random.choice(PALABRAS)
    
    for sid in sids:
        rol = 'impostor' if sid == game["impostor_id"] else 'civil'
        socketio.emit('comenzar', {'rol': rol, 'palabra': game["palabra"]}, room=sid)

@socketio.on('reset')
def handle_reset():
    socketio.emit('ir_al_lobby')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)