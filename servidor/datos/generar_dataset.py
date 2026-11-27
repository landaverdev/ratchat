"""
Generador del dataset de RatChat (10,400 frases en español).

IMPORTANTE (transparencia): el dataset es SINTÉTICO. No viene de redes sociales ni de ningún
sitio web: lo generamos con este script a partir de vocabulario y plantillas que escribimos
a mano (curaduría manual) y de transformaciones automáticas (disfraces, faltas de ortografía,
mayúsculas, signos y emojis). No usa scraping ni modelos de lenguaje.

Cada frase queda etiquetada con un tipo y con la plantilla que la generó:

    tipo       etiqueta  ejemplo
    insulto    1         "eres un pendejo"
    groseria   1         "qué chingón jugaste"   (también se censura, aunque sea amistosa)
    odio       1         "ese marica no sabe jugar"
    amenaza    1         "te voy a violar"
    limpio     0         chat normal + frases "trampa" que parecen mala palabra y no lo son
                         ("Maricela", "mi computadora", "no hay que violar las reglas")

El campo `plantilla` identifica el molde de cada frase. entrenar.py lo usa con GroupShuffleSplit:
las plantillas de prueba NO aparecen en el entrenamiento, así el modelo no puede "aprenderse"
las frases de memoria y las métricas son más honestas.

Variedad: cada molde tiene espacios ({m}, {n}, {x}...) que se llenan con listas grandes de
palabras; hay moldes de distintos registros (coloquial mexicano, juvenil/gamer, formal,
narrativo, preguntas, mensajes cortos, con faltas de ortografía) y a cada frase se le pueden
agregar muletillas, emojis, mayúsculas o errores de escritura. Todo el texto está en español.

Uso (desde la carpeta servidor/datos):
    python generar_dataset.py        -> escribe dataset_groserias.csv (10,400 filas, siempre igual)
"""

import csv
import random
from pathlib import Path

SEMILLA = 2026
AQUI = Path(__file__).parent
SALIDA = AQUI / "dataset_groserias.csv"

META = {"insulto": 3000, "groseria": 2300, "odio": 700, "amenaza": 800, "limpio": 3600}
TOTAL = sum(META.values())  # 10,400

# ---------------------------------------------------------------------------
# Vocabulario curado a mano
# ---------------------------------------------------------------------------
NOMBRES = [
    "Pepe", "Luna", "Toño", "Majo", "Beto", "Sofi", "Rafa", "Dani", "Chuy", "Vale", "Memo", "Lupita",
    "Iker", "Fer", "Santi", "Ximena", "Paco", "Regi", "Emi", "Lalo", "Kevin", "Ale", "Nico", "Pau",
    "Gael", "Carlitos", "Brayan", "Diego", "Mari", "Leo", "Fátima", "Joaquín", "Camila", "Mateo",
    "Renata", "Ulises", "Abril", "Octavio", "Citlali", "Axel", "Yolanda", "Rodrigo", "Tere", "Hugo",
    "RataVeloz", "ReyQueso", "Quesito_07", "Bigotes", "Colita", "xXSombraXx", "Tubería99", "MiniPau",
    "Sombra_22", "Gris", "Pelusa", "Orejas", "Cacahuate", "Chispa",
]

INS_M = [
    "pendejo", "idiota", "imbécil", "estúpido", "culero", "cabrón", "mamón", "baboso", "menso", "tarado",
    "inútil", "retrasado", "naco", "gilipollas", "payaso", "perdedor", "malparido", "pendejazo", "tonto",
    "bruto", "puto", "maricón", "joto", "cerdo asqueroso", "zopenco", "pendejete", "capullo", "huevón",
    "pelotudo", "boludo", "ojete", "cretino", "zonzo", "lerdo", "fracasado", "desgraciado", "hijo de puta",
    "idiota de primera", "menso de remate", "culero de lo peor", "imbécil integral", "cabrón sin remedio",
]
INS_F = [
    "pendeja", "idiota", "imbécil", "estúpida", "culera", "cabrona", "mamona", "babosa", "mensa", "tarada",
    "inútil", "retrasada", "naca", "payasa", "perdedora", "tonta", "bruta", "perra", "zorra", "puta", "cerda",
    "pendejaza", "malparida", "huevona", "cretina", "zonza", "lerda", "fracasada", "desgraciada", "ojete",
]
INS_ADJ = [
    "pendejo", "idiota", "imbécil", "estúpido", "culero", "mamón", "baboso", "menso", "tarado", "inútil",
    "retrasado", "naco", "tonto", "bruto", "pendeja", "estúpida", "mensa", "tarada", "culera", "mamona",
    "tonta", "cabrón", "huevón", "pelotudo", "cretino", "zonzo", "lerdo", "mamona", "babosa", "inútil",
]
INS_SUST = ["basura", "mierda", "escoria", "lacra", "porquería", "vergüenza", "asco de persona", "plaga", "mugre"]
INS_FRASES = [
    "hijo de puta", "hija de puta", "hijo de tu puta madre", "chinga tu madre", "vete a la verga", "vete a la mierda",
    "vete al carajo", "pinche pendejo", "pendejo de mierda", "cara de verga", "come mierda", "pinche culero",
    "pinche pendeja", "maldito idiota", "estúpido de mierda", "me das asco", "muérete de una vez", "nadie te quiere",
    "tu mamá es una puta", "hdp", "ctm", "vtalv", "chingada madre contigo", "eres un asco", "pinche naco",
    "que te jodan", "jódete", "pinche gordo asqueroso", "ojalá te baneen, imbécil", "eres un estorbo y un idiota",
    "bola de pendejos", "puros culeros en este equipo", "qué par de imbéciles", "pinches inútiles todos",
]
GAMER = [
    "por tu culpa perdimos", "otra vez te moriste", "ni para eso sirves", "juegas horrible", "aprende a jugar",
    "deja de llorar", "nadie te pidió tu opinión", "cierra la boca", "no hables", "lárgate de aquí",
    "sal del juego", "eres el peor del servidor", "ya cállate", "cállate", "no sabes ni caminar",
    "arruinaste la partida", "eres una carga para el equipo", "mejor desinstala el juego", "qué mal juegas",
    "no sirves en equipo", "perdimos por ti", "me haces perder el tiempo",
]
BUENOS_M = [
    "crack", "genio", "campeón", "máquina", "buen amigo", "profesional", "maestro", "ídolo", "capo", "experto",
    "ganador", "artista", "chistoso", "nuevo", "ñoño", "bailarín", "fan del queso", "buen compañero", "héroe",
    "loquillo", "dormilón", "friolento", "goloso", "valiente", "rápido", "listo", "mejor jugador",
]
BUENOS_F = [
    "crack", "genia", "campeona", "máquina", "buena amiga", "profesional", "maestra", "experta", "ganadora",
    "artista", "chistosa", "nueva", "ñoña", "bailarina", "buena compañera", "heroína", "dormilona", "friolenta",
    "valiente", "rápida", "lista", "mejor jugadora",
]
SUELTAS = [
    "hola", "sí", "no", "va", "adiós", "queso", "frío", "fiesta", "túnel", "gracias", "jaja", "sale", "vale",
    "obvio", "claro", "órale", "porfa", "ya", "bailar", "correr", "aquí", "allá", "mande", "bueno", "perdón",
    "quién", "dónde", "pizza", "tacos", "helado", "música", "azul", "rojo", "verde", "morado", "rosa", "nadar",
    "tubería", "madriguera", "bigotes", "cola", "mañana", "hoy", "después", "ahorita",
]
ODIO_PAL = [
    "joto", "marica", "maricón", "puto", "mayate", "sudaca", "negrata", "tortillera", "machorra", "travelo",
    "marimacha", "sidoso", "mariquita", "jotito", "maricón de mierda", "puñal", "jota", "trolo",
]
GRUPOS = [
    "los negros", "los gays", "las lesbianas", "los judíos", "los musulmanes", "los indios", "los inmigrantes",
    "los homosexuales", "los trans", "los extranjeros", "los árabes", "los gitanos",
]
AMENAZAS = [
    "te voy a violar", "te voy a matar", "voy a violarte", "voy a matarte", "te vamos a matar", "te vamos a violar",
    "te voy a asesinar", "te voy a golpear", "te voy a partir la madre", "te voy a romper la cara",
    "ojalá te mueras", "ojalá te mates", "ojalá te violen", "muérete", "mátate", "suicídate", "vete a morir",
    "te vas a morir", "mereces morir", "te voy a reventar", "te voy a degollar", "voy a violar a tu hermana",
    "voy a matar a tu mamá", "voy a violar a tu mamá", "te voy a secuestrar", "te voy a dar una paliza",
    "te voy a dar una madriza", "sé dónde vives", "sabemos dónde vives", "te voy a quemar", "te voy a disparar",
    "te voy a apuñalar", "te van a violar", "te van a matar", "voy a ir por ti", "te voy a torturar",
    "ojalá te atropellen", "ojalá te caigas y te mueras", "te mato", "te violo", "te voy a ahorcar",
    "te voy a estrangular", "voy a matar a todos", "te voy a buscar para matarte", "ojalá se muera tu familia",
    "voy a encontrar tu casa y te voy a matar", "te voy a dejar tirado y sin dientes",
]

