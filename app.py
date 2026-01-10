import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = "impostor_definitivo_v4"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

game = {
    "encendido": False,
    "jugadores": {}, # sid: nombre
    "impostor_sid": None,
    "palabra": "",
    "pista": ""
}

RECURSOS = {
    "Arepa": "Hecha de maíz", "Cerveza": "Bebida con espuma", "Metro": "Transporte rápido", 
    "Hallaca": "Navidad", "Teclado": "Para escribir", "Monitor": "Pantalla",
    "Plátano": "Frito es rico", "Chamo": "Un joven", "Sifrino": "Persona con plata"
}

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Impostor Fijo</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0b0d17; color: white; text-align: center; }
        .box { background: #1c1f33; padding: 20px; border-radius: 15px; max-width: 300px; margin: 40px auto; border: 1px solid #444; }
        .btn { background: #ff4b2b; color: white; border: none; padding: 12px; border-radius: 8px; width: 100%; cursor: pointer; margin-top: 10px; font-weight: bold; }
        .hidden { display: none; }
        #lista { text-align: left; background: #0b0d17; padding: 10px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
        input { width: 85%; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: none; background: #2a2e45; color: white; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="color:#ff4b2b;">IMPOSTOR</h2>
        
        <div id="sec-off">
            <p style="color:#ffcc00;">SALA CERRADA</p>
        </div>
        
        <div id="sec-admin" class="hidden">
            <button class="btn" style="background:#00ff88; color:#000;" onclick="socket.emit('activar')">ENCENDER JUEGO</button>
            <hr style="border:0.1px solid #333;">
        </div>

        <div id="sec-reg" class="hidden">
            <input type="text" id="nombre" placeholder="Tu Apodo...">
            <button class="btn" onclick="unirse()">ENTRAR AL JUEGO</button>
        </div>

        <div id="sec-lobby" class="hidden">
            <h3>En el Lobby:</h3>
            <div id="lista"></div>
            <button id="btn-iniciar" class="btn hidden" style="background:#00ff88; color:#000;" onclick="socket.emit('iniciar')">INICIAR PARTIDA</button>
        </div>

        <div id="sec-juego" class="hidden">
            <div id="rol-text" style="font-size:20px; font-weight:bold; margin:20px;"></div>
            <p id="pista-text" style="color:#aaa; font-style:italic;"></p>
            <button id="btn-fin" class="btn hidden" style="background:#ffcc00; color:#000;" onclick="socket.emit('finalizar')">REVELAR TODO</button>
        </div>
    </div>

    <script>
        const socket = io();
        const isAdmin = window.location.search.includes('admin=true');
        let yaEntro = false; // LLAVE MAESTRA: Evita que la pantalla cambie sola

        if(isAdmin) document.getElementById('sec-admin').classList.remove('hidden');

        function unirse() {
            const n = document.getElementById('nombre').value;
            if(n) {
                yaEntro = true; // El usuario dio permiso para cambiar de pantalla
                socket.emit('unirse', {nombre: n, admin: isAdmin});
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
            // Solo actualiza visualmente la lista si la persona ya entró al lobby
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
                res.innerHTML = '<span style="color:red">ERES EL IMPOSTOR</span>';
                pst.innerHTML = "Pista: " + data.pista;
            } else {
                res.innerHTML = 'Tu Palabra: <br><span style="color:#00ff88">' + data.palabra + '</span>';
                pst.innerHTML = "";
            }
            if(isAdmin) document.getElementById('btn-fin').classList.remove('hidden');
        });

        socket.on('reset', (data) => {
            alert("EL IMPOSTOR ERA: " + data.nombre + "\\nPALABRA: " + data.palabra);
            location.reload();
        });
    </script>
</body>
</html>
