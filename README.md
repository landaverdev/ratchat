# RatChat

Juego web de chat multijugador (ratas en una alcantarilla) con un **sistema de IA que detecta y censura
groserías, insultos, odio y amenazas**.

## Estructura

```
ratchat/
├── cliente-web/   El juego (HTML, CSS y JavaScript). Se sube a ratchatapp.com
├── servidor/      Python: servidor del chat + modelo de IA. Corre en Render.com
├── dashboard.html Dashboard autocontenido (métricas reales + simulador). Doble clic para abrir
└── render.yaml    Configuración de Render (entrena el modelo al publicar)
```

## Cómo se conecta todo

- **ratchatapp.com** solo aloja la carpeta `cliente-web/` (el juego).
- **Render.com** ejecuta `servidor/`: entrena el modelo al publicar y atiende el chat (WebSocket `/ws`) y la API del detector.
- La dirección del servidor está en `cliente-web/js/config.js` (`servidor: "https://ratchat.onrender.com"`).
  **Cámbiala por la URL real de tu servicio en Render** y vuelve a subir la web.

## Publicar

1. **Render:** sube este proyecto a GitHub, en Render elige *New > Blueprint* y selecciona el repositorio.
   Al terminar te da una URL (por ejemplo `https://ratchat.onrender.com`). Prueba `/salud`.
   En el plan gratis el servidor se duerme y tarda hasta un minuto en despertar.
2. **Web:** pon esa URL en `cliente-web/js/config.js` y sube el contenido de `cliente-web/` a ratchatapp.com.

## Probar en tu computadora

```
cd servidor
pip install -r requirements.txt
python entrenar.py
SERVIR_WEB=1 uvicorn app:app --port 8000     # y en config.js deja servidor: ""
```
Abre http://localhost:8000

## Reglas del juego

- Groserías, insultos, palabras de odio y amenazas se censuran para todos y dan una advertencia.
- A la 3.ª advertencia quedas baneado (puedes volver con otro nombre).
- No se permiten nombres con groserías, insultos u odio.
- Los mensajes del chat se borran a los 5 minutos, empezando por los más antiguos.

## Dashboard para la revisión académica

Abre **`dashboard.html`** con doble clic en cualquier navegador (no necesita internet, servidor ni librerías:
los datos y el código van dentro del archivo). Incluye:

- Distribución de las 10,400 frases por categoría.
- Comparativa de exactitud, precisión, recall y F1 entre el **modelo de IA solo** y el **sistema híbrido**
  (promedio y desviación de 5 divisiones por plantillas no vistas).
- Matrices de confusión, aciertos por tipo y ejemplos de errores (también de `prueba_dificil.csv`).
- Un **simulador interactivo en JavaScript** que muestra paso a paso el texto normalizado, la categoría, el motivo
  (`lexico`, `contexto` o `modelo`), la probabilidad y el texto censurado con `*`, para mensajes de chat y para nombres
  de usuario.

**El simulador es una réplica en JavaScript hecha para demostración**: el servidor real corre en Python. Se comprobó
que coincide con `detector.py` (categoría, motivo, texto censurado y nombres idénticos, y probabilidad con diferencia
menor a 0.0005) en las 136 frases de `prueba_dificil.csv`, 1,500 frases del dataset y 10 ejemplos extra.

`dashboard.html` se regenera solo al ejecutar `python entrenar.py` (o con `python construir_dashboard.py`), a partir de
`modelo/metricas.json`, `modelo/modelo.joblib` y `detector/lexico.py`. Si cambian el léxico o el modelo, regeneren el archivo.

## El sistema inteligente

El detector es **híbrido** (reglas + IA) y censura cuatro categorías:

| Categoría | Ejemplos | Cuándo se censura |
|---|---|---|
| Grosería | "qué chingón", "pinche lag", "no mames" | siempre (amistoso u ofensivo) |
| Odio | joto, marica, "odio a los gays" | siempre |
| Amenaza | "te voy a violar", "ojalá te mueras" | siempre |
| Insulto | "eres un pendejo", "tonto", "perra" | palabras claras siempre; las ambiguas según el contexto |

Flujo de `detector/detector.py` (`Detector.analizar`):

1. **Normalización** (`detector/normalizar.py`): quita acentos, cambia números y símbolos por letras
   (`P3ND3J0`), reduce letras repetidas (`idiotaaaa`) y junta letras separadas (`p.e.n.d.e.j.o`, `p e n d e j o`).
   Cada palabra conserva su posición en el texto original para poder censurarla.
2. **Léxico** (`detector/lexico.py`): raíces, palabras completas, palabras de odio, léxico en inglés y expresiones
   regulares de frases (amenazas, odio, expresiones groseras). Hay listas de excepciones ("computadora", "Maricela",
   "Vergara", "violar las reglas") para no censurar palabras normales. Motivo: `lexico`.
