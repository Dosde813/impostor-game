import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_v6_pro"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

game = {
    "encendido": False,
    "jugadores": {},  # sid: nombre
    "impostor_sid": None,
    "palabra": "",
    "pista": ""
}

RECURSOS = {
    "Arepa": "Se come en el desayuno o cena", "Hallaca": "Huele a navidad y lleva pabilo",
    "Cerveza": "Bien fría en una cava con hielo", "Malta": "Bebida negra dulce muy nuestra",
    "Tequeño": "El rey de todas las fiestas", "Empanada": "Se compra en la calle con salsa de ajo",
    "Metro": "Transporte que siempre va full", "Béisbol": "Deporte que paraliza al país",
    "Plátano": "Si está frito es tajada", "Chamo": "Persona joven o amigo",
    "Sifrino": "Alguien que habla con la papa en la boca", "Moto": "Esquiva el tráfico"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Impostor V6</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; margin: 0; padding: 15px; }
        .box { background: #1c1f33; padding: 20px; border-radius: 20px; max-width: 320px; margin: 10px auto; border: 1px solid #444; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 10px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; font-size: 16px; }
        .btn-sec { background: #555; font-size: 12px; padding: 8px; }
        .hidden { display: none; }
        #lista { text-align: left; background: #0b0d17; padding: 10px; border-radius: 10px; margin: 10px 0; border: 1px solid #333; }
        input { width: 88%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #444; background: #2a2e45; color: white; }
        .modal { background: rgba(0,0,0,0.9); position: fixed; top:0; left:0; width:100%; height:100%; display:flex; align-items:center; justify-content:center; z-index:1000; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="color:#ff4b2b; margin-top:0;">IMPOSTOR</h2>
        
        <div id="sec-off">
            <p style="color:#ffcc00; font-weight:bold;">SALA CERRADA</p>
            <p style="font-size:12px;">Espera a que el anfitrión abra la sala.</p>
        </div>
        
        <div id="sec-admin" class="hidden">
            <button id="btn-on" class="btn" style="background:#00ff88; color:#000;" onclick="socket.emit('activar')">ENCENDER SERVIDOR</button>
            <button id="btn-kill" class="btn btn-sec hidden" onclick="socket.emit('cerrar_total')">CERRAR SALA POR COMPLETO</button>
            <hr style="border:0.1px solid #333; margin:15px 0;">
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="¿Tu nombre?">
            <button class="btn" onclick="unirse()">ENTRAR AL LOBBY</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <p style="color:#00ff88; font-size:12px;">✓ Conectado</p>
            <div id="lista"></div>
            <p id="wait-msg" style="font-size:14px; color:#aaa;">Esperando inicio...</p>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:#000;" onclick="socket.emit('iniciar')">¡INICIAR PARTIDA!</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-text" style="font-size:22px; font-weight:bold; margin:20px 0;"></div>
            <p id="pista-text" style="color:#aaa; font-style:italic;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#ffcc00; color:#000;" onclick="socket.emit('finalizar')">REVELAR IMPOSTOR</button>
        </div>
    </div>

    <div id="modal-reveal" class="modal hidden">
        <div class="box" style="border:2px solid #ff4b2b;">
            <h3 style="color:#ff4b2b;">RESULTADOS</h3>
            <p id="reveal-msg"></p>
            <button class="btn" onclick="cerrarModal()">VOLVER AL LOBBY</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        let miNombre = "";

        if(isAdmin) {
            document.getElementById('sec-admin').classList.remove('hidden');
            document.getElementById('btn-kill').classList.remove('hidden');
        }

        function unirse() {
            miNombre = document.getElementById('nombre').value;
            if(miNombre) socket.emit('unirse', {nombre: miNombre});
        }

        function cerrarModal() {
            document.getElementById('modal-reveal').classList.add('hidden');
        }

        socket.on('estado_servidor', (data) => {
            if(data.encendido) {
                document.getElementById('sec-off').classList.add('hidden');
                if(!miNombre) {
                    document.getElementById('sec-reg').classList.remove('hidden');
                }
            } else {
                // Expulsión total
                miNombre = "";
                document.getElementById('sec-off').classList.remove('hidden');
                document.getElementById('sec-reg').classList.add('hidden');
                document.getElementById('sec-lobby').classList.add('hidden');
                document.getElementById('sec-juego').classList.add('hidden');
                document.getElementById('modal-reveal').classList.add('hidden');
            }
        });

        socket.on('actualizar_lista', (data) => {
            if(miNombre) {
                document.getElementById('sec-reg').classList.add('hidden');
                document.getElementById('sec-lobby').classList.remove('hidden');
                document.getElementById('sec-juego').classList.add('hidden');
                document.getElementById('lista').innerHTML = data.map(j => '• ' + j).join('<br>');
                if(isAdmin) document.getElementById('btn-iniciar').classList.remove('hidden');
            }
        });

        socket.on('ver_rol', (data) => {
            document.getElementById('sec-lobby').classList.add('hidden');
            document.getElementById('sec-juego').classList.remove('hidden');
            const res = document.getElementById('rol-text');
            const pst = document.getElementById('pista-text');
            if(data.rol === 'impostor') {
                res.innerHTML = '<span style="color:#ff4b2b">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "Tu Pista: " + data.pista;
            } else {
                res.innerHTML = 'Palabra: <br><span style="color:#00ff88">' + data.palabra + '</span>';
                pst.innerHTML = "";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        socket.on('reset', (data) => {
            document.getElementById('reveal-msg').innerHTML = "Impostor: <b>"+data.nombre+"</b><br>Palabra: <b>"+data.palabra+"</b>";
            document.getElementById('modal-reveal').classList.remove('hidden');
            // El servidor enviará actualizar_lista automáticamente después
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
    emit('estado_servidor', {'encendido': game['encendido']})

@socketio.on('activar')
def on_activar():
    game['encendido'] = True
    socketio.emit('estado_servidor', {'encendido': True})

@socketio.on('cerrar_total')
def cerrar_total():
    game['encendido'] = False
    game['jugadores'] = {}
    socketio.emit('estado_servidor', {'encendido': False})

@socketio.on('unirse')
def on_unirse(data):
    game['jugadores'][request.sid] = data['nombre']
    socketio.emit('actualizar_lista', list(game['jugadores'].values()))

@socketio.on('iniciar')
def on_iniciar():
    sids = list(game['jugadores'].keys())
    if len(sids) < 2: return
    game['impostor_sid'] = random.choice(sids)
    game['palabra'], game['pista'] = random.choice(list(RECURSOS.items()))
    for sid in sids:
        rol = 'impostor' if sid == game['impostor_sid'] else 'civil'
        socketio.emit('ver_rol', {'rol': rol, 'palabra': game['palabra'], 'pista': game['pista']}, room=sid)

@socketio.on('finalizar')
def on_finalizar():
    nombre = game['jugadores'].get(game['impostor_sid'], "Desconocido")
    socketio.emit('reset', {'nombre': nombre, 'palabra': game['palabra']})
    # Después de un pequeño delay, regresamos a todos al lobby sin pedir nombre
    eventlet.sleep(1)
    socketio.emit('actualizar_lista', list(game['jugadores'].values()))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
