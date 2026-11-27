"""
Servidor de RatChat.

  - /ws             conexión en tiempo real del juego (WebSocket)
  - /api/analizar   prueba el detector:  /api/analizar?texto=qu%C3%A9%20ching%C3%B3n
  - /api/metricas   métricas del modelo (para la presentación)
  - /               sirve el cliente web (carpeta ../cliente-web)

Ejecutar en local:   uvicorn app:app --reload --port 8000
"""

import asyncio
import json
import os
import random
import re
import time
import uuid
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from detector import Detector
from detector.normalizar import quitar_acentos

AQUI = Path(__file__).resolve().parent
CLIENTE_WEB = AQUI.parent / "cliente-web"

# --- Reglas del juego (el cliente usa los mismos valores) ----------------------
MUNDO = {"ancho": 960, "alto": 600, "x_min": 40, "x_max": 920, "y_min": 255, "y_max": 575}
MAX_ADVERTENCIAS = 3
MAX_CARACTERES = 120
VIDA_MENSAJE = int(os.environ.get("RATCHAT_VIDA_MENSAJE", 300))            # segundos: el chat borra cada mensaje a los 5 minutos (primero los más viejos)
REVISION_BORRADO = 2          # cada cuántos segundos se revisa qué mensajes ya caducaron
MAX_MENSAJES = 150            # tope de seguridad
MAX_JUGADORES = 60
ESPERA_ENTRE_MENSAJES = 0.8   # segundos
ESPERA_ENTRE_MOVIMIENTOS = 0.05
NOMBRE_RE = re.compile(r"^[0-9A-Za-zÀ-ÖØ-öø-ÿ _\-.]{2,15}$")
# Colores de pelaje: grises y cafés de rata, más algunos de fantasía
COLORES = ["#9aa3a8", "#c9b39a", "#8b6b52", "#6d7680", "#f0eee9", "#b98fd9",
           "#5fa8e8", "#f07c74", "#58c08a", "#f2b84b", "#ff8fc0", "#4fc4c9"]

detector = Detector()


class Jugador:
    def __init__(self, ws: WebSocket, nombre: str):
        self.ws = ws
        self.id = uuid.uuid4().hex[:8]
        self.nombre = nombre
        en_uso = {j.color for j in sala.jugadores.values()}
        self.color = random.choice([c for c in COLORES if c not in en_uso] or COLORES)
        self.x = random.randint(MUNDO["x_min"] + 80, MUNDO["x_max"] - 80)
        self.y = random.randint(MUNDO["y_min"] + 60, MUNDO["y_max"] - 30)
        self.advertencias = 0
        self.ultimo_mensaje = 0.0
        self.ultimo_movimiento = 0.0
        self.candado = asyncio.Lock()

    def publico(self):
        return {"id": self.id, "nombre": self.nombre, "color": self.color, "x": self.x, "y": self.y}

    async def enviar(self, datos: dict):
        try:
            async with self.candado:
                await self.ws.send_text(json.dumps(datos, ensure_ascii=False))
        except Exception:
            pass  # si ya se desconectó, se limpia en su propio ciclo


class Sala:
    def __init__(self):
        self.jugadores: dict[str, Jugador] = {}
        self.historial: list = []        # mensajes vivos, del más viejo al más nuevo
        self.limpiador = None
        self.baneados: set[str] = set()

    @staticmethod
    def clave(nombre: str) -> str:
        return quitar_acentos(nombre).lower().strip()

    def validar_nombre(self, nombre: str):
        """Devuelve un mensaje de error, o None si el nombre está bien."""
        if not NOMBRE_RE.match(nombre):
            return "El nombre debe tener de 2 a 15 caracteres (letras, números, espacio, _ - .)."
        if self.clave(nombre) in self.baneados:
            return "Ese usuario está baneado. Entra con otro nombre."
        if any(self.clave(j.nombre) == self.clave(nombre) for j in self.jugadores.values()):
            return "Ya hay alguien conectado con ese nombre."
        if not detector.nombre_permitido(nombre):
            return "Ese nombre no está permitido (no se aceptan groserías, insultos ni palabras de odio). Elige otro."
        if len(self.jugadores) >= MAX_JUGADORES:
            return "La sala está llena, intenta en un rato."
        return None

    async def difundir(self, datos: dict, excepto: str | None = None):
        await asyncio.gather(*(j.enviar(datos) for j in list(self.jugadores.values()) if j.id != excepto))

    def guardar(self, msg: dict) -> dict:
        """Le pone un identificador al mensaje y lo guarda en el historial."""
        msg["mid"] = uuid.uuid4().hex[:10]
        self.historial.append(msg)
        return msg

    async def sistema(self, texto: str):
        await self.difundir(self.guardar({"tipo": "sistema", "texto": texto, "hora": time.time()}))

    async def borrar_caducados(self):
        """Borra los mensajes de más de VIDA_MENSAJE segundos, empezando por los más antiguos."""
        ahora = time.time()
        ids = []
        while self.historial and (ahora - self.historial[0]["hora"] >= VIDA_MENSAJE
                                  or len(self.historial) > MAX_MENSAJES):
            ids.append(self.historial.pop(0)["mid"])
        if ids:
            await self.difundir({"tipo": "borrar", "ids": ids})

    def iniciar_limpiador(self):
        """Arranca (una sola vez) la tarea que borra los mensajes viejos."""
        if self.limpiador is None or self.limpiador.done():
            self.limpiador = asyncio.get_running_loop().create_task(self._ciclo_limpieza())

    async def _ciclo_limpieza(self):
        while True:
            await asyncio.sleep(REVISION_BORRADO)
            try:
                await self.borrar_caducados()
            except Exception as e:   # que un error no detenga la limpieza
                print("[limpieza] error:", repr(e))


