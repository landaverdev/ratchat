"""
Genera ../dashboard.html: un solo archivo HTML (sin dependencias externas) que se abre con
doble clic en cualquier navegador.

Qué incrusta dentro del HTML (para que funcione sin servidor y sin internet):
  - modelo/metricas.json  -> gráficas del dashboard (valores reales del último entrenamiento)
  - el léxico y las reglas de detector/lexico.py  -> simulador en JavaScript
  - los pesos del modelo entrenado (vocabulario TF-IDF, IDF y coeficientes de la regresión
    logística) -> el simulador calcula la MISMA probabilidad que scikit-learn

Se ejecuta solo al final de `python entrenar.py`; también se puede correr a mano:
    python construir_dashboard.py
"""

import json
from pathlib import Path

import joblib

from detector import lexico as L

AQUI = Path(__file__).resolve().parent
PLANTILLA = AQUI / "dashboard_plantilla.html"
SALIDA = AQUI.parent / "dashboard.html"
MARCA = "/*__DATOS__*/null"


def exportar_lexico() -> dict:
    return {
        "patron_raiz": L._PATRON_RAIZ.pattern,
        "patron_palabra": L._PATRON_PALABRA.pattern,
        "patron_odio": L._PATRON_ODIO.pattern,
        "patron_contexto": L._PATRON_CONTEXTO.pattern,
        "patron_ingles": L._PATRON_INGLES.pattern,
        "normales": sorted(L._NORMALES),
        "frases_odio": [r.pattern for r in L.FRASES_ODIO],
        "frases_amenaza": [r.pattern for r in L.FRASES_AMENAZA],
        "seguros_amenaza": [r.pattern for r in L.SEGUROS_AMENAZA],
        "frases_groseras": [r.pattern for r in L.FRASES_GROSERAS],
        "senal_insulto": sorted(L._SENAL_INSULTO),
        "senal_animal": sorted(L._SENAL_ANIMAL),
        "raices_nombre": list(L.RAICES_NOMBRE_LARGAS),
        "nombres_seguros": L.NOMBRES_SEGUROS.pattern,
    }


def exportar_modelo(ruta: Path) -> dict:
    """Vocabulario, IDF y coeficientes: lo necesario para repetir el cálculo en JavaScript."""
    modelo = joblib.load(ruta)
    union = modelo.named_steps["caracteristicas"]
    clf = modelo.named_steps["clasificador"]
    coef = clf.coef_[0]
    salida, inicio = {}, 0
    for nombre, vec in union.transformer_list:
        terminos = [t for t, _ in sorted(vec.vocabulary_.items(), key=lambda kv: kv[1])]
        n = len(terminos)
        salida[nombre] = {
            "terminos": terminos,
            "idf": [round(float(x), 5) for x in vec.idf_],
            "coef": [round(float(x), 5) for x in coef[inicio:inicio + n]],
        }
        inicio += n
    salida["intercepto"] = round(float(clf.intercept_[0]), 5)
    return salida


def construir() -> Path:
    metricas = json.loads((AQUI / "modelo" / "metricas.json").read_text(encoding="utf-8"))
    datos = {
        "metricas": metricas,
        "lexico": exportar_lexico(),
        "modelo": exportar_modelo(AQUI / "modelo" / "modelo.joblib"),
    }
    html = PLANTILLA.read_text(encoding="utf-8")
    if MARCA not in html:
        raise SystemExit("La plantilla no tiene el marcador de datos.")
    cuerpo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    SALIDA.write_text(html.replace(MARCA, cuerpo, 1), encoding="utf-8")
    return SALIDA


if __name__ == "__main__":
    print("Dashboard escrito en", construir())