# Groserías "casuales" (amistosas o de desahogo): también se censuran
EXPR_GROS = [
    "qué chingón", "qué chingona", "está cabrón", "está bien cabrón", "no mames", "a huevo", "me vale madre",
    "qué pedo", "está de poca madre", "ni madres", "a la madre", "qué poca madre", "está chingón",
    "qué cabrón", "qué verga", "está de huevos", "qué padre y chingón",
]
CONTEXTO_GROS = [
    "tu jugada", "el nivel", "ese salto", "la partida", "este queso", "el servidor", "tu madriguera", "el mapa nuevo",
    "cómo corres", "tu color", "esa idea", "cómo bailas", "el boss final", "tu disfraz", "esa estrategia",
    "lo que hiciste", "este juego", "tu rata", "cómo suena la música", "la pizza de ayer",
]
PINCHE_N = [
    "lag", "juego", "internet", "servidor", "tubería", "hambre", "sueño", "suerte", "calor", "mapa", "frío",
    "queso", "sala", "escuela", "tarea", "examen", "tráfico", "celular", "pila", "wifi", "jefe final",
]
EVENTOS = [
    "se cayó el servidor", "perdí otra vez", "se me fue el internet", "me quedé sin vidas", "se acabó el queso",
    "me sacaron de la sala", "se me borró el progreso", "me atrapó el gato", "no encuentro la salida",
    "se trabó el juego", "me quedé sin batería", "llegué tarde a la partida", "me ganaron por un segundo",
]
COSAS_MALAS = ["lag", "internet", "servidor", "wifi", "tarea", "trabajo", "juego", "sueño", "examen"]

# Variaciones de superficie
PREF = ["", "", "", "", "oye ", "güey ", "neta ", "jajaja ", "ay ", "ya ", "órale ", "mira ", "la neta ",
        "compa ", "banda ", "carnal ", "oigan ", "hey ", "uy ", "pues ", "o sea ", "mano ", "amigo ", "mi rey "]
SUF = ["", "", "", "", "!", "!!", " jaja", " 🤡", " 😂", "...", " xd", " ya vete", " jajaja", " 😡", " 🙄", " pues",
       ", en serio", " la verdad", " ¿no?", " 😤", " ahorita", " de una vez", " y ya"]
SUF_SUAVE = ["", "", "", "!", " jaja", " 😂", "...", " xd", " 😎", " jajaja", " 🔥", " 👏", " :D"]


# ---------------------------------------------------------------------------
# Moldes (plantillas)
#   {m}/{m2} insulto masculino  {f} insulto femenino   {a}/{a2} adjetivo   {s} sustantivo
#   {p} frase insultante        {g} reclamo gamer      {n}/{n2} nombre
#   {h}/{h2} palabra de odio    {gr} grupo             {t}/{t2} amenaza
#   {x} expresión grosera casual   {c} contexto  {pn} "pinche ___"  {e} evento  {cm} cosa mala
#   {bm}/{bf} cumplidos o cosas neutras   {w}/{w2} palabra suelta
# ---------------------------------------------------------------------------
PLANTILLAS_INSULTO = [
    # directos y cortos
    "eres un {m}", "eres una {f}", "eres bien {a}", "qué {m} eres", "qué {f} eres", "{m}", "{f}",
    "cállate {m}", "cállate {f}", "ya cállate {m}", "pinche {m}", "pinche {f}", "{m} de mierda", "{f} de mierda",
    "lárgate {m}", "lárgate de aquí {f}", "vete de aquí {f}", "no seas {a}", "pareces {m}", "{m}, {p}",
    "{p}", "{p} {n}", "{n} {p}", "{m} {m2}", "eres un {m} y un {m2}",
    # tercera persona
    "{n} es un {m}", "{n} es una {f}", "{n} eres un {m}", "{n} eres una {f}", "{n} es el más {a} del equipo",
    "{n} es bien {a}", "{n} es una {s}", "{n} siempre ha sido un {m} con todos", "no inviten a {n}, es un {m}",
    "no le hagan caso a {n}, es bien {a}", "{n} y {n2} son unos {m} los dos",
    # familia y ataques
    "tu mamá es una {f}", "tu hermana es una {f}", "tu jefa es una {f}", "tu papá es un {m}",
    "toda tu familia es una bola de {m}s",
    # gamer
    "{g} {m}", "{g} {f}", "{n} {g}, {m}", "{g}, eres un {m}", "{g}, {p}", "no sirves para nada {m}",
    "hasta mi abuela juega mejor que tú {m}", "eres el más {a} del servidor", "eres una {s} de persona",
    "eres una {s}", "qué asco me das {m}",
    # narrativos y largos
    "la verdad es que eres un {m} y todos lo saben", "te juro que eres el {m} más grande del juego",
    "nunca he visto a alguien tan {a}", "en mi vida había conocido a alguien tan {a} como tú",
    "no puedo creer lo {a} que eres", "de todos los del servidor tú eres el más {a}",
    "cada día estás más {a} {n}", "ayer te vi jugar y la neta eres un {m}", "me pareces un {m}, lo digo en serio",
    "después de lo que hiciste en la partida confirmo que eres un {m}", "llevo una hora jugando contigo y solo veo a un {m}",
    "no entiendo cómo alguien puede ser tan {a} como tú", "si hubiera un premio al más {a}, ya sería tuyo {m}",
    "mi hermano dice que eres un {m} y tiene razón", "todos en el chat piensan que eres un {m}",
    # preguntas
    "¿por qué eres tan {a}?", "¿eres {a} o te haces?", "¿siempre has sido así de {a}?", "¿de verdad eres tan {m}?",
    "¿quién invitó a este {m}?", "¿alguien puede sacar a este {m}?", "¿cuándo vas a dejar de ser un {m}?",
    # formales o "educados" pero insultantes
    "con todo respeto, eres un {m}", "disculpa que te lo diga, pero eres un {m}", "usted es un {m}, señor {n}",
    "lamento informarte que eres un {m}", "perdón por la sinceridad, eres bien {a}",
    # órdenes y reacciones
    "mejor ya vete {m}", "eres un {m} de verdad", "nadie te quiere aquí {m}", "neta eres bien {a} {n}",
    "cállate {m}, nadie te habla", "jaja qué {m} eres {n}", "qué {a} estás {n}", "qué {m} tan {a2}",
    "quítate de aquí {m}", "deja de estorbar {m}", "pinche {m} aprende a jugar", "ya bájale {m}",
    "qué asco de jugador, {m}", "juegas como un {m}", "{n}, eres un {m}", "ay qué {a} eres",
    "uy qué {m}", "pinche {m} y {f}", "los dos son unos {m}", "bola de {m}s",
]

