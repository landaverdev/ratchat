"""
Pruebas del detector.  Ejecutar desde la carpeta servidor/:
    python -m pytest pruebas        (o simplemente: python pruebas/test_detector.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detector import Detector  # noqa: E402
from detector.normalizar import normalizar_texto  # noqa: E402

det = Detector()


def test_normalizacion():
    assert normalizar_texto("P3ND3J0") == "pendejo"
    assert normalizar_texto("p.e.n.d.e.j.o") == "pendejo"
    assert normalizar_texto("p e n d e j o") == "pendejo"
    assert normalizar_texto("Estúpidoooo") == "estupidoo"
    assert normalizar_texto("tengo 5 vidas") == "tengo vidas"


def test_insultos_se_censuran():
    for texto, esperado in [
        ("eres un pendejo", "eres un *******"),
        ("P3ND3J0 jaja", "******* jaja"),
        ("hijo de puta", "**** ** ****"),
    ]:
        r = det.analizar(texto)
        assert r.es_inapropiado, texto
        assert r.texto_censurado == esperado, (texto, r.texto_censurado)


def test_groserias_se_censuran_aunque_sean_amistosas():
    for texto, esperado in [
        ("qué chingón jugaste", "qué ******* jugaste"),
        ("pinche lag", "****** lag"),
        ("no mames qué buena jugada", "** ***** qué buena jugada"),
        ("está cabrón este nivel", "está ****** este nivel"),
        ("eres bien chingón", "eres bien *******"),
        ("a huevo ganamos", "* ***** ganamos"),
    ]:
        r = det.analizar(texto)
        assert r.es_inapropiado, texto
        assert r.categoria == "groseria", (texto, r.categoria)
        assert r.texto_censurado == esperado, (texto, r.texto_censurado)


def test_odio():
    for texto in ["eres un joto", "ese marica no sabe jugar", "qué onda marica", "j0t0", "ma.ri.con", "odio a los gays"]:
        r = det.analizar(texto)
        assert r.es_inapropiado and r.categoria == "odio", (texto, r.categoria)


def test_amenazas():
    for texto in ["te voy a violar", "te voy a matar", "ojalá te mueras", "voy a violar a tu hermana",
                  "tevoy a violar", "mátate"]:
        r = det.analizar(texto)
        assert r.es_inapropiado and r.categoria == "amenaza", (texto, r.categoria)
    assert det.analizar("te voy a violar").texto_censurado == "** *** * ******"


def test_palabras_parecidas_no_se_censuran():
    for texto in ["mi computadora es nueva", "estudio idiomas", "vi un zorro", "hice pastel de pera",
                  "te mando saludos", "estoy pendiente", "hola Maricela", "mi maestra es Vergara",
                  "no hay que violar las reglas", "te voy a ganar", "voy a matar el tiempo",
                  "mi perra se llama Luna", "el huevo frito", "mi mamá me llama", "el cabrito estaba rico",
                  "la verdad no sé", "te voy a reportar", "hay que ser amables con todos"]:
        r = det.analizar(texto)
        assert not r.es_inapropiado, (texto, r.categoria, r.palabras_censuradas)
        assert r.texto_censurado == texto


def test_perra_depende_del_contexto():
    assert det.analizar("eres una perra").es_inapropiado
    assert not det.analizar("mi perra tuvo cachorros").es_inapropiado


def test_nombres():
    malos = ["ElPendejo", "Pendejo99", "xXPutoXx", "Maric0n", "J0to", "Mierda", "Chingon", "Pinche_Rata",
             "ratoncito_culero", "P3nd3j0", "Perra", "Violador", "idiota", "ElMarica", "hdp_gamer", "te.voy.a.violar"]
    buenos = ["Luna", "Copito", "Maricela", "Computadora", "Vergara", "Disputa", "RataVeloz", "Queso_07",
              "Ximena", "Nacho", "Pedro", "Penelope", "Cultura", "Mariana", "ElMaestro"]
    for n in malos:
        assert not det.nombre_permitido(n), n
    for n in buenos:
        assert det.nombre_permitido(n), n


if __name__ == "__main__":
    for nombre, f in list(globals().items()):
        if nombre.startswith("test_"):
            f()
            print("ok", nombre)