sala = Sala()


def recortar(valor, minimo, maximo):
    try:
        return max(minimo, min(maximo, float(valor)))
    except (TypeError, ValueError):
        return None


async def ws_juego(ws: WebSocket):
    await ws.accept()
    sala.iniciar_limpiador()
    jugador = None
    try:
        # 1) Esperar un nombre válido
        while jugador is None:
            datos = json.loads(await ws.receive_text())
            if datos.get("tipo") == "ping":
                await ws.send_text('{"tipo":"pong"}')
                continue
            if datos.get("tipo") != "entrar":
                continue
            nombre = re.sub(r"\s+", " ", str(datos.get("nombre", ""))).strip()
            error = sala.validar_nombre(nombre)
            if error:
                await ws.send_text(json.dumps({"tipo": "error_ingreso", "mensaje": error}, ensure_ascii=False))
                continue
            jugador = Jugador(ws, nombre)
            sala.jugadores[jugador.id] = jugador
            await jugador.enviar({
                "tipo": "bienvenida",
                "id": jugador.id,
                "mundo": MUNDO,
                "max_advertencias": MAX_ADVERTENCIAS,
                "vida_mensaje": VIDA_MENSAJE,
                "jugadores": [j.publico() for j in sala.jugadores.values()],
                "historial": list(sala.historial),
            })
            await sala.difundir({"tipo": "entra", "jugador": jugador.publico()}, excepto=jugador.id)
            await sala.sistema(f"{nombre} entró a la sala")

        # 2) Ciclo del juego
        while True:
            datos = json.loads(await ws.receive_text())
            tipo = datos.get("tipo")
            ahora = time.monotonic()

            if tipo == "ping":
                await jugador.enviar({"tipo": "pong"})

            elif tipo == "mover":
                if ahora - jugador.ultimo_movimiento < ESPERA_ENTRE_MOVIMIENTOS:
                    continue
                x = recortar(datos.get("x"), MUNDO["x_min"], MUNDO["x_max"])
                y = recortar(datos.get("y"), MUNDO["y_min"], MUNDO["y_max"])
                if x is None or y is None:
                    continue
                jugador.ultimo_movimiento = ahora
                jugador.x, jugador.y = round(x), round(y)
                await sala.difundir({"tipo": "mover", "id": jugador.id, "x": jugador.x, "y": jugador.y})

            elif tipo == "chat":
                texto = re.sub(r"\s+", " ", str(datos.get("texto", ""))).strip()[:MAX_CARACTERES]
                if not texto:
                    continue
                if ahora - jugador.ultimo_mensaje < ESPERA_ENTRE_MENSAJES:
                    await jugador.enviar({"tipo": "aviso", "mensaje": "Más despacio, espera un momento."})
                    continue
                jugador.ultimo_mensaje = ahora

                resultado = detector.analizar(texto)
                mensaje = sala.guardar({
                    "tipo": "chat", "id": jugador.id, "nombre": jugador.nombre, "color": jugador.color,
                    "texto": resultado.texto_censurado, "censurado": resultado.es_inapropiado, "hora": time.time(),
                })
                await sala.difundir(mensaje)
                print(f"[chat] {jugador.nombre}: {texto!r} -> {resultado.categoria or 'ok'} p={resultado.probabilidad}")

                if resultado.es_inapropiado:
                    jugador.advertencias += 1
                    if jugador.advertencias < MAX_ADVERTENCIAS:
                        await jugador.enviar({
                            "tipo": "advertencia", "numero": jugador.advertencias, "maximo": MAX_ADVERTENCIAS,
                            "categoria": resultado.categoria, "palabras": resultado.palabras_censuradas,
                        })
                    else:
                        sala.baneados.add(sala.clave(jugador.nombre))
                        await jugador.enviar({"tipo": "baneado", "nombre": jugador.nombre, "maximo": MAX_ADVERTENCIAS})
                        await asyncio.sleep(0.2)
                        await ws.close(code=4003)
                        return  # el bloque finally avisa a los demás

    except (WebSocketDisconnect, json.JSONDecodeError, RuntimeError):
        pass
    finally:
        if jugador and sala.jugadores.pop(jugador.id, None):
            await sala.difundir({"tipo": "sale", "id": jugador.id})
            baneado = sala.clave(jugador.nombre) in sala.baneados
            await sala.sistema(f"{jugador.nombre} fue baneado por lenguaje inapropiado" if baneado
                               else f"{jugador.nombre} salió de la sala")


CORS = {"Access-Control-Allow-Origin": "*"}


async def api_analizar(request: Request):
    texto = request.query_params.get("texto", "")[:300]
    return JSONResponse(detector.analizar(texto).a_dict(), headers=CORS)


async def api_metricas(request: Request):
    ruta = AQUI / "modelo" / "metricas.json"
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    return JSONResponse(datos, headers=CORS)


async def salud(request: Request):
    return JSONResponse({"ok": True, "jugadores": len(sala.jugadores)}, headers=CORS)


async def raiz(request: Request):
    return JSONResponse({"servicio": "RatChat", "ok": True, "web": "https://ratchatapp.com"}, headers=CORS)


rutas = [
    WebSocketRoute("/ws", ws_juego),
    Route("/api/analizar", api_analizar),
    Route("/api/metricas", api_metricas),
    Route("/salud", salud),
]
# En producción la web vive en ratchatapp.com y este servidor solo hace de IA + chat.
# Para probar todo junto en tu computadora: SERVIR_WEB=1 uvicorn app:app
if os.environ.get("SERVIR_WEB") == "1" and CLIENTE_WEB.exists():
    rutas.append(Mount("/", StaticFiles(directory=CLIENTE_WEB, html=True)))
else:
    rutas.append(Route("/", raiz))

app = Starlette(routes=rutas)