PLANTILLAS_GROSERIA = [
    # expresiones casuales con contexto
    "{x} {c}", "{x} {c} {n}", "{n}, {x} {c}", "{x} {c}, la neta", "jaja {x} {c}", "oye {x} {c}",
    "{x}, {c} está increíble", "la verdad {x} {c}", "{x} {c} jajaja",
    # pinche + sustantivo
    "pinche {pn}", "pinche {pn} otra vez", "ya estoy harto del pinche {pn}", "otra vez el pinche {pn}",
    "qué pinche {pn} tenemos hoy", "{n}, no soporto el pinche {pn}", "maldito {pn}, perdí por el pinche {pn}",
    # desahogo ante eventos
    "verga, {e}", "puta madre, {e}", "ptm, {e}", "me lleva la verga, {e}", "chingada madre, {e}", "vale madre, {e}",
    "ay cabrón, {e}", "no mames, {e}", "qué poca madre, {e}", "ni madres, {e}", "uta madre, {e}", "a la verga, {e}",
    "mierda, {e}", "carajo, {e}", "pinche vida, {e}", "alv, {e}", "me lleva el diablo, {e}",
    "{e} y me vale madre", "{e}, qué pinche rollo", "{e}, qué mierda",
    # elogios y bromas con groserías
    "eres bien chingón {n}", "eres un chingón jugando {n}", "estás cabrón jugando {n}", "{n} es una chingona",
    "me cae que eres bien vergas {n}", "qué cabrón eres para bailar {n}", "eres bien cabrón para los minijuegos",
    "ah qué cabrón, sí te salió", "eres un pinche genio {n}", "qué pinche miedo", "no mames te pasaste de chido",
    "qué chingona rata eres {n}", "{n} qué chingón tu escondite", "me vale madre, vamos a jugar",
    "vamos a darles en la madre", "a huevo, ganamos", "a huevo {n}, lo logramos", "a huevo encontré el queso",
    "está bien vergas tu madriguera", "qué verga tan buena idea",
    # quejas con groserías
    "la neta está culero el {cm}", "qué culero, se cerró el juego", "vale verga el {cm}", "ya me cansé de esta mierda de {cm}",
    "qué pendejada hice jaja", "soy bien pendejo para esto jaja", "me caí como pendejo jaja", "qué pendejada de nivel",
    "no mames, ya es tarde", "no mames {n}, qué rápido", "no mames qué buena jugada", "ya valió madre la partida",
    "está de poca madre el juego", "alv ya me voy a dormir", "qué pedo banda", "qué pedo {n}",
    "me vale madre perder, igual me divierto", "puta, se me fue el turno", "verga, me asustaste",
    "chingue a su madre el {cm}", "ah cabrón, qué buena idea", "uy cabrón ya son las once",
    "pinche queso está bien rico", "verga, qué asco huele aquí jaja", "está cabrón encontrar queso",
    # registros distintos
    "perdón por la expresión pero qué chingón estuvo todo", "disculpen mi lenguaje, pero ese nivel está cabrón",
    "con permiso, no mames qué bonito mapa", "mi mamá me regañaría por decir esto, pero qué cabrón juego",
    "en la escuela diría otra cosa, pero aquí digo que está de huevos", "hoy amanecí con ganas de decir puras groserías, ptm",
    "jajaja no mames, me caí del tubo", "qué chingón se siente ganar, no mames", "ándale cabrón, sí se pudo",
    "órale pinche {n}, qué buena rata", "échale ganas cabrón, tú puedes", "qué pedo con este nivel tan difícil",
]

