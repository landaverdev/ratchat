"""
Entrena el modelo de IA que detecta lenguaje inapropiado (groserías, insultos, odio y amenazas) y guarda sus métricas.

    python entrenar.py

Pasos:
  1. Carga datos/dataset_groserias.csv (+ datos/externos.csv si existe, ver importar_externos.py)
  2. Evalúa con GroupShuffleSplit (5 divisiones): las plantillas de prueba NUNCA aparecen en el
     entrenamiento, así las métricas no se inflan por memorizar frases. Se mide el modelo de IA solo
     y el sistema híbrido completo (léxico + contexto + modelo).
  3. Evalúa el sistema completo con datos/prueba_dificil.csv (frases escritas a mano; ojo: se
     usaron mientras se ajustaba el léxico, así que su resultado es optimista).
  4. Entrena el modelo final con todos los datos y lo guarda en modelo/modelo.joblib
  5. Guarda modelo/metricas.json (con ejemplos de errores) y regenera ../dashboard.html

El resultado es reproducible: semillas fijas y dataset generado con semilla fija.
"""

import json
import platform
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline

from detector.normalizar import normalizar_texto

AQUI = Path(__file__).parent
DATOS = AQUI / "datos"
MODELO = AQUI / "modelo"
NOMBRES_CLASE = ["apropiado", "inapropiado"]
SEMILLA_DIVISION = 7
DIVISIONES = 5
TAM_PRUEBA = 0.25
MAX_ERRORES = 25   # cuántos ejemplos de error se guardan en metricas.json


def crear_modelo():
    caracteristicas = FeatureUnion([
        # Palabras y pares de palabras: capta el contexto ("eres bien" + "pendejo")
        ("palabras", TfidfVectorizer(preprocessor=normalizar_texto, ngram_range=(1, 2), sublinear_tf=True)),
        # Pedazos de 2 a 5 letras: capta variantes y faltas de ortografía ("pndjo", "estupida")
        ("letras", TfidfVectorizer(preprocessor=normalizar_texto, analyzer="char_wb",
                                   ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
    ])
    clasificador = LogisticRegression(C=4.0, class_weight="balanced", max_iter=3000)
    return Pipeline([("caracteristicas", caracteristicas), ("clasificador", clasificador)])


def cargar_datos():
    datos = pd.read_csv(DATOS / "dataset_groserias.csv")
    n_externos = 0
    externos = DATOS / "externos.csv"
    if externos.exists():
        extra = pd.read_csv(externos)
        n_externos = len(extra)
        datos = pd.concat([datos, extra[["texto", "etiqueta", "tipo", "plantilla"]]], ignore_index=True)
        print(f"+ {n_externos} frases de {externos.name}")
    datos = datos.dropna(subset=["texto"]).drop_duplicates(subset=["texto"]).reset_index(drop=True)
    return datos, n_externos


def media(v):
    return round(float(sum(v) / len(v)), 4)


def desv(v):
    return round(float(pd.Series(v).std(ddof=0)), 4)


def resumen(y, pred):
    """Métricas de la clase 'inapropiado' (1)."""
    return {
        "exactitud": round(float(accuracy_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
    }


def aciertos_por_tipo(df, col):
    return {t: round(float((g.etiqueta == g[col]).mean()), 4) for t, g in df.groupby("tipo")}


def ejemplos_error(df, col, limite=MAX_ERRORES):
    err = df[df.etiqueta != df[col]]
    return [{"texto": r.texto, "tipo": r.tipo, "esperado": "inapropiado" if r.etiqueta else "apropiado",
             "predijo": "inapropiado" if r[col] else "apropiado"} for _, r in err.head(limite).iterrows()]


def main():
    datos, n_externos = cargar_datos()
    print(f"Dataset: {len(datos)} frases, {datos.texto.str.len().sum():,} caracteres, {datos.plantilla.nunique()} plantillas")
    print(datos.tipo.value_counts().to_string(), "\n")

    # --- 1. Evaluación con plantillas nunca vistas (promedio de 5 divisiones) -----
    division = GroupShuffleSplit(n_splits=DIVISIONES, test_size=TAM_PRUEBA, random_state=SEMILLA_DIVISION)
    from detector import Detector
    res_modelo, res_sistema = [], []
    matriz_modelo = matriz_sistema = None
    por_tipo_modelo, por_tipo_sistema = {}, {}
    errores_modelo, errores_sistema = [], []
    for k, (i_ent, i_pru) in enumerate(division.split(datos, groups=datos.plantilla)):
        ent, pru = datos.iloc[i_ent].copy(), datos.iloc[i_pru].copy()
        modelo_k = crear_modelo().fit(ent.texto, ent.etiqueta)
        det_k = Detector(modelo=modelo_k)
        pru["pred_modelo"] = modelo_k.predict(pru.texto)
        pru["pred_sistema"] = [int(det_k.analizar(t).es_inapropiado) for t in pru.texto]
        res_modelo.append(resumen(pru.etiqueta, pru.pred_modelo))
        res_sistema.append(resumen(pru.etiqueta, pru.pred_sistema))
        m1 = confusion_matrix(pru.etiqueta, pru.pred_modelo, labels=[0, 1])
        m2 = confusion_matrix(pru.etiqueta, pru.pred_sistema, labels=[0, 1])
        matriz_modelo = m1 if matriz_modelo is None else matriz_modelo + m1
        matriz_sistema = m2 if matriz_sistema is None else matriz_sistema + m2
        for t, v in aciertos_por_tipo(pru, "pred_modelo").items():
            por_tipo_modelo.setdefault(t, []).append(v)
        for t, v in aciertos_por_tipo(pru, "pred_sistema").items():
            por_tipo_sistema.setdefault(t, []).append(v)
        if k == 0:
            errores_modelo = ejemplos_error(pru, "pred_modelo")
            errores_sistema = ejemplos_error(pru, "pred_sistema")
            print("=== División 1 de 5: plantillas que el modelo no vio ===")
            print(classification_report(pru.etiqueta, pru.pred_modelo, target_names=NOMBRES_CLASE, digits=3))

    def promedio(lista):
        return {m: {"promedio": media([r[m] for r in lista]), "desviacion": desv([r[m] for r in lista])}
                for m in ("exactitud", "precision", "recall", "f1")}

    p_modelo, p_sistema = promedio(res_modelo), promedio(res_sistema)
    print("Solo el modelo de IA        :", {m: v["promedio"] for m, v in p_modelo.items()})
    print("Sistema completo (híbrido)  :", {m: v["promedio"] for m, v in p_sistema.items()}, "\n")

    # --- 2. Modelo final con todos los datos ------------------------------------
    modelo = crear_modelo().fit(datos.texto, datos.etiqueta)
    MODELO.mkdir(exist_ok=True)
    joblib.dump(modelo, MODELO / "modelo.joblib")

    # --- 3. Sistema completo (modelo + reglas) con frases escritas a mano -------
    det = Detector()
    dificil = pd.read_csv(DATOS / "prueba_dificil.csv")
    analisis = [det.analizar(t) for t in dificil.texto]
    dificil["prediccion"] = [int(r.es_inapropiado) for r in analisis]
    dificil["categoria"] = [r.categoria for r in analisis]
    dificil["motivo"] = [r.motivo for r in analisis]
    print("=== Sistema completo con prueba_dificil.csv (frases escritas a mano) ===")
    print(classification_report(dificil.etiqueta, dificil.prediccion, target_names=NOMBRES_CLASE, digits=3))
    errores = dificil[dificil.etiqueta != dificil.prediccion]
    if len(errores):
        print("Errores:")
        for _, e in errores.iterrows():
            print(f"  [{e.tipo}] {e.texto!r} -> predijo {'inapropiado' if e.prediccion else 'apropiado'}")
    else:
        print("Sin errores en prueba_dificil.csv (recuerden que se usó para ajustar el léxico: es optimista).")

    metricas = {
        "dataset": {
            "frases": int(len(datos)),
            "caracteres": int(datos.texto.str.len().sum()),
            "plantillas": int(datos.plantilla.nunique()),
            "frases_externas": int(n_externos),
            "por_tipo": {k: int(v) for k, v in datos.tipo.value_counts().items()},
            "plantillas_por_tipo": {k: int(v) for k, v in datos.groupby("tipo").plantilla.nunique().items()},
        },
        "configuracion": {
            "modelo": "TfidfVectorizer (palabras 1-2) + TfidfVectorizer (letras 2-5, char_wb) + LogisticRegression",
            "logistic_regression": {"C": 4.0, "class_weight": "balanced", "max_iter": 3000},
            "validacion": {"tipo": "GroupShuffleSplit por plantilla", "divisiones": DIVISIONES,
                           "tam_prueba": TAM_PRUEBA, "semilla": SEMILLA_DIVISION},
            "umbrales_detector": {"contexto": 0.5, "modelo_sin_palabra_conocida": 0.85, "nombres": 0.85},
            "versiones": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                          "pandas": pd.__version__},
        },
        "plantillas_no_vistas": {
            "divisiones": DIVISIONES,
            "modelo_ia_solo": p_modelo,
            "sistema_completo": p_sistema,
            "aciertos_por_tipo": {
                "modelo_ia_solo": {t: media(v) for t, v in sorted(por_tipo_modelo.items())},
                "sistema_completo": {t: media(v) for t, v in sorted(por_tipo_sistema.items())},
            },
            "matriz_confusion_modelo_ia_solo": matriz_modelo.tolist(),
            "matriz_confusion_sistema_completo": matriz_sistema.tolist(),
            "ejemplos_error_modelo_ia_solo": errores_modelo,
            "ejemplos_error_sistema_completo": errores_sistema,
            "nota": "Matrices sumadas de las 5 divisiones: filas = real (apropiado, inapropiado), columnas = predicho.",
        },
        "prueba_dificil": {
            "frases": int(len(dificil)),
            "advertencia": "Escrita a mano y usada mientras se ajustaba el léxico: resultado optimista.",
            "exactitud": round(float(accuracy_score(dificil.etiqueta, dificil.prediccion)), 4),
            "precision": round(float(precision_score(dificil.etiqueta, dificil.prediccion, zero_division=0)), 4),
            "recall": round(float(recall_score(dificil.etiqueta, dificil.prediccion, zero_division=0)), 4),
            "f1_inapropiado": round(float(f1_score(dificil.etiqueta, dificil.prediccion)), 4),
            "frases_por_tipo": {t: int(n) for t, n in dificil.tipo.value_counts().items()},
            "aciertos_por_tipo": aciertos_por_tipo(dificil, "prediccion"),
            "matriz_confusion": confusion_matrix(dificil.etiqueta, dificil.prediccion, labels=[0, 1]).tolist(),
            "errores": ejemplos_error(dificil, "prediccion"),
        },
    }
    (MODELO / "metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nModelo guardado en {MODELO / 'modelo.joblib'}")
    print(f"Métricas guardadas en {MODELO / 'metricas.json'}")

    # --- 4. Dashboard autocontenido con las métricas reales ---------------------
    try:
        from construir_dashboard import construir
        print("Dashboard actualizado en", construir())
    except ImportError:
        pass


if __name__ == "__main__":
    main()
