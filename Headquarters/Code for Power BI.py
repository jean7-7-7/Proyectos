import warnings
warnings.filterwarnings("ignore")

import requests
import pandas as pd
import numpy as np
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2

OVERPASS_ENDPOINTS = {
    "fossgis": "https://overpass-api.de/api/interpreter",
    "kumi": "https://overpass.kumi.systems/api/interpreter",
    "main": "https://overpass-api.de/api/interpreter",
    "mailru": "https://overpass.maptile.ru/api/interpreter"
}

CATEGORY_WEIGHTS_REF = {
    "transporte": 20, "educacion": 20, "salud": 20,
    "ocio": 15, "restauracion": 10, "comercio": 15
}

POI_SCORES = {
    "railway=station": {"cat": "transporte", "score": 30},
    "public_transport=station": {"cat": "transporte", "score": 25},
    "amenity=bus_station": {"cat": "transporte", "score": 20},
    "highway=bus_stop": {"cat": "transporte", "score": 8},
    "amenity=ferry_terminal": {"cat": "transporte", "score": 15},
    "aeroway=aerodrome": {"cat": "transporte", "score": 40},
    "amenity=university": {"cat": "educacion", "score": 35},
    "amenity=college": {"cat": "educacion", "score": 25},
    "amenity=school": {"cat": "educacion", "score": 20},
    "amenity=kindergarten": {"cat": "educacion", "score": 10},
    "amenity=library": {"cat": "educacion", "score": 12},
    "amenity=childcare": {"cat": "educacion", "score": 8},
    "amenity=place_of_worship": {"cat": "educacion", "score": 5},
    "amenity=community_centre": {"cat": "educacion", "score": 10},
    "amenity=hospital": {"cat": "salud", "score": 50},
    "amenity=clinic": {"cat": "salud", "score": 30},
    "amenity=doctors": {"cat": "salud", "score": 15},
    "amenity=dentist": {"cat": "salud", "score": 10},
    "amenity=pharmacy": {"cat": "salud", "score": 10},
    "amenity=veterinary": {"cat": "salud", "score": 5},
    "amenity=social_facility": {"cat": "salud", "score": 20},
    "leisure=park": {"cat": "ocio", "score": 15},
    "leisure=garden": {"cat": "ocio", "score": 12},
    "leisure=playground": {"cat": "ocio", "score": 8},
    "leisure=pitch": {"cat": "ocio", "score": 10},
    "leisure=sports_centre": {"cat": "ocio", "score": 15},
    "leisure=nature_reserve": {"cat": "ocio", "score": 20},
    "tourism=attraction": {"cat": "ocio", "score": 12},
    "amenity=bench": {"cat": "ocio", "score": 2},
    "amenity=restaurant": {"cat": "restauracion", "score": 6},
    "amenity=cafe": {"cat": "restauracion", "score": 4},
    "amenity=fast_food": {"cat": "restauracion", "score": 4},
    "amenity=bar": {"cat": "restauracion", "score": 4},
    "amenity=pub": {"cat": "restauracion", "score": 4},
    "amenity=ice_cream": {"cat": "restauracion", "score": 2},
    "shop=supermarket": {"cat": "comercio", "score": 15},
    "shop=convenience": {"cat": "comercio", "score": 6},
    "shop=mall": {"cat": "comercio", "score": 20},
    "amenity=bank": {"cat": "comercio", "score": 10},
    "amenity=atm": {"cat": "comercio", "score": 3},
    "amenity=post_office": {"cat": "comercio", "score": 6},
    "amenity=police": {"cat": "comercio", "score": 8},
    "amenity=fire_station": {"cat": "comercio", "score": 12},
    "shop=general": {"cat": "comercio", "score": 5},
    "shop=hardware": {"cat": "comercio", "score": 5},
    "shop=electronics": {"cat": "comercio", "score": 5},
    "amenity=marketplace": {"cat": "comercio", "score": 12},
    "amenity=fuel": {"cat": "comercio", "score": 10},
    "amenity=telephone": {"cat": "comercio", "score": 2},
    "amenity=townhall": {"cat": "comercio", "score": 10},
    "amenity=public_building": {"cat": "comercio", "score": 6},
    "shop=car_repair": {"cat": "comercio", "score": 5},
}

KEYWORDS = {
    "educacion": ["escuela", "colegio", "liceo", "universidad", "biblioteca", "kindergarten", "guardería", "casa de la cultura"],
    "salud": ["hospital", "clínica", "médico", "farmacia", "centro de salud", "ambulatorio"],
    "transporte": ["parada", "estación", "metro", "bus", "camioneta"],
    "ocio": ["parque", "plaza", "cancha", "gimnasio", "área recreativa"],
    "restauracion": ["restaurante", "cafetería", "comida rápida", "bar", "arepera"],
    "comercio": ["tienda", "supermercado", "abasto", "mercado", "banco", "casa de cambio"]
}

