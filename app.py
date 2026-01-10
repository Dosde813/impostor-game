import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_v10_final"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

game = {
    "encendido": False,
    "jugadores": {},  # sid: nombre
    "roles_asignados": {}, # nombre: {rol, palabra, pista}
    "estado": "lobby",
    "impostor_sid": None,
    "palabra": "",
    "pista": ""
}

RECURSOS = {
    "Arepa": "Se come en el desayuno o cena", "Hallaca": "Navidad y lleva pabilo",
    "Cerveza": "Bien fría con mucho hielo", "Malta": "Bebida negra dulce",
    "Tequeño": "El rey de las fiestas", "Empanada": "Fritura con salsa de ajo",
    "Metro": "Transporte que siempre va full", "Béisbol": "Deporte con bates",
    "Plátano": "Si está frito es tajada", "Chamo": "Un joven amigo",
    "Sifrino": "Habla con la papa en la boca", "Moto": "Esquiva el tráfico"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor V10</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; margin: 0; padding: 15px; }
        .box { background: #1c1f33; padding: 20px; border-radius: 20px; max-width: 320px; margin: 10px auto; border: 1px solid #444; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 10px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; font-size: 16px; }
        .hidden { display: none !important; }
        #lista { text-align: left; background: #0b0d17; padding: 10px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        input { width: 88%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #444; background: #2a2e45; color: white; }
        .modal { background: rgba(0,0,0,0.95); position: fixed; top:0; left:0; width:100%; height:100%; display:flex; align-items:center; justify-content:center; z-index:9999; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="color:#ff4b2b;">IMPOSTOR</h2>
        
        <div id="sec-off"><p style="color:#ffcc00; font-weight:bold;">SALA CERRADA</p></div>
        
        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:#000;" onclick="socket.emit('activar')">ENCENDER SERVIDOR</button>
            <button class="btn" style="background:#444; font-size:12px;" onclick="socket.emit('cerrar_total')">CERRAR SALA</button>
        </div>

        <div id="sec-bloqueo" class="hidden">
            <p style="color:#ff4b2b; font-weight:bold;">PARTIDA EN CURSO</p>
            <p>Espera a que termine la ronda para poder unirte.</p>
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="¿Tu nombre?">
            <button class="btn" onclick="unirse()">ENTRAR</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:#000;" onclick="socket.emit('iniciar')">¡INICIAR PARTIDA!</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-text" style="font-size:22px; font-weight:bold; margin:20px 0;"></div>
            <p id="pista-text" style="color:#aaa;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#ffcc00; color:#000;" onclick="socket.emit('finalizar')">REVELAR IMPOSTOR</button>
        </div>
    </div>

    <div id="modal-reveal" class="modal hidden">
        <div class="box">
            <h3 style="color:#ff4b2b;">RESULTADOS</h3>
            <p id="reveal-msg"></p>
            <button class="btn" onclick="cerrarModal()">VOLVER AL LOBBY</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        let miNombre = localStorage.getItem('impostor_name_v10') || "";

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function unirse() {
            const n = document.getElementById('nombre').value.trim();
            if(n) {
                miNombre = n;
                localStorage.setItem('impostor_name_v10', n);
                socket.emit('unirse', {nombre: n});
            }
        }

        function cerrarModal() {
            document.getElementById('modal-reveal').classList.add('hidden');
        }

        socket.on('estado_servidor', (data) => {
            document.getElementById('sec-off').classList.add('hidden');
            document.getElementById('sec-bloqueo').classList.add('hidden');
            document.getElementById('sec-reg').classList.add('hidden');

            if(!data.encendido) {
                document.getElementById('sec-off').classList.remove('hidden');
                return;
            }

            if(data.estado === "juego" && !miNombre) {
                document.getElementById('sec-bloqueo').classList.remove('hidden');
            } else if(!miNombre) {
                document.getElementById('sec-reg').classList.remove('hidden');
            } else {
                socket.emit('unirse', {nombre: miNombre});
            }
        });

        socket.on('pantalla_lobby', (data) => {
            if(!miNombre) return;
            document.getElementById('sec-reg').classList.add('hidden');
            document.getElementById('sec-juego').classList.add('hidden');
            document.getElementById('sec-bloqueo').classList.add('hidden');
            document.getElementById('sec-lobby').classList.remove('hidden');
            document.getElementById('lista').innerHTML = data.jugadores.map(j => '• ' + j).join('<br>');
            if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
        });

        socket.on('ver_rol', (data) => {
            if(!miNombre) return;
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('rol-text');
            const pst = document.getElementById('pista-text');
            if(data.rol === 'impostor') {
                res.innerHTML = '<span style="color:#ff4b2b">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "Pista: " + data.pista;
            } else {
                res.innerHTML = 'Palabra: <br><span style="color:#00ff88">' + data.palabra + '</span>';
                pst.innerHTML = "¡No te descubras!";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        socket.on('reset', (data) => {
            document.getElementById('reveal-msg').innerHTML = "Impostor: <b>"+data.nombre+"</b><br>Palabra: <b>"+data.palabra+"</b>";
            document.getElementById('modal-reveal').classList.remove('hidden');
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_INDEX)

@socketio.on('connect')
def on_connect():
    emit('estado_servidor', {'encendido': game['encendido'], 'estado': game['estado']})

@socketio.on('activar')
def on_activar():
    game['encendido'] = True
    socketio.emit('estado_servidor', {'encendido': True, 'estado': game['estado']})

@socketio.on('unirse')
def on_unirse(data):
    nombre = data['nombre']
    # Evitar duplicados por nombre
    for sid, n in list(game['jugadores'].items()):
        if n == nombre: del game['jugadores'][sid]
    
    game['jugadores'][request.sid] = nombre
    
    if game['estado'] == "lobby":
        socketio.emit('pantalla_lobby', {'jugadores': list(set(game['jugadores'].values()))})
    else:
        # Si ya hay partida, le devolvemos su rol si estaba en ella
        if nombre in game['roles_asignados']:
            info = game['roles_asignados'][nombre]
            emit('ver_rol', info)
        else:
            emit('estado_servidor', {'encendido': True, 'estado': "juego"})

@socketio.on('iniciar')
def on_iniciar():
    sids = list(game['jugadores'].items())
    if len(sids) < 2: return
    game['estado'] = "juego"
    game['roles_asignados'] = {}
    
    impostor_sid, impostor_nombre = random.choice(sids)
    game['palabra'], game['pista'] = random.choice(list(RECURSOS.items()))
    
    for sid, nombre in sids:
        rol = 'impostor' if sid == impostor_sid else 'civil'
        info = {'rol': rol, 'palabra': game['palabra'], 'pista': game['pista']}
        game['roles_asignados'][nombre] = info
        socketio.emit('ver_rol', info, room=sid)

@socketio.on('finalizar')
def on_finalizar():
    impostor_nombre = ""
    for n, info in game['roles_asignados'].items():
        if info['rol'] == 'impostor': impostor_nombre = n
    
    socketio.emit('reset', {'nombre': impostor_nombre, 'palabra': game['palabra']})
    game['estado'] = "lobby"
    game['roles_asignados'] = {}
    socketio.emit('pantalla_lobby', {'jugadores': list(set(game['jugadores'].values()))})

@socketio.on('cerrar_total')
def cerrar_total():
    game.update({"encendido": False, "jugadores": {}, "estado": "lobby", "roles_asignados": {}})
    socketio.emit('estado_servidor', {'encendido': False, 'estado': "lobby"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
