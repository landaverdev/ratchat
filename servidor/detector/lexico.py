"""
Léxico de RatChat: listas de palabras y frases que el sistema conoce.

El detector usa cuatro categorías:

  GROSERÍAS  palabras altisonantes. Se censuran SIEMPRE, en cualquier contexto
             (ofensivo o amistoso): "qué chingón", "pinche lag", "eres un pendejo".
  ODIO       insultos discriminatorios (joto, marica, ...). Se censuran SIEMPRE.
  AMENAZAS   frases como "te voy a violar" o "te voy a matar". Se censuran SIEMPRE.
  CONTEXTO   palabras que a veces son insulto y a veces no ("tonto", "perra"):
             solo se censuran si el contexto lo indica (reglas simples + modelo de IA).

El modelo de IA (TF-IDF + regresión logística) cubre lo que el léxico no conoce:
insultos con palabras nuevas, faltas de ortografía, frases ofensivas completas.

Todo se escribe ya normalizado (minúsculas, sin acentos). Cada letra acepta repeticiones,
así "puta" también encuentra "putaaaa".
"""

import re

# ---------------------------------------------------------------------------
# 1) Groserías y palabras altisonantes (siempre se censuran)
# ---------------------------------------------------------------------------
# Raíces: cualquier palabra que EMPIECE así (pendejo, pendeja, pendejazo, pendejadas...)
RAICES_GROSERIAS = [
    "pendej", "idiot", "imbecil", "estupid", "culer", "gilipoll", "retrasad", "malparid",
    "cabron", "mamon", "mamad", "babos", "tarad", "zopenc", "pndj", "ching", "verg", "mierd",
    "putaz", "putit", "puter", "pinch", "jodid", "joder", "jodan", "jodete", "cojon", "hijueputa",
    "hijoeputa", "hijodeputa", "huevon", "pelotud", "pajero", "cagad", "cagon", "culiad",
    "putisima", "chupapij", "mrd", "mamast", "mamaste",
]

# Palabras completas (aceptan plurales y diminutivos: puta -> putas, putita)
GROSERIAS = [
    "puto", "puta", "verga", "vrga", "chingon", "chingona", "carajo", "culo", "joto", "hdp",
    "ctm", "vtalv", "alv", "ptm", "hptm", "mierda", "hostia", "ostia", "gonorrea", "ctmr", "pirobo", "marica",
    "maricon", "mariquita", "punal", "pinche", "naco", "naca", "menso", "mensa", "cabron",
    "cabrona", "pendejo", "chingue", "chingas", "chinga", "chingar", "chingo", "chingada",
    "chingado", "chingadera", "ojete", "cojones", "boludo", "pelotudo", "bastardo", "bastarda",
    "cono", "coño", "cagada", "mamada", "mamadas",
]

# Palabras normales que chocan con alguna raíz (se dejan pasar)
_NORMALES = {
    "chino", "chinos", "china", "chinas", "chinche", "chincheta", "chinchilla", "chingolo",
    "verde", "verdes", "verdad", "verdades", "verdura", "verduras", "verdadero", "verdadera",
    "verguenza", "vergara", "vergel", "vergeles", "verano", "version", "versiones", "verso",
    "versos", "verse", "vergonzoso",
    "pinchazo", "pincho", "pinchos", "pinchar", "pinchito",
    "tarde", "tardes", "tarea", "tareas", "tarantula", "tarro", "tarjeta", "tarjetas", "tarima",
    "tarot", "tarifa", "tarifas",
    "pajaro", "pajaros", "pajarito", "pajaritos",
    "cojin", "cojines", "cojinete",
    "cabrito", "cabritos", "cabra", "cabras", "cabrero",
}

SUFIJO = r"(?:s|es|ote|otes|ita|itas|ito|itos|a|o|as|os)?"


def _flexible(palabra: str) -> str:
    """'puta' -> 'p+u+t+a+'  (acepta letras repetidas)"""
    return "".join(re.escape(c) + "+" for c in palabra)


_PATRON_RAIZ = re.compile(r"^(?:" + "|".join(_flexible(r) for r in RAICES_GROSERIAS) + r")[a-z]*$")
_PATRON_PALABRA = re.compile(r"^(?:" + "|".join(_flexible(p) for p in GROSERIAS) + r")" + SUFIJO + r"$")

