import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

# Configuración de pantalla
st.set_page_config(layout="wide", page_title="GEODNET MX - Folium Style")

@st.cache_data
def load_data():
    # 1. Cargar Estaciones
    df = pd.read_csv('E:/I+D/DESARROLLO_SOFTWARE/MAPA_GEODNET/conteo_final_mexico.csv').dropna(subset=['lat', 'lng'])
    
    # 2. Cargar Shapefile
    path_shp = r'E:/I+D/DESARROLLO_SOFTWARE/MAPA_GEODNET/MEXICO/estados-mexico.shp'
    try:
        gdf = gpd.read_file(path_shp, encoding='latin-1', engine='fiona')
    except Exception:
        gdf = gpd.read_file(path_shp, encoding='cp1252')
    
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    
    # Simplificar un poco para que el mapa no pese
    gdf['geometry'] = gdf['geometry'].simplify(0.005)
    return df, gdf

df_mx, gdf_estados = load_data()

# --- BARRA LATERAL ---
st.sidebar.title("🛰️ SELECCIONA UN ESTADO MX")
lista_estados = sorted(gdf_estados['nom_ent'].unique().tolist())
estado_sel = st.sidebar.selectbox("📍 Selecciona un Estado:", ["México (Vista General)"] + lista_estados)

# Lógica de coordenadas para el centro
if estado_sel != "México (Vista General)":
    poly = gdf_estados[gdf_estados['nom_ent'] == estado_sel].geometry.iloc[0]
    view_lat, view_lng = poly.centroid.y, poly.centroid.x
    view_zoom = 7
else:
    view_lat, view_lng = 23.6345, -102.5528
    view_zoom = 5

st.sidebar.subheader("🔍 Punto de Análisis")
u_lat = st.sidebar.number_input("Latitud", value=float(view_lat), format="%.6f")
u_lng = st.sidebar.number_input("Longitud", value=float(view_lng), format="%.6f")

# Cálculo de las 5 más cercanas
df_mx['dist_km'] = df_mx.apply(lambda r: geodesic((u_lat, u_lng), (r['lat'], r['lng'])).km, axis=1)
top5 = df_mx.nsmallest(5, 'dist_km')

# --- CREACIÓN DEL MAPA FOLIUM ---
st.subheader(f"🗺️ Cobertura de Red GEODNET: {estado_sel}")

# Crear el objeto mapa de Folium con el estilo que te gusta
m = folium.Map(location=[view_lat, view_lng], zoom_start=view_zoom, tiles='OpenStreetMap')

# Capa de los estados (Tu SHP)
folium.GeoJson(
    gdf_estados if estado_sel == "México (Vista General)" else gdf_estados[gdf_estados['nom_ent'] == estado_sel],
    style_function=lambda x: {'fillColor': '#black', 'color': '#222', 'weight': 1, 'fillOpacity': 0.05}
).add_to(m)

# Capas de Estaciones y Radios
for row in df_mx.itertuples():
    # El radio de 100km
    folium.Circle(
        location=[row.lat, row.lng],
        radius=100000,
        color='green',
        weight=1,
        fill=True,
        fill_opacity=0.03,
        interactive=False
    ).add_to(m)
    
    # ACCESO CORREGIDO: Usamos getattr para manejar el nombre '_id' de forma segura
    estacion_id = getattr(row, '_id', 'Sin ID')
    
    # El punto de la antena
    folium.CircleMarker(
        location=[row.lat, row.lng],
        radius=3,
        color='green',
        fill=True,
        fill_opacity=0.7,
        popup=f"Estación: {estacion_id}"
    ).add_to(m)

# Marcador de usuario (Punto Rojo)
folium.Marker(
    location=[u_lat, u_lng],
    popup="Tu ubicación",
    icon=folium.Icon(color='red', icon='info-sign')
).add_to(m)

# Dibujar líneas a las 5 más cercanas
for row in top5.itertuples():
    folium.PolyLine(
        locations=[[u_lat, u_lng], [row.lat, row.lng]],
        color='red',
        weight=2,
        dash_array='5, 5',
        tooltip=f"{row.dist_km:.2f} km"
    ).add_to(m)

# RENDERIZAR EN STREAMLIT
st_folium(m, width=1200, height=600, returned_objects=[])

# --- TABLA ---
st.dataframe(top5[['_id', 'lat', 'lng', 'dist_km']].style.format({"dist_km": "{:.2f} km"}), use_container_width=True)