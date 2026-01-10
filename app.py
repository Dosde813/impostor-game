import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_v_venezuela_final"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

game = {
    "encendido": False,
    "jugadores": {},  
    "impostor_sid": None,
    "palabra": "",
    "pista": ""
}

# DICCIONARIO AMPLIADO - Aquí puedes meter todas las que quieras
RECURSOS = {
    "Arepa": "Se come en el desayuno o cena",
    "Hallaca": "Huele a navidad y lleva pabilo",
    "Cerveza": "Bien fría en una cava con hielo",
    "Malta": "Bebida negra dulce muy nuestra",
    "Tequeño": "El rey de todas las fiestas",
    "Empanada": "Se compra en la calle con salsa de ajo",
    "Metro": "Transporte que siempre va full",
    "Cine": "Lugar para comer cotufas",
    "Béisbol": "Deporte que paraliza al país",
    "Chinchorro": "Para echarse un camarón (siesta)",
    "Papelón con Limón": "Bebida para el calor del mediodía",
    "Tiburón": "Animal que da miedo en la playa",
    "Ávila": "La montaña que se ve desde la capital",
    "Carro": "Medio para ir al trabajo o de viaje",
    "Plátano": "Si está frito es tajada",
    "Chamo": "Persona joven o amigo",
    "Sifrino": "Alguien que habla con la papa en la boca",
    "Moto": "Transporte que esquiva el tráfico",
    "Playera": "Camisa que se usa para ir a la costa",
    "Dominó": "Juego de mesa que se tranca",
    "Ron": "Bebida espirituosa de caña",
    "Pirulín": "Barrita de chocolate famosa",
    "Susy": "Galleta de chocolate muy querida",
    "Teclado": "Se usa para escribir en la computadora",
    "Celular": "Donde estás jugando ahorita mismo"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impostor Criollo</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Arial', sans-serif; background: #0b0d17; color: white; text-align: center; margin: 0; padding: 20px; }
        .box { background: #1c1f33; padding: 25px; border-radius: 20px; max-width: 320px; margin: 20px auto; border: 1px solid #444; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .btn { background: #ff4b2b; color: white; border: none; padding: 15px; border-radius: 10px; width: 100%; cursor: pointer; margin-top: 15px; font-weight: bold; font-size: 16px; }
        .hidden { display: none; }
        #lista { text-align: left; background: #0b0d17; padding: 12px; border-radius: 10px; margin: 15px 0; border: 1px solid #333; min-height: 40px; }
        input { width: 90%; padding: 12px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #444; background: #2a2e45; color: white; font-size: 16px; }
        h2 { color: #ff4b2b; text-transform: uppercase; letter-spacing: 2px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>IMPOSTOR</h2>
        <div id="sec-off"><p style="color:#ffcc00; font-weight:bold;">ESPERANDO AL ANFITRIÓN...</p></div>
        
        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:#000;" onclick="socket.emit('activar')">ENCENDER SERVIDOR</button>
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="¿Cómo te llamas?">
            <button class="btn" onclick="unirse()">ENTRAR A LA SALA</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3 id="status-lobby">En la sala:</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:#000;" onclick="socket.emit('iniciar')">¡INICIAR PARTIDA!</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-text" style="font-size:24px; font-weight:bold; margin:25px 0;"></div>
            <p id="pista-text" style="color:#aaa; font-style:italic; font-size:18px; line-height:1.4;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#ffcc00; color:#000; margin-top:30px;" onclick="socket.emit('finalizar')">REVELAR IMPOSTOR</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        let yaEntro = false;

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function unirse() {
            const n = document.getElementById('nombre').value;
            if(n) {
                yaEntro = true;
                socket.emit('unirse', {nombre: n});
                document.getElementById('sec-reg').classList.add('hidden');
                document.getElementById('sec-lobby').classList.remove('hidden');
            }
        }

        socket.on('estado_servidor', (data) => {
            if(data.encendido && !yaEntro) {
                document.getElementById('sec-off').classList.add('hidden');
                document.getElementById('sec-reg').classList.remove('hidden');
            }
        });

        socket.on('actualizar_lista', (data) => {
            if(yaEntro) {
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
                res.innerHTML = '<span style="color:#ff4b2b">¡ERES EL IMPOSTOR!</span>';
                pst.innerHTML = "<b>Tu Pista:</b><br>" + data.pista;
            } else {
                res.innerHTML = 'Tu Palabra es:<br><span style="color:#00ff88; font-size:35px;">' + data.palabra + '</span>';
                pst.innerHTML = "¡No dejes que el impostor sepa qué es!";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        socket.on('reset', (data) => {
            alert("EL IMPOSTOR ERA: " + data.nombre + "\\nLA PALABRA ERA: " + data.palabra);
            location.reload();
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

@socketio.on('unirse')
def on_unirse(data):
    game['jugadores'][request.sid] = data['nombre']
    socketio.emit('actualizar_lista', list(game['jugadores'].values()))

@socketio.on('iniciar')
def on_iniciar():
    sids = list(game['jugadores'].keys())
    if len(sids) < 2: return
    
    # Lógica de barajado criollo
    game['impostor_sid'] = random.choice(sids)
    game['palabra'], game['pista'] = random.choice(list(RECURSOS.items()))
    
    # REPARTO PRIVADO - NADIE VE LO QUE NO DEBE
    for sid in sids:
        if sid == game['impostor_sid']:
            socketio.emit('ver_rol', {'rol': 'impostor', 'pista': game['pista']}, room=sid)
        else:
            socketio.emit('ver_rol', {'rol': 'civil', 'palabra': game['palabra']}, room=sid)

@socketio.on('finalizar')
def on_finalizar():
    nombre = game['jugadores'].get(game['impostor_sid'], "Desconocido")
    socketio.emit('reset', {'nombre': nombre, 'palabra': game['palabra']})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