# ---------------------------------------------------------------------------
# 2) Odio: insultos discriminatorios (siempre se censuran)
# ---------------------------------------------------------------------------
ODIO = [
    "joto", "jota", "jotos", "jotito", "marica", "maricon", "maricones", "mariquita", "marico",
    "maricas", "mariconazo", "puñal", "punal", "puto", "putos", "faggot", "fag", "mayate", "mayates",
    "sudaca", "sudacas", "negrata", "negrito de mierda", "nigga", "nigger", "tortillera", "tortilleras",
    "machorra", "marimacha", "travelo", "travelos", "trolo", "trolos", "sidoso", "sidosa",
    "mongolico", "mongolo", "mongol", "subnormal", "retrasado", "retrasada", "retardado", "retardada",
    "invalido", "lisiado", "lisiada", "gabacho de mierda", "indio patarrajada", "naco de mierda",
]
_ODIO_SOLO_CONTEXTO = {"invalido", "mongol", "retardado", "retardada", "lisiado", "lisiada"}
ODIO_PALABRAS = [w for w in ODIO if " " not in w and w not in _ODIO_SOLO_CONTEXTO]
_PATRON_ODIO = re.compile(r"^(?:" + "|".join(_flexible(p) for p in ODIO_PALABRAS) + r")s?$")

# Frases de odio (se buscan sobre el texto normalizado)
FRASES_ODIO = [re.compile(p) for p in [
    r"\b(?:negro|negra|negros|negras|indio|india|indios|chino|china|chinos|judio|judios|moro|moros|gitano|gitanos) de (?:mierda|m|porqueria)\b",
    r"\b(?:odio|odiamos) a (?:los|las) (?:negros|negras|gays|lesbianas|judios|musulmanes|indios|inmigrantes|mexicanos|trans|homosexuales)\b",
    r"\bmueran? (?:los|las) (?:negros|negras|gays|lesbianas|judios|musulmanes|indios|inmigrantes|mexicanos|trans|homosexuales)\b",
    r"\bsucio (?:negro|indio|judio|moro|gitano)\b",
    r"\b(?:eres|es|son|sois) (?:un|una) (?:enfermo|enferma|abominacion|aberracion) (?:gay|trans|homosexual)\b",
    r"\bgays? de mierda\b",
    r"\bhomosexual(?:es)? de mierda\b",
    r"\bheil hitler\b", r"\bviva hitler\b", r"\bsieg heil\b",
]]

# ---------------------------------------------------------------------------
# 3) Amenazas y violencia dirigida
# ---------------------------------------------------------------------------
_VERBOS_AMENAZA = (
    r"viol(?:ar|are|aré|o|are)|mat(?:ar|are|o)|asesin(?:ar|o|are)|golpe(?:ar|are|o)|"
    r"romp(?:er|ere)|cort(?:ar|are)|reventar|partir|apu(?:nalar|nalare)|degoll(?:ar|are)|"
    r"torturar|secuestrar|quemar|disparar|balear|fusilar|ahorcar|estrangular|ahogar|"
    r"pegar|madrear|linchar|acuchillar|matarte|violarte"
)
FRASES_AMENAZA = [re.compile(p) for p in [
    # Futuro perifrástico: "te voy a violar", "te voy a matar", "los voy a golpear"
    rf"\b(?:(?:te|los|las|le|les|lo|la) |te)(?:voy|vamos|van|va) a (?:\w+ ){{0,2}}(?:{_VERBOS_AMENAZA})\b",
    # "voy a violarte", "vamos a matarlos"
    r"\b(?:voy|vamos|van|va) a (?:\w+ ){0,2}(?:violarte|violarlo|violarla|violarlos|violarlas|matarte|matarlo|matarla|matarlos|matarlas|"
    r"asesinarte|asesinarlo|asesinarla|golpearte|golpearlo|golpearla|golpearlos|degollarte|degollarlo|reventarte|reventarlo|"
    r"apunalarte|partirte|romperte|cortarte|secuestrarte|acuchillarte|ahorcarte|estrangularte|quemarte|lincharte|"
    r"torturarte|dispararte|balearte|fusilarte)\b",
    # "voy a violar a tu hermana", "voy a matar a tu mamá"
    r"\bvoy a (?:violar|matar|asesinar|golpear|secuestrar|torturar) (?:a )?(?:tu|tus|su|sus|ti)\b",
    # Presente: "te violo", "te mato", "te asesino", "te reviento"
    r"\bte (?:violo|mato|asesino|reviento|rompo la|parto la|corto|degüello|degüello|secuestro|torturo|quemo|disparo|fusilo|ahorco|estrangulo|madreo|linchan?)\b",
    r"\bte voy a dar (?:una|unos|unas) (?:madriza|golpiza|paliza|putiza|chinga|trancazos|chingadazos|madrazos|balazos)\b",
    r"\bte voy a partir (?:la|el|tu) (?:madre|cara|hocico|jeta|hocico|cabeza|cuello)\b",
    r"\bte vamos a (?:violar|matar|golpear|asesinar|linchar|madrear|reventar|torturar)\b",
    # Deseos de muerte o daño
    r"\bojala (?:te|se) (?:mueras|mueran|mueres|mate|maten|mataran|violen|violaran|atropellen|cai?gas|atropelle|muera|muere|pudras|pudran|quemes|quemen)\b",
    r"\b(?:muerete|muerase|mueranse|matate|suicidate|ahorcate|degollate|quemate|pudrete)\b",
    r"\bmerec(?:es|e|en) (?:morir|que te maten|ser violad[oa]|que te violen)\b",
    r"\bvete a morir\b", r"\bvas a morir\b", r"\btu vas a morir\b", r"\bte vas a morir\b",
    r"\bvoy a (?:ir por|encontrar|buscar) (?:a )?(?:ti|tu familia|tu casa|tu mama|tu hermana)\b",
    r"\bse donde vives\b", r"\bsabemos donde vives\b", r"\bsabemos donde vive\b",
    r"\bvoy a (?:matar|violar|asesinar|golpear) (?:a )?(?:todos|todas|todo)\b",
    r"\b(?:violare|violo|violaremos|violamos) (?:a )?(?:tu|tus|su|sus|ti)\b",
    r"\bviolar(?:te|lo|la|los|las)\b",
    # "violar a ..." (persona) pero NO "violar las reglas / la ley / los términos"
    r"\bviolar (?:a|al) (?!las? (?:reglas?|normas?|leyes?|ley|politicas?)\b)(?:\w+)\b",
    r"\bviolacion (?:grupal|tumultuaria|en manada)\b",
    r"\b(?:violen|violaran|violarian) (?:a )?(?:tu|tus|su|sus)\b",
    r"\b(?:te|los|las) (?:voy|vamos|van) a (?:\w+ )?(?:coger|cojer|follar|culear|chingar|penetrar)\b",
    r"\b(?:cogerte|follarte|culearte|penetrarte)\b",
    r"\bte van a (?:violar|matar|golpear|asesinar|linchar|madrear|reventar|torturar)\b",
    r"\b(?:mereces|merece) (?:que te violen|que te maten|morir|la muerte)\b",
    r"\bviolador(?:es)?\b",
]]
# Frases que parecen amenaza pero no lo son (juego, cocina, deportes): se descartan
SEGUROS_AMENAZA = [re.compile(p) for p in [
    r"\bviolar (?:las? |los )?(?:reglas?|normas?|leyes?|ley|politicas?|terminos|condiciones|derechos|privacidad|acuerdos?|contratos?)\b",
    r"\bmat(?:ar|are|o) (?:el|la|los|las) (?:tiempo|aburrimiento|hambre|sed|frio|calor|virus|bacterias|cucarachas?|moscas?|mosquitos?|plantas?|bichos|ratas? de laboratorio)\b",
    r"\bpegar (?:el|la|los|las) (?:cartel|poster|foto|etiqueta|pegatina|papel|sticker)\b",
    r"\bquemar (?:calorias|grasa|el|la|los|las) (?:calorias|grasa|disco|cd|lena|basura|incienso|salsa|comida|tostadas?)\b",
]]

# ---------------------------------------------------------------------------
# 4) Palabras de CONTEXTO: insultan solo si el contexto lo indica
# ---------------------------------------------------------------------------
CONTEXTO = [
    "tonto", "tonta", "bruto", "bruta", "inutil", "perdedor", "perdedora", "payaso", "payasa",
    "basura", "escoria", "lacra",  "asqueroso", "asquerosa", "gordo", "gorda",
    "fracasado", "fracasada", "manco", "manca", "bobo", "boba", "ridiculo", "ridicula",
    "lloron", "llorona",  "igualado", "hocico", "perra", "zorra", "cerdo", "cerda",
    "mongol", "retardado", "retardada", "invalido", "lisiado", "lisiada", "zonzo", "zonza",
    "cretino", "cretina", "mediocre", "patetico", "patetica", "inservible", "estorbo",
    "parasito", "desgraciado", "desgraciada", "miserable", "malnacido", "malnacida", "maldito",
    "maldita", "mugre", "porqueria", "tarugo", "burro", "burra", "cobarde",
]
_PATRON_CONTEXTO = re.compile(r"^(?:" + "|".join(_flexible(p) for p in CONTEXTO) + r")(?:s|es|ote|otes|ita|itas|ito|itos)?$")

# Señales de que una palabra de contexto se usa como insulto: aparece en las 3 palabras anteriores
_SENAL_INSULTO = {"eres", "eras", "sos", "es", "son", "soy", "seas", "ser", "pareces", "que", "bien", "muy", "tan",
                  "pinche", "pinches", "hija", "hijo", "callate", "vete", "largate", "como", "puro", "pura",
                  "grandisima", "grandisimo", "maldita", "maldito", "estupida", "estupido"}
# Señales de que se habla de un animal o de una cosa normal
_SENAL_ANIMAL = {"ladra", "ladrar", "cachorro", "cachorra", "mascota", "granja", "bosque", "veterinario",
                 "veterinaria", "paseo", "pasear", "croquetas", "huellas", "collar", "correa", "perrito",
                 "perrita", "tocino", "chorizo", "jamon", "carne", "puerco", "adoptar", "adopte", "adoptamos",
                 "perro", "perros", "gato", "gata", "ladro", "pastor", "salchicha", "chihuahua", "labrador", "husky", "poodle", "bulldog", "zorro"}


def es_palabra_groseria(p: str) -> bool:
    if p in _NORMALES:
        return False
    return bool(_PATRON_RAIZ.match(p) or _PATRON_PALABRA.match(p))


def es_palabra_odio(p: str) -> bool:
    return bool(_PATRON_ODIO.match(p))


def es_palabra_contexto(p: str) -> bool:
    return bool(_PATRON_CONTEXTO.match(p))


def contexto_insulto(palabras: list, i: int) -> bool:
    """¿La palabra de contexto en la posición i se usa como insulto? (reglas simples)."""
    if any(p in _SENAL_ANIMAL for p in palabras):
        return False
    return any(p in _SENAL_INSULTO for p in palabras[max(0, i - 3):i])


def frase_odio(texto_norm: str):
    return [m for r in FRASES_ODIO for m in r.finditer(texto_norm)]


def frase_amenaza(texto_norm: str):
    if any(r.search(texto_norm) for r in SEGUROS_AMENAZA):
        return []
    return [m for r in FRASES_AMENAZA for m in r.finditer(texto_norm)]


# ---------------------------------------------------------------------------
# 5) Frases groseras de varias palabras (siempre se censuran las palabras de la frase)
# ---------------------------------------------------------------------------
FRASES_GROSERAS = [re.compile(p) for p in [
    r"\bno mam(?:es|a|en|ar)\w*\b", r"\bnmms\b", r"\bno mamen\b",
    r"\bme (?:vale|valio|la pela|importa un) (?:madre|madres|verga|vergas|pito|reverendo)\b",
    r"\bvales? (?:madre|madres|verga|vergas)\b", r"\bvalio (?:madre|madres|verga|vergas)\b",
    r"\b(?:a la|ala) (?:madre|madres|verga|vergas|chingada|mierda)\b",
    r"\bde (?:poca|puta|su) madre\b", r"\bpoca madre\b", r"\bputa madre\b", r"\bpinche madre\b",
    r"\bni madres\b", r"\bhijo de (?:su|tu|la) (?:chingada|puta|pinche|madre)\b", r"\bhij[oa]s? de (?:tu )?(?:pinche )?put+a+\b",
    r"\bchinga(?:s|r)? (?:a )?(?:tu|su) madre\b", r"\bhij[oa]s? de la (?:gran )?(?:puta|chingada|verga|mierda)\b", r"\b(?:vete|vayanse|vaya) a la (?:verga|vrga|mierda|chingada)\b",
    r"\ba huevo\b", r"\bme lleva(?: la)?(?: chingada| verga| el diablo| la fregada)?\b",
    r"\b(?:que|qué) pedo\b", r"\b(?:no )?hay pedo\b", r"\bsin pedos\b", r"\bnada de pedos\b",
    r"\bcomo chingados\b", r"\bpor que chingados\b", r"\bque chingados\b", r"\bdonde chingados\b",
    r"\bvale gorro\b", r"\bme importa un comino\b",
    r"\bchupa(?:me|lo|la)? (?:la|el)? ?\w*\b(?= (?:verga|pito|pene))",
    r"\bchupame\b", r"\bchupalo\b", r"\bchupala\b", r"\bmamame\b", r"\bsuper puto\b",
    r"\bcomo la chingada\b", r"\ba chingar a su madre\b", r"\bvete a chingar\b",
    r"\bson? of a bitch\b", r"\bfuck(?:ing|er|ed)?\b", r"\bshit\b", r"\bbitch\b", r"\basshole\b", r"\bdick\b",
    r"\bmotherfucker\b", r"\bwtf\b", r"\bstfu\b", r"\bpussy\b", r"\bcunt\b", r"\bbastard\b", r"\bslut\b", r"\bwhore\b",
    r"\bchinga tu madre\b", r"\bchingatumadre\b", r"\bchingatu\w*\b", r"\bmadre\b(?= (?:que|tu|su) (?:chinga|puta|verga))",
    r"\bsoplapollas\b", r"\bcapullo\b", r"\bcapulla\b", r"\bcoño\b", r"\bjoder\b", r"\bjodete\b", r"\bme cago en\b",
    r"\bcarajo\b", r"\bcaray\b(?= zorra)",
]]

# Palabras sueltas en inglés (siempre se censuran)
INGLES = ["fuck", "fucker", "fucking", "fucked", "shit", "shitty", "bitch", "asshole", "dick", "pussy", "cunt",
          "bastard", "slut", "whore", "motherfucker", "wtf", "stfu", "dickhead", "bullshit", "cock", "nigga", "nigger", "fag", "faggot"]
_PATRON_INGLES = re.compile(r"^(?:" + "|".join(_flexible(p) for p in INGLES) + r")(?:s|es|ing|ed|er)?$")


def es_palabra_ingles(p: str) -> bool:
    return bool(_PATRON_INGLES.match(p))


def frase_grosera(texto_norm: str):
    return [m for r in FRASES_GROSERAS for m in r.finditer(texto_norm)]


# ---------------------------------------------------------------------------
# 6) Nombres de usuario: estricto (se busca DENTRO del nombre, ej. "ElPendejo99")
# ---------------------------------------------------------------------------
# Raíces largas: seguras para buscar dentro de cualquier nombre
RAICES_NOMBRE_LARGAS = [
    "pendej", "idiot", "imbecil", "estupid", "culer", "mierda", "chinga", "chingon", "cabron",
    "mamon", "mamada", "retrasad", "gilipoll", "malparid", "vergon", "verga", "pinche", "joder",
    "jodete", "maricon", "marica", "puto", "puta", "putit", "putaz", "pndj", "hdp", "ctm", "ptm",
    "vtalv", "hijueputa", "pelotud", "boludo", "culiao", "culiad", "cojon", "putisima", "gonorrea",
    "sexo", "porno", "pornografia", "vagina", "nalgas", "tetas", "orgasmo", "pija",
    "violar", "violador", "violaci", "nazi", "hitler", "kkk", "negrata", "nigga", "nigger", "faggot",
    "fuck", "shit", "bitch", "asshole", "dick", "cunt", "pussy", "slut", "whore", "joto", "culo",
    "perra", "zorra", "mugre", "pajero", "pajeo", "masturb", "semen", "coño", "ojete", "mamar", "mamame",
    "chupa", "tarado", "babos", "zopenc", "menso", "naco", "bastard", "cagon", "cagad", "sidoso", "mayate",
    "travelo", "tortillera", "machorra", "suicid", "terroris", 
    "estupido", "cabrona", "culero", "chingue", "chingad", "chingo", 
    "retrasa", "mongol", "subnormal", 
]
# Palabras normales que contienen raíces peligrosas: se quitan antes de revisar
NOMBRES_SEGUROS = re.compile(
    r"computa\w*|disputa\w*|reputa\w*|imputa\w*|diputad\w*|deputa\w*|putamen|"
    r"(?:ti|ri|pi|ra|ca|la|ni|ve|mus|ar|cir|cal|ec|ocu|obsta|ten|ma|sa|tra|su|bi|mi|ju|pe|pa|par|vehi)culo\w*|"
    r"culebr\w*|culmin\w*|cultur\w*|cultiv\w*|culpa\w*|culto\w*|"
    r"maricela|maricarmen|maricruz|marisol|marina|mariana|"
    r"vergara|vergel|"
    r"idioma\w*|"
    r"pitufo\w*|pitagoras|pitillo|"
    r"sexto|sexta|sextos|sextas|"
    r"penelope|penal\w*|pensar|pendiente|pendient\w*|penar|penas|"
    r"pinchazo\w*|pincho\w*|"
    r"asesor\w*|"
    r"matar[ei]\w*|matemati\w*|matilda|matias|material\w*|matriz|matute|matadero|"
    r"chupete|chupacabras|"
    r"nazir|nazario|"
    r"semental|seminario|seminari\w*|"
    r"shitake|shiitake|"
    r"pijama\w*|"
    r"nacho\w*|nacion\w*|nacer|"
    r"carajillo|"
    r"sidra\w*|"
    r"puton|"
    r"basuraleza"
)