3. **Contexto**: palabras ambiguas ("perra", "tonto") se censuran si hay una señal de insulto en las 3 palabras
   anteriores ("eres una perra"), o si el modelo da ≥ 0.5 y no hay señal de animal u objeto ("mi perra tuvo
   cachorros" se deja). Motivo: `contexto`.
4. **Modelo de IA**: `TfidfVectorizer` (palabras 1-2) + `TfidfVectorizer` (letras 2-5, `char_wb`) unidos con
   `FeatureUnion` y `LogisticRegression(C=4, class_weight="balanced")`. Si no se encontró ninguna palabra conocida,
   solo censura el mensaje completo con probabilidad ≥ 0.85. Motivo: `modelo`.
5. **Censura**: cada palabra marcada se reemplaza por `*` conservando espacios. La categoría final es la de mayor
   prioridad (amenaza > odio > grosería > insulto).

Los **nombres de usuario** pasan por un filtro más estricto (`Detector.nombre_permitido`): busca raíces ofensivas
dentro del nombre aunque estén pegadas ("ElPendejo99", "xXPutoXx"), con excepciones para nombres normales, y además
usa el detector de chat y el modelo (umbral 0.85).

## Dataset: curaduría y generación

`servidor/datos/dataset_groserias.csv` tiene **10,400 frases únicas en español** (375,663 caracteres, 590 plantillas).
**Es un dataset sintético**: no se descargó ni se copió de ninguna fuente externa, no hay scraping y no se usó un
modelo de lenguaje para escribirlo. Todo sale de `datos/generar_dataset.py` con semilla fija (2026), así que se
puede reproducir con `python datos/generar_dataset.py`.

| Tipo | Frases | Plantillas | Etiqueta |
|---|---|---|---|
| insulto | 3,000 | 99 | 1 (se censura) |
| grosería | 2,300 | 93 | 1 (se censura) |
| odio | 700 | 46 | 1 (se censura) |
| amenaza | 800 | 37 | 1 (se censura) |
| limpio | 3,600 | 315 | 0 |

**Curaduría manual.** El equipo escribió a mano las listas de vocabulario (insultos masculinos y femeninos, adjetivos,
groserías y expresiones de jerga gamer mexicana, palabras de odio, amenazas, nombres de usuario con temática de rata) y
las plantillas, con distintos registros: chat informal con faltas de ortografía, mensajes en mayúsculas, texto con
emojis, frases largas y cortas, amistosas y agresivas. Las plantillas "limpias" incluyen **casos trampa** que parecen
groserías sin serlo: nombres como "Maricela" o "Vergara", "computadora", "violar las reglas", la perra mascota, "te voy a
ganar", menciones respetuosas de grupos y expresiones de enojo con el juego sin insultar a nadie.

**Variaciones.** Cada plantilla se llena con distintas palabras y luego se aplican transformaciones al azar: leetspeak,
letras alargadas, letras separadas, sin acentos, faltas de ortografía, prefijos y sufijos y estilo global (mayúsculas,
emojis). El generador valida que todo sea único, que no haya la misma frase con dos etiquetas y que el total sea
exactamente 10,400. Ninguna frase está en inglés (el léxico en inglés del detector sirve para mensajes reales).

**Campo `plantilla`.** Cada fila guarda el molde del que salió. `entrenar.py` lo usa como grupo en `GroupShuffleSplit`
para que una plantilla nunca esté a la vez en entrenamiento y prueba.

**Datasets externos (opcional).** Si consiguen un corpus real, `datos/importar_externos.py` lo normaliza y lo agrega a
`datos/externos.csv`; `entrenar.py` lo incluye solo. El script está documentado en su encabezado y **no descarga nada**.
Ejemplo:

```
cd servidor
python datos/importar_externos.py mensajes.csv --texto texto --etiqueta clase --inapropiado 1
python entrenar.py
```

## Entrenamiento y resultados

`cd servidor && python entrenar.py` evalúa, guarda `modelo/modelo.joblib` y escribe `modelo/metricas.json`.

| Evaluación | Exactitud | F1 (inapropiado) |
|---|---|---|
| Solo el modelo de IA, plantillas nunca vistas (5 divisiones) | 92.0 % ± 1.5 | 94.0 % ± 1.1 |
| Sistema híbrido, plantillas nunca vistas | 97.2 % ± 0.4 | 97.8 % ± 0.2 |
| `prueba_dificil.csv` (136 frases escritas a mano, sistema híbrido) | 98.5 % | 99.0 % |

Los errores (en `metricas.json` y en el dashboard) son sobre todo falsos positivos en frases limpias con estructura
parecida a un mensaje ofensivo ("hay que tirar la basura") y frases de odio muy distintas al léxico.
Las 136 frases se usaron mientras se ajustaba el léxico, así que ese 98.5 % es optimista.

## Limitaciones

- **El dataset es sintético**: las métricas miden qué tan bien se aprende el estilo del generador, no el chat real.
  Con mensajes reales de jugadores los resultados serían menores. Lo ideal es validar con datos reales etiquetados.
- La validación por plantillas evita memorizar moldes, pero las plantillas siguen siendo del mismo equipo y estilo.
- Insultos "educados" sin groserías ("me caes mal") pasan, y hay falsos positivos en frases limpias parecidas a un insulto.
- Amenazas y odio con palabras ausentes del léxico dependen solo del modelo.
- La jerga regional nueva no se detecta hasta que se agregue a `lexico.py`.
- Las etiquetas reflejan criterios del equipo (por ejemplo, groserías amistosas también se censuran); otro criterio
  daría otras etiquetas.
- El simulador del dashboard es una réplica en JavaScript; ante cualquier diferencia manda el código Python.

## Borrado de mensajes

El servidor guarda cada mensaje con su hora y cada 2 s borra los de más de 5 minutos
(`VIDA_MENSAJE` en `servidor/app.py`), del más viejo al más nuevo, y avisa a los clientes con un evento `borrar`.

## Probar el detector en vivo

`https://TU-SERVIDOR/api/analizar?texto=te%20voy%20a%20violar` devuelve la categoría, el texto
censurado y las palabras detectadas. `https://TU-SERVIDOR/api/metricas` muestra las métricas.