PLANTILLAS_ODIO = [
    "eres un {h}", "eres bien {h}", "qué {h} eres", "{h}", "cállate {h}", "{n} es un {h}", "{n} eres un {h}",
    "pinche {h}", "ya cállate {h}", "no seas {h}", "todos los del equipo son unos {h}", "qué {h} tan asqueroso",
    "{n} es un {h} y todos lo saben", "jaja {h}", "jajaja eres {h} {n}", "hola {h}", "qué onda {h}", "quítate {h}",
    "lárgate de aquí {h}", "eres un {h} de mierda", "{h} de mierda", "vete {h}", "oye {h} ven acá",
    "odio a {gr}", "odiamos a {gr}", "mueran {gr}", "{gr} de mierda", "qué asco {gr}", "{gr} no deberían existir",
    "{gr} son basura", "este chat es para gente normal, no para {gr}", "fuera {gr} de este servidor",
    "eres un {h} {n}", "{n} {h}", "bien {h} tu amigo", "no juego con {h}", "{h} {h2}",
    "no quiero equipo con {h} como tú", "aquí no queremos {h}", "{n}, deja de ser tan {h}",
    "{gr} arruinan todo, qué asco", "hay que sacar a {gr} del juego", "pinche {h} y su amigo {h2}",
    "dicen que {n} es {h}, qué asco", "no me caen bien {gr}", "todo sería mejor sin {gr}",
]

PLANTILLAS_AMENAZA = [
    "{t}", "{t} {n}", "{n} {t}", "{t} idiota", "oye {t}", "{t} {t2}", "{t}, lo juro", "jajaja {t}", "neta {t}",
    "{t} en la vida real", "{t} cuando te encuentre", "te lo advierto, {t}", "{t} cuando salgas del juego",
    "si vuelves a hablar {t}", "{n}, {t}", "{t} pinche {m}", "ya verás, {t}", "cuidado porque {t}", "{t} {n} jaja",
    "{t} y nadie se va a enterar", "{t} cuando te vea", "no estoy jugando: {t}", "escúchame bien {n}, {t}",
    "ya me tienes harto, {t}", "última advertencia, {t}", "por tu culpa perdimos, {t}", "te lo digo en serio, {t}",
    "{t} si no te sales de la sala", "{t}, no es broma", "mañana en la escuela {t}", "{t} y vas a lamentarlo",
    "cuando te encuentre solo, {t}", "{n}: {t}", "{t} por lo que dijiste", "pasa tu dirección o {t}",
    "{t}. Ya lo decidí", "me cansé de ti, {t}",
]

PLANTILLAS_LIMPIO = [
    # --- casos trampa: palabras parecidas a insultos o a groserías ---
    "voy a violar las reglas jaja no es cierto", "no hay que violar las reglas del juego", "violar las normas te puede banear",
    "mi perra se llama {n}", "mi perra tuvo cachorros", "la perra de mi vecino ladra mucho", "vi una zorra en el bosque",
    "mi perra {n} es bien juguetona", "la zorra del zoológico estaba dormida", "adoptamos una perrita muy tierna",
    "Maricela es mi amiga", "hola Maricela", "Maricela ven acá", "mi prima Maricarmen juega aquí", "Vergara es mi apellido",
    "el señor Vergara es mi maestro", "mi computadora está nueva", "la computadora se trabó", "mi mamá me llama", "mi madre cocina rico",
    "te voy a reportar con el moderador", "te voy a reportar si sigues así", "qué asco de clima hoy", "qué asco de comida jaja",
    "qué maldición, se me cayó el queso", "te voy a dar mi número de nivel", "dame tu usuario para agregarte",
    "te voy a ganar jaja", "te voy a enseñar a jugar", "te voy a ayudar {n}", "te voy a esperar en la madriguera",
    "te voy a invitar queso", "te voy a pasar el mapa", "te voy a mandar un mensaje", "te voy a buscar {n}",
    "te voy a extrañar", "te voy a llevar al túnel", "te voy a contar un secreto", "te voy a regalar mi gorro",
    "voy a matar el tiempo jugando", "voy a golpear la pelota", "voy a cortar el queso", "voy a quemar calorías",
    "voy a romper mi récord", "voy a pegar el cartel en la pared", "mato el tiempo viendo videos", "voy a partir la pizza",
    "voy a matar el aburrimiento con un juego", "voy a quemar la basura del patio", "hoy voy a romper la alcancía",
    "el cabrito está rico", "el cabrito asado está rico", "el verde es mi color favorito", "hay que decir la verdad",
    "me da vergüenza hablar", "mañana tengo examen de verano", "hay un huevo en el queso", "huevos revueltos de desayuno",
    "el chino es un idioma difícil", "tengo un amigo chino muy buena onda", "mi amigo negro es muy bueno jugando",
    "mi vecino gay es muy buena onda", "mi tía lesbiana me regaló un gorro", "los judíos celebran hanuká",
    "respeto a todas las personas", "todos somos iguales", "no a la discriminación", "el bullying está mal",
    "no hay que insultar a nadie", "aquí no se permiten insultos", "sé amable con todos", "el pedido llegó rápido",
    "pedro es mi hermano", "tengo que pedir permiso", "el pinchazo de la vacuna no dolió", "me comí un pincho de queso",
    "el mamífero más grande es la ballena", "mi mamá es doctora", "pienso que está bien", "la tarea de matemáticas estuvo larga",
    "mi computadora está lenta", "tengo una disputa con mi hermano por la tele", "eso estuvo estupendo",
    "estoy pendiente de la partida", "mi perro se llama Max", "vi un zorro en el bosque", "el cerdo de la granja está gordo",
    "hay que tirar la basura", "estoy estudiando idiomas", "la reputación del clan es buena", "mi mamá me está llamando",
    "hice un pastel de pera", "el chiste estuvo bien tonto jaja", "no seas tímido {n}", "la película estuvo de miedo",
    "el diputado dio un discurso largo", "el vehículo se descompuso en la esquina", "qué espectáculo tan bonito",
    "el músculo del brazo me duele", "el círculo de amigos del club es chico", "tengo que estudiar para el examen de cálculo",
    "el pitufo azul sale en mi caricatura favorita", "Pitágoras fue un matemático griego", "la cojinería de mi casa es nueva",
    "compré un cojín muy suave", "el pájaro se comió mi queso", "la culebra se escondió en la tubería",
    "la cultura mexicana es muy rica", "no es mi culpa, fue el lag", "el pastel de verduras estuvo rico",
    "la tarjeta de regalo llegó hoy", "me gusta la tarde cuando llueve", "mi tarea de química estuvo difícil",
    "la mamá de {n} trajo pastel", "mamá dice que ya es hora de cenar", "estudio historia de la cultura china",
    "el Dalai Lama es un líder religioso", "mi amigo judío me invitó a su cena", "mi amiga musulmana celebra el Ramadán",
    "mi tío es trans y lo queremos mucho", "dos de mis mejores amigos son gays y los quiero", "mi compañera lesbiana ganó el concurso",
    "los inmigrantes aportan mucho a la ciudad", "no hay que odiar a nadie por cómo es", "la violencia nunca es la solución",
    "me preocupa el bullying en la escuela", "dicen que insultar a otros no está bien", "hay que denunciar el acoso",
    "ayer vi un documental sobre la discriminación", "si alguien te amenaza, avisa a un adulto", "reportar a quien insulta ayuda mucho",
    # --- saludos, juego y conversación normal ---
    "hola a todos", "hola {n}", "¿qué onda {n}?", "buenas noches banda", "buenos días", "buenas tardes a todos",
    "¿alguien quiere jugar?", "vamos a la madriguera", "¿dónde es la fiesta?", "me gusta tu color {n}",
    "buena partida", "bien jugado {n}", "eres muy bueno {n}", "eres bien buena onda {n}", "eres un crack {n}",
    "{n} eres una crack", "qué divertido", "jajaja", "¿de dónde eres?", "me voy a cenar", "ahorita regreso",
    "bailemos todos", "qué bonita está la alcantarilla", "¿cómo se juega?", "ayúdame por favor", "gracias {n}",
    "de nada", "perdón, me equivoqué", "nos vemos mañana", "adiós banda", "¿quién quiere ser mi amigo?",
    "{n} ven acá", "sígueme {n}", "me encanta este juego", "tu nombre está bien chistoso {n}",
    "felicidades {n}", "feliz cumpleaños {n}", "qué calor hace", "¿cuántos años llevas jugando?",
    "corran a la coladera", "ya llegué", "te extrañamos {n}", "{n} eres mi mejor amigo", "¿alguien vio a {n}?",
    "me caes bien {n}", "qué padre tu nombre {n}", "no entiendo nada jaja", "¿hay alguien aquí?",
    "vamos por queso", "ya me voy a dormir", "mañana tengo escuela", "¿qué hora es?", "hoy comí tacos",
    "mi gato está dormido", "¿qué música te gusta?", "me gusta el reguetón", "vamos a la tienda",
    "¿cuántos puntos llevas?", "subí de nivel", "encontré un tesoro", "hay un charco en el túnel",
    "me cambié de color", "¿quién es el más rápido?", "el más rápido gana", "corre {n}", "espérame {n}",
    "no encuentro la salida", "¿dónde estás {n}?", "ya voy", "aquí estoy", "llegué primero", "qué buena idea",
    "tienes razón {n}", "estoy de acuerdo", "no sé", "a lo mejor", "puede ser", "mi hermana también juega",
    "mi primo me enseñó este juego", "la maestra nos dejó mucha tarea", "el sábado es mi cumpleaños",
    "voy a hacer mi tarea", "¿alguien sabe la respuesta?", "es el mejor juego del mundo", "la peor parte es esperar",
    "el peor día fue ayer porque llovió", "la persona más chistosa es {n}", "cada día está más bonito el juego",
    "no puedo creer que ganamos", "te juro que vi una paloma gigante", "soy una rata feliz",
    "qué bonita rata eres {n}", "mi rata es la más rápida", "encontré queso en la tubería", "¿quién quiere queso?",
    "eres una rata muy chistosa {n}", "las ratas somos las mejores", "cuidado con el agua", "huele a queso aquí",
    "mi rata es gris", "me gusta tu cola {n}", "qué orejas tan grandes tienes {n}", "viva la rata veloz",
    "vamos al túnel", "ratas unidas", "soy la rata más rápida", "{n} es una ratita bien buena onda", "ratita linda",
    "hola ratas", "buenas noches ratitas", "¿alguien vio el queso?", "hagamos una fiesta de ratas", "se escucha el agua",
    "qué rata tan bonita",
    # --- cumplidos con el mismo molde que los insultos ---
    "eres un {bm}", "eres una {bf}", "eres un {bm} {n}", "{n} eres una {bf}", "{n} es un {bm}", "{n} es una {bf}",
    "qué {bm} eres", "eres bien {bm}", "eres el más {bm} del servidor", "eres un {bm} jaja", "{n}, eres un {bm}",
    "la verdad es que eres un {bm} y todos lo saben", "te juro que eres el {bm} más grande del juego",
    "¿por qué eres tan {bm}?", "con todo respeto, eres un {bm}", "mi hermano dice que eres un {bm}",
    "ayer te vi jugar y la neta eres un {bm}", "todos en el chat piensan que eres un {bm}",
    "{n} siempre ha sido un {bm} con todos", "no inviten a {n}, es un {bm}",
    # --- palabras sueltas y mensajes cortos ---
    "{n}", "{n}!", "{w}", "{w} {n}", "{n} {w}", "{w} {w2}", "jaja {n}", "@{n}",
    "te mando saludos {n}", "te quiero mucho amigo", "te veo en la fiesta", "te espero en el túnel", "te ayudo {n}",
    "te sigo", "te invito a mi madriguera", "te gané jaja", "te presto mi gorro", "te extraño {n}", "te cuento un chiste",
    "te va a gustar el mapa nuevo", "te dejo, me voy a bañar", "¿te puedo agregar de amigo?", "¿te acuerdas de la fiesta?",
    "no te vayas {n}", "te pasaste de buena onda",
    # --- registros distintos: formal, narrativo, con preguntas ---
    "buen día, quisiera saber cómo se desbloquea el siguiente nivel", "disculpen, ¿alguien me explica cómo funciona el chat?",
    "agradezco mucho la ayuda de todos en la partida", "con permiso, voy a cambiar de sala un momento",
    "ayer terminé mi tarea y después jugué una hora con mis primos", "mi mamá dice que ya me desconecte, nos vemos luego",
    "hoy en la escuela hicimos un experimento con queso y fue divertidísimo", "me costó mucho llegar al último nivel pero lo logré",
    "¿alguien sabe si el servidor se reinicia a medianoche?", "¿cómo hago para cambiar el color de mi rata?",
    "creo que hoy hay muchos jugadores nuevos, qué bien", "propongo que hagamos una carrera hasta el fondo del túnel",
    "estoy aprendiendo a programar y me gusta mucho", "mañana tengo exposición y estoy nerviosa", "qué cansado estoy después del examen",
    "acabo de ver que {n} subió de nivel, felicidades", "si quieren, les paso el truco para el nivel tres",
    "ya casi termino la tarea, espérenme tantito", "no me salió bien pero lo intento otra vez", "me dio mucha risa tu mensaje {n}",
    "k onda {n}, ya llegaste?", "q bueno q viniste hoy", "xq no me contestas {n}", "ntp, a todos nos pasa", "wenas noches a todos",
]


# ---------------------------------------------------------------------------
# Transformaciones (para que el modelo vea variantes reales de escritura)
# ---------------------------------------------------------------------------
LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"}


def leet(palabra):
    return "".join(LEET.get(c, c) if random.random() < 0.6 else c for c in palabra)


def alargar(palabra):
    vocales = [i for i, c in enumerate(palabra) if c in "aeiou"]
    if not vocales:
        return palabra
    i = vocales[-1]
    return palabra[: i + 1] + palabra[i] * random.randint(2, 5) + palabra[i + 1:]


def separar(palabra):
    return random.choice([".", "-", "*", " ", "_"]).join(palabra)


def sin_acentos(t):
    return t.translate(str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU"))


def disfrazar(palabra):
    """Aplica a una palabra ofensiva alguna forma de esquivar un filtro."""
    r = random.random()
    if r < 0.12:
        return leet(palabra)
    if r < 0.24:
        return alargar(palabra)
    if r < 0.30 and " " not in palabra and len(palabra) <= 8:
        return separar(palabra)
    if r < 0.36:
        return palabra.upper()
    return palabra


def faltas(t):
    """Errores de escritura comunes en chats: 'que'->'ke', 'porque'->'xq', sin signos, letras comidas."""
    reemplazos = [("que ", "ke "), ("qué ", "ke "), ("porque", "xq"), ("para ", "pa "), ("también", "tmb"),
                  ("¿", ""), ("?", ""), ("¡", ""), ("eres", "eres"), ("pero", "pero"), ("hacer", "acer")]
    for a, b in random.sample(reemplazos, 3):
        t = t.replace(a, b)
    if len(t) > 8 and random.random() < 0.5:
        i = random.randrange(1, len(t) - 1)
        if t[i].isalpha():
            t = t[:i] + t[i + 1:]
    return t


def estilo_global(t):
    r = random.random()
    if r < 0.06:
        return t.upper()
    if r < 0.30:
        t = t[:1].upper() + t[1:]
    elif r < 0.45:
        t = sin_acentos(t)
    elif r < 0.55:
        t = faltas(t)
    elif r < 0.60:
        t = t.lower()
    if random.random() < 0.05:
        t = t.rstrip(".!?") + random.choice(["!!!", "??", "?!", "..."])
    return t


def rellenar(plantilla, disfraz):
    d = disfrazar if disfraz else (lambda x: x)
    m, m2 = random.sample(INS_M, 2)
    a, a2 = random.sample(INS_ADJ, 2)
    n, n2 = random.sample(NOMBRES, 2)
    valores = {
        "m": d(m), "m2": d(m2), "f": d(random.choice(INS_F)), "s": d(random.choice(INS_SUST)),
        "p": d(random.choice(INS_FRASES)), "g": random.choice(GAMER), "n": n, "n2": n2,
        "bm": random.choice(BUENOS_M), "bf": random.choice(BUENOS_F),
        "w": random.choice(SUELTAS), "w2": random.choice(SUELTAS),
        "h": d(random.choice(ODIO_PAL)), "h2": d(random.choice(ODIO_PAL)), "gr": random.choice(GRUPOS),
        "t": random.choice(AMENAZAS), "t2": random.choice(AMENAZAS),
        "a": d(a), "a2": d(a2),
        "x": d(random.choice(EXPR_GROS)), "c": random.choice(CONTEXTO_GROS), "pn": random.choice(PINCHE_N),
        "e": random.choice(EVENTOS), "cm": random.choice(COSAS_MALAS),
    }
    return plantilla.format(**valores)


def generar(plantillas, tipo, meta, disfraz):
    vistos, filas = set(), []
    intentos = 0
    sufijos = SUF_SUAVE if tipo in ("limpio",) else SUF
    while len(filas) < meta and intentos < meta * 200:
        intentos += 1
        pid = random.randrange(len(plantillas))
        texto = random.choice(PREF) + rellenar(plantillas[pid], disfraz) + random.choice(sufijos)
        texto = estilo_global(texto.strip())
        if texto.lower() in vistos:
            continue
        vistos.add(texto.lower())
        filas.append({
            "texto": texto,
            "etiqueta": 0 if tipo == "limpio" else 1,
            "tipo": tipo,
            "plantilla": f"{tipo[:3]}-{pid:03d}",
        })
    if len(filas) != meta:
        raise RuntimeError(f"No se pudieron generar {meta} frases únicas de tipo {tipo} (solo {len(filas)}).")
    return filas


def main():
    random.seed(SEMILLA)
    filas = []
    filas += generar(PLANTILLAS_INSULTO, "insulto", META["insulto"], disfraz=True)
    filas += generar(PLANTILLAS_GROSERIA, "groseria", META["groseria"], disfraz=True)
    filas += generar(PLANTILLAS_ODIO, "odio", META["odio"], disfraz=True)
    filas += generar(PLANTILLAS_AMENAZA, "amenaza", META["amenaza"], disfraz=False)
    filas += generar(PLANTILLAS_LIMPIO, "limpio", META["limpio"], disfraz=False)
    random.shuffle(filas)

    # Un mismo texto no puede tener dos etiquetas distintas
    por_texto = {}
    for x in filas:
        por_texto.setdefault(x["texto"].lower(), set()).add(x["etiqueta"])
    conflictos = [t for t, e in por_texto.items() if len(e) > 1]
    if conflictos:
        raise RuntimeError(f"Frases con etiquetas contradictorias: {conflictos[:5]}")
    assert len(filas) == TOTAL, (len(filas), TOTAL)

    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["texto", "etiqueta", "tipo", "plantilla"])
        w.writeheader()
        w.writerows(filas)
    caracteres = sum(len(x["texto"]) for x in filas)
    plantillas = len({x["plantilla"] for x in filas})
    print(f"Dataset escrito en {SALIDA.name}: {len(filas)} frases, {caracteres:,} caracteres, {plantillas} plantillas")
    for t in META:
        print(f"  {t:10s} {sum(1 for x in filas if x['tipo'] == t)}")


if __name__ == "__main__":
    main()
