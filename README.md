# Laboratorio 4 - Análisis geoespacial de cianobacterias

Este repositorio contiene el avance de los ejercicios 1 a 4 para los lagos de
Amatitlán y Atitlán. El notebook principal es
`Lab4_Analisis_Cianobacterias.ipynb`.

## Preparación y ejecución

1. Crear y activar un entorno virtual con Python 3.11 o superior.
2. Instalar las dependencias con `python -m pip install -r requirements.txt`.
3. Abrir Jupyter desde la raíz del proyecto y seleccionar el kernel del entorno.
4. Ejecutar el notebook en orden. La primera conexión a Copernicus Data Space
   solicita autenticación interactiva OIDC; no se guardan credenciales en Git.

Las descargas B03, B04 y B08 se regeneran en `data/raw/`, que no se versiona
por su tamaño. El producto numérico de cianobacteria se ubica en
`data/cyano/` y también se mantiene fuera de Git. Antes de ejecutar las
secciones 3 y 4, debe existir un GeoTIFF de una banda por lago y fecha, con la
misma grilla del raster mínimo. No se debe usar una captura RGB del script para
calcular promedios o picos.

## Alcance del avance

El avance cubre:

- conexión y trazabilidad de las 22 fechas oficiales;
- obtención mínima de bandas Sentinel-2;
- cálculo de NDVI, NDWI y un producto numérico de cianobacteria documentado;
- métricas por fecha, serie temporal y detección reproducible de picos.

Los ejercicios 5 a 8 pertenecen a la fase 2 y aparecen solo como secciones
pendientes en el notebook. La lista de control generada en
`outputs/tablas/lista_control_calidad_avance.csv` identifica cualquier insumo
faltante antes de preparar la entrega.

## Entrega de Persona 1

La parte de datos y reproducibilidad queda respaldada por `inventario_datos.csv`,
`lista_control_calidad_avance.csv`, los módulos de `src/` y la sección de
correlaciones del ejercicio 6. La tabla `outputs/tablas/correlaciones_por_lago.csv`
y la figura `outputs/figuras/correlaciones_por_lago.png` se generan al ejecutar el
notebook con los raster compartidos localmente. Las carpetas `data/raw/`,
`data/cyano/` y `data/cyano_inputs/` no se suben a Git por su tamaño; deben
compartirse por Drive/OneDrive conservando sus rutas relativas.

## Fuentes y limitaciones

La estimación de cianobacteria debe documentar el script CyanoLakes
Chlorophyll-a NDCI L1C de Sentinel Hub y su versión. Sus resultados son una
estimación indirecta; nubes, mezcla de píxeles, falta de una máscara precisa del
lago y condiciones ópticas no representadas por el modelo son limitaciones que
deben declararse al interpretar los resultados.
