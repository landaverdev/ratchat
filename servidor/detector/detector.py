"""
Detector de lenguaje inapropiado de RatChat (sistema híbrido: reglas + modelo de IA).

Qué censura:
  - GROSERÍAS y palabras altisonantes, ya sea en tono ofensivo o amistoso
    ("qué chingón", "pinche lag", "eres un pendejo").
  - Palabras de ODIO (joto, marica, ...) y frases de odio.
  - AMENAZAS ("te voy a violar", "te voy a matar", "ojalá te mueras").
  - Insultos con palabras que el léxico no conoce: los detecta el MODELO DE IA
    (TF-IDF + regresión logística) leyendo el mensaje completo.
  - Palabras ambiguas ("perra", "tonto") solo cuando el contexto indica que insultan.

Pasos:
    1. Normaliza el texto (quita disfraces como P3ND3J0 o p.e.n.d.e.j.o).
    2. Busca groserías, odio y amenazas en el léxico (palabras y frases).
    3. Revisa las palabras ambiguas con reglas de contexto y con el modelo.
    4. Si no encontró nada, el modelo de IA evalúa el mensaje completo.
    5. Se censuran con * solo las palabras que lo provocaron.
"""

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import joblib

from . import lexico as L
from .normalizar import quitar_acentos, tokenizar

RUTA_MODELO = Path(__file__).resolve().parent.parent / "modelo" / "modelo.joblib"
UMBRAL_CONTEXTO = 0.5   # palabras ambiguas ("tonto"): el modelo debe estar al menos así de seguro
UMBRAL_MODELO = 0.85    # mensajes sin ninguna palabra conocida: se exige más seguridad
UMBRAL_NOMBRE = 0.85    # nombres de usuario

PRIORIDAD = {"amenaza": 3, "odio": 2, "groseria": 1, "insulto": 0}


@dataclass
class Resultado:
    es_inapropiado: bool
    categoria: str            # "", "groseria", "insulto", "odio" o "amenaza"
    probabilidad: float       # probabilidad que da el modelo de IA
    texto_censurado: str
    palabras_censuradas: list = field(default_factory=list)
    motivo: str = ""          # "lexico", "contexto" o "modelo"

    def a_dict(self):
        return asdict(self)


def _censurar(texto: str, tramos) -> str:
    out = list(texto)
    for inicio, fin in tramos:
        for k in range(inicio, fin):
            if not out[k].isspace():
                out[k] = "*"
    return "".join(out)


class Detector:
    def __init__(self, ruta_modelo: Path = RUTA_MODELO, modelo=None):
        if modelo is not None:          # (se usa al evaluar, con un modelo recién entrenado)
            self.modelo = modelo
            return
        if not Path(ruta_modelo).exists():
            raise FileNotFoundError(
                f"No encontré el modelo en {ruta_modelo}. Entrénalo primero con: python entrenar.py"
            )
        self.modelo = joblib.load(ruta_modelo)

    def probabilidad(self, texto: str) -> float:
        return float(self.modelo.predict_proba([texto])[0][1])

    # ------------------------------------------------------------------
    def analizar(self, texto: str) -> Resultado:
        texto = texto or ""
        tokens = tokenizar(texto)
        palabras = [t[0] for t in tokens]
        prob = self.probabilidad(texto)

        marcados: dict[int, str] = {}          # índice de token -> categoría

        def marcar(i, cat):
            if i not in marcados or PRIORIDAD[cat] > PRIORIDAD[marcados[i]]:
                marcados[i] = cat

        # 1) Palabras sueltas del léxico (siempre se censuran)
        for i, p in enumerate(palabras):
            if L.es_palabra_odio(p):
                marcar(i, "odio")
            elif L.es_palabra_groseria(p) or L.es_palabra_ingles(p):
                marcar(i, "groseria")

        # 2) Frases (de varias palabras): odio, amenazas y groserías compuestas
        plano = " ".join(palabras)
        inicios, pos = [], 0
        for p in palabras:
            inicios.append((pos, pos + len(p)))
            pos += len(p) + 1

        def tokens_de(m):
            return [i for i, (a, b) in enumerate(inicios) if a < m.end() and b > m.start()]

        for m in L.frase_amenaza(plano):
            for i in tokens_de(m):
                marcar(i, "amenaza")
        for m in L.frase_odio(plano):
            for i in tokens_de(m):
                marcar(i, "odio")
        for m in L.frase_grosera(plano):
            for i in tokens_de(m):
                marcar(i, "groseria")

        motivo = "lexico" if marcados else ""

        # 3) Palabras ambiguas: solo si el contexto indica insulto
        for i, p in enumerate(palabras):
            if i in marcados or not L.es_palabra_contexto(p):
                continue
            animal = any(w in L._SENAL_ANIMAL for w in palabras)
            if L.contexto_insulto(palabras, i) or (prob >= UMBRAL_CONTEXTO and not animal):
                marcar(i, "insulto")
                motivo = motivo or "contexto"

        # 4) Sin nada conocido: el modelo de IA lee el mensaje completo
        if not marcados and prob >= UMBRAL_MODELO and tokens:
            for i in range(len(tokens)):
                marcar(i, "insulto")
            motivo = "modelo"

        if not marcados:
            return Resultado(False, "", round(prob, 3), texto)

        categoria = max(marcados.values(), key=lambda c: PRIORIDAD[c])
        tramos = [(tokens[i][1], tokens[i][2]) for i in sorted(marcados)]
        return Resultado(
            es_inapropiado=True,
            categoria=categoria,
            probabilidad=round(prob, 3),
            texto_censurado=_censurar(texto, tramos),
            palabras_censuradas=[texto[a:b] for a, b in tramos],
            motivo=motivo,
        )

    # ------------------------------------------------------------------
    def nombre_permitido(self, nombre: str) -> bool:
        """Un nombre no puede contener groserías, odio, amenazas ni insultos, ni siquiera pegados."""
        sin_acentos = quitar_acentos(nombre.lower())
        compacto = re.sub(r"[^a-z]", "", sin_acentos.translate(
            str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"})))
        compacto = re.sub(r"(.)\1{2,}", r"\1\1", compacto)            # ppppendejo -> ppendejo
        compacto_sin_seguros = L.NOMBRES_SEGUROS.sub("", compacto)
        if any(raiz in compacto_sin_seguros for raiz in L.RAICES_NOMBRE_LARGAS):
            return False
        # Letras repetidas dentro de la raíz: "peeendejo"
        sin_repetir = re.sub(r"(.)\1+", r"\1", compacto_sin_seguros)
        if any(re.sub(r"(.)\1+", r"\1", raiz) in sin_repetir for raiz in L.RAICES_NOMBRE_LARGAS if len(raiz) >= 5):
            return False
        # Mismas reglas que en el chat (palabras sueltas y frases)
        r = self.analizar(nombre)
        if r.es_inapropiado and r.motivo != "contexto":
            return False
        return self.probabilidad(nombre) < UMBRAL_NOMBRE