def haversine_corrected(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    return distance / 10.0

def query_overpass(query):
    headers = {'User-Agent': 'PowerBI-Overpass-Script/2.0'}
    timeout = 90
    for name, endpoint in OVERPASS_ENDPOINTS.items():
        try:
            resp = requests.post(endpoint, data=query, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            continue
    return None

def build_overpass_query(lat, lon, radius):
    return f"""
    [out:json][timeout:60];
    ( node(around:{radius}, {lat}, {lon}); way(around:{radius}, {lat}, {lon}); relation(around:{radius}, {lat}, {lon}); );
    out body;"""

def get_location_intelligence(lat, lon, radius=3000):
    query = build_overpass_query(lat, lon, radius)
    return query_overpass(query)

def classify_poi(tags):
    for key_val, info in POI_SCORES.items():
        if '=' in key_val:
            k, v = key_val.split('=', 1)
            if tags.get(k) == v:
                return info['cat'], info['score']
    for val in tags.values():
        val_lower = val.lower()
        for cat, kw_list in KEYWORDS.items():
            if any(kw in val_lower for kw in kw_list):
                return cat, 3
    return None

def analyze_location_points(lat, lon, radius=3000, top_n=10):
    data = get_location_intelligence(lat, lon, radius)
    if not data or 'elements' not in data:
        return 0, {}, 0, radius, []
    
    points_by_cat = defaultdict(float)
    places_list = []
    
    for element in data['elements']:
        tags = element.get('tags', {})
        if not tags:
            continue
        
        if 'lat' in element and 'lon' in element:
            el_lat, el_lon = element['lat'], element['lon']
        elif 'center' in element:
            el_lat, el_lon = element['center'].get('lat'), element['center'].get('lon')
        else:
            continue
        
        distance = haversine_corrected(lat, lon, el_lat, el_lon)
        if distance > radius * 1.05:
            continue
        
        weight = 1 - (distance / radius)
        res = classify_poi(tags)
        if res:
            cat, base_score = res
            weighted_score = base_score * weight
            points_by_cat[cat] += weighted_score
            
            name = tags.get('name', tags.get('name:es', 'Sin nombre'))
            places_list.append({
                'nombre': name,
                'categoria': cat,
                'score': base_score,
                'distancia_m': round(distance, 0),
                'distancia_km': round(distance / 1000, 3),
                'peso': round(weight, 3),
                'latitud': el_lat,
                'longitud': el_lon
            })
    
    total_points = round(sum(points_by_cat.values()), 2)
    breakdown = {cat: round(points_by_cat[cat], 2) for cat in points_by_cat}
    places_list.sort(key=lambda x: x['score'] * x['peso'], reverse=True)
    top_places = places_list[:top_n]
    
    return total_points, breakdown, len(places_list), radius, top_places

if dataset is None or dataset.empty:
    raise ValueError("No hay datos en la tabla seleccionada.")

cols = list(dataset.columns)

lat_col, lon_col = None, None
for c in cols:
    c_low = c.lower().replace('ó','o').replace('ú','u').replace('í','i').replace('á','a').replace('é','e')
    if 'lat' in c_low:
        lat_col = c
    if 'lon' in c_low or 'lng' in c_low:
        lon_col = c

if lat_col is None or lon_col is None:
    raise ValueError(f"No se encontraron columnas de lat/lon. Columnas: {cols}")

dataset[lat_col] = pd.to_numeric(dataset[lat_col], errors='coerce')
dataset[lon_col] = pd.to_numeric(dataset[lon_col], errors='coerce')
dataset_clean = dataset.dropna(subset=[lat_col, lon_col]).copy()

if dataset_clean.empty:
    raise ValueError("No hay filas con coordenadas válidas.")

id_cols = [c for c in cols if c not in [lat_col, lon_col]]
if not id_cols:
    dataset_clean['id'] = range(1, len(dataset_clean)+1)
    id_cols = ['id']

resultados = []

for idx, row in dataset_clean.iterrows():
    lat = row[lat_col]
    lon = row[lon_col]
    meta = {col: row[col] for col in id_cols}
    
    total_points, breakdown, num_pois, radius, places = analyze_location_points(lat, lon, radius=3000)
    
    for p in places:
        fila = {}
        fila.update(meta)
        fila['Latitud'] = lat
        fila['Longitud'] = lon
        fila['Puntuacion_Total'] = total_points
        fila['Num_POIs'] = num_pois
        fila['Radio_Usado_m'] = radius
        for cat, val in breakdown.items():
            fila[f'Pts_{cat}'] = val
        fila['Lugar_Nombre'] = p['nombre']
        fila['Lugar_Categoria'] = p['categoria']
        fila['Lugar_Score_Base'] = p['score']
        fila['Distancia_m'] = p['distancia_m']
        fila['Distancia_km'] = p['distancia_km']
        fila['Peso_Distancia'] = p['peso']
        fila['Lugar_Latitud'] = p['latitud']
        fila['Lugar_Longitud'] = p['longitud']
        resultados.append(fila)

df_final = pd.DataFrame(resultados)

if 'Lugar_Tipo' in df_final.columns:
    df_final = df_final.drop(columns=['Lugar_Tipo'])

df_final = df_final.dropna()

for col in df_final.columns:
    if 'lat' in col.lower() or 'lon' in col.lower():
        df_final[col] = df_final[col].round(6)

df_final