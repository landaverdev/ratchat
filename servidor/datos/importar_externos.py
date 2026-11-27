"""
Integra un dataset EXTERNO (propio o de terceros) al entrenamiento de RatChat.

Este repositorio NO incluye ni descarga ningún dataset externo: el dataset base
(dataset_groserias.csv) es sintético y lo genera generar_dataset.py. Este script solo
sirve para el caso en que ustedes consigan un archivo con mensajes reales etiquetados
(por ejemplo, uno que ustedes mismos hayan recopilado con permiso, o un corpus académico
al que tengan acceso) y quieran reentrenar con él. No hace scraping de ningún sitio.

Qué hace
--------
1. Lee un CSV/TSV con una columna de texto y una columna de etiqueta.
2. Normaliza el texto: quita @menciones (-> @usuario), URL, espacios repetidos, saltos de línea
   y filas vacías, y descarta mensajes de menos de 2 caracteres o de más de 280.
3. Convierte la etiqueta a 0/1 (1 = lenguaje inapropiado) según los valores que ustedes indiquen.
4. Agrega las filas a datos/externos.csv (sin duplicar textos) con las columnas
   texto, etiqueta, tipo, plantilla.
5. Al ejecutar `python entrenar.py`, se leen automáticamente dataset_groserias.csv + externos.csv.

Uso
---
    python importar_externos.py archivo.csv --texto tweet --etiqueta clase --inapropiado 1
    python importar_externos.py archivo.tsv --sep tab --texto comment --etiqueta label --inapropiado OFP,OFG
    python importar_externos.py archivo.csv --texto texto --etiqueta clase --inapropiado 1 --tipo-ofensivo odio

Opciones
--------
  --texto        nombre de la columna con el texto
  --etiqueta     nombre de la columna con la clase
  --inapropiado  valores de la etiqueta que cuentan como inapropiado (separados por coma).
                 Todo lo demás se toma como apropiado (0). (--insulto es un alias antiguo.)
  --tipo-ofensivo  tipo que se guarda para las filas inapropiadas: insulto (default), groseria, odio o amenaza
  --sep          separador: coma (default), tab o puntoycoma
  --codificacion codificación del archivo (default utf-8; prueben latin-1 si hay caracteres raros)
  --reemplazar   borra externos.csv antes de importar (por defecto se AGREGA)

Cómo se usan las filas externas al evaluar
------------------------------------------
Los datos externos no tienen plantilla, así que se agrupan en bloques consecutivos de 50 filas
(plantilla "externo-0", "externo-1", ...). GroupShuffleSplit mantiene cada bloque completo en
entrenamiento O en prueba, igual que con las plantillas del dataset sintético.

Recomendaciones
---------------
- Revisen una muestra a mano antes de entrenar: las etiquetas de terceros pueden no coincidir con
  la política de RatChat (aquí también se censuran las groserías amistosas).
- Si el dataset externo está en otro idioma o dialecto, el modelo puede empeorar en español mexicano.
- Después de importar, reentrenen con `python entrenar.py`; las métricas cambiarán y se guardarán
  en modelo/metricas.json (la sección "dataset" indicará cuántas filas externas se usaron).
"""

import argparse
import re
from pathlib import Path

import pandas as pd

SEPARADORES = {"coma": ",", "tab": "\t", "puntoycoma": ";"}
DESTINO = Path(__file__).parent / "externos.csv"
TIPOS = ("insulto", "groseria", "odio", "amenaza")
COLUMNAS = ["texto", "etiqueta", "tipo", "plantilla"]


def limpiar_texto(serie: pd.Series) -> pd.Series:
    """Normalización básica de texto externo (ver el docstring del módulo)."""
    return (serie.astype(str)
            .str.replace(r"https?://\S+|www\.\S+", "", regex=True)
            .str.replace(r"@\w+", "@usuario", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip())


def convertir(datos: pd.DataFrame, col_texto: str, col_etiqueta: str, valores: set, tipo: str) -> pd.DataFrame:
    for col in (col_texto, col_etiqueta):
        if col not in datos.columns:
            raise SystemExit(f"No existe la columna '{col}'. Columnas del archivo: {list(datos.columns)}")
    nuevo = pd.DataFrame({
        "texto": limpiar_texto(datos[col_texto]),
        "etiqueta": datos[col_etiqueta].astype(str).str.strip().isin(valores).astype(int),
    })
    nuevo = nuevo[nuevo.texto.str.len().between(2, 280)]
    nuevo = nuevo.drop_duplicates("texto").reset_index(drop=True)
    nuevo["tipo"] = nuevo.etiqueta.map({1: tipo, 0: "limpio"})
    nuevo["plantilla"] = "externo-" + (nuevo.index // 50).astype(str)
    return nuevo[COLUMNAS]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--texto", required=True)
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--inapropiado", "--insulto", dest="inapropiado", required=True,
                    help="valores que significan inapropiado, ej. 1 u OFP,OFG")
    ap.add_argument("--tipo-ofensivo", default="insulto", choices=TIPOS)
    ap.add_argument("--sep", default="coma", choices=SEPARADORES)
    ap.add_argument("--codificacion", default="utf-8")
    ap.add_argument("--reemplazar", action="store_true")
    a = ap.parse_args()

    datos = pd.read_csv(a.archivo, sep=SEPARADORES[a.sep], dtype=str, encoding=a.codificacion,
                        on_bad_lines="skip")
    valores = {v.strip() for v in a.inapropiado.split(",")}
    nuevo = convertir(datos, a.texto, a.etiqueta, valores, a.tipo_ofensivo)

    if DESTINO.exists() and not a.reemplazar:
        previo = pd.read_csv(DESTINO)
        nuevo = pd.concat([previo, nuevo], ignore_index=True).drop_duplicates("texto").reset_index(drop=True)
        nuevo["plantilla"] = "externo-" + (nuevo.index // 50).astype(str)
    nuevo.to_csv(DESTINO, index=False)
    print(f"{DESTINO.name}: {len(nuevo)} frases ({int(nuevo.etiqueta.sum())} inapropiadas, "
          f"{int((nuevo.etiqueta == 0).sum())} apropiadas).")
    print("Siguiente paso:  python entrenar.py")


if __name__ == "__main__":
    main()
