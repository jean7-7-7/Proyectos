import flet as ft
import numpy as np
import pandas as pd
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import interp1d
import os
from datetime import datetime

# ----------------------------------------------------------------------
# SECCIÓN: ESTILOS GLOBALES
# ----------------------------------------------------------------------
COLORES = {
    "bg": "#0f172a",
    "sidebar": "#1e293b",
    "card": "#1e293b",
    "accent": "#06b6d4",
    "accent_hover": "#0891b2",
    "text_main": "#f8fafc",
    "text_sec": "#94a3b8",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
}

def get_text_style(size=14, weight=ft.FontWeight.NORMAL, color=COLORES["text_sec"]):
    return ft.TextStyle(size=size, weight=weight, color=color)

def estilo_boton(icon=None, color_fondo=COLORES["accent"]):
    return ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=12),
        padding=15,
        bgcolor=color_fondo,
        color="#ffffff",
        elevation=5,
        shadow_color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
    )

def estilo_campo(label, width=120):
    return ft.TextField(
        label=label,
        width=width,
        filled=True,
        fill_color=ft.Colors.with_opacity(0.5, COLORES["sidebar"]),
        border_color=COLORES["accent"],
        focused_border_color=COLORES["accent"],
        border_radius=12,
        height=55,
        text_style=get_text_style(16, color="white"),
        label_style=get_text_style(12, color=COLORES["text_sec"]),
        cursor_color=COLORES["accent"],
    )

# ----------------------------------------------------------------------
# SECCIÓN: FUNCIONES DE CÁLCULO
# ----------------------------------------------------------------------
def calcular_B(unit_system, Q_bep, H_bep, N, vis):
    if unit_system.upper() == 'US':
        B = 26.6 * (vis**0.5) * (H_bep**0.0625) / (Q_bep**0.375) / (N**0.25)
    else:
        B = 16.5 * (vis**0.5) * (H_bep**0.0625) / (Q_bep**0.375) / (N**0.25)
    return B

def calcular_CQ(B):
    logB = math.log10(B)
    expo = -0.165 * (logB ** 3.15)
    return math.exp(expo)

def calcular_CH(C_BEP_H, ratio):
    return 1 - (1 - C_BEP_H) * (ratio ** 0.75)

def calcular_Ceta(B):
    exp_interno = -0.0547 * (B ** 0.69)
    return B ** exp_interno

def potencia_vis(Q_vis, H_vis, sg, eta_vis, unit_system='US'):
    if unit_system.upper() == 'US':
        return (Q_vis * H_vis * sg) / (3960 * eta_vis)
    else:
        return (Q_vis * H_vis * sg) / (367 * eta_vis)

def ajustar_polinomio(Q, H, BHP=None):
    Matriz = np.vstack([Q**2, Q, np.ones_like(Q)]).T
    coef_H = np.linalg.lstsq(Matriz, H, rcond=None)[0]
    if BHP is not None:
        coef_BHP = np.linalg.lstsq(Matriz, BHP, rcond=None)[0]
    else:
        coef_BHP = None
    return coef_H, coef_BHP

def generar_curva(Q_min, Q_max, coef_H, coef_BHP, sg, paso=1):
    Q_vals = np.arange(Q_min, Q_max + paso, paso)
    H_vals = coef_H[0]*Q_vals**2 + coef_H[1]*Q_vals + coef_H[2]
    if coef_BHP is not None:
        BHP_vals = coef_BHP[0]*Q_vals**2 + coef_BHP[1]*Q_vals + coef_BHP[2]
        Pot_Hid = (Q_vals * H_vals * sg) / 3960
        Eta = (Pot_Hid / BHP_vals) * 100
        return Q_vals, H_vals, BHP_vals, Pot_Hid, Eta
    else:
        return Q_vals, H_vals

# ----------------------------------------------------------------------
# SECCIÓN: FUNCIONES DE EXPORTACIÓN E IMPORTACIÓN
# ----------------------------------------------------------------------
def exportar_a_excel(filename, water_curve_data, leyes_data=None, viscosidad_data=None):
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            if water_curve_data:
                df_agua = pd.DataFrame({
                    'Q (gpm)': water_curve_data['Q'],
                    'H (ft)': water_curve_data['H'],
                })
                if water_curve_data.get('BHP') is not None:
                    df_agua['BHP (HP)'] = water_curve_data['BHP']
                    df_agua['Pot. Hid (HP)'] = water_curve_data.get('Pot_Hid', [])
                    df_agua['Eta (%)'] = water_curve_data.get('Eta', [])
                df_agua.to_excel(writer, sheet_name='Curva de Agua', index=False)

                coef_H = water_curve_data['coef_H']
                coef_BHP = water_curve_data.get('coef_BHP')
                sg = water_curve_data.get('sg', '')
                q_bep = water_curve_data.get('Q_bep', '')
                h_bep = water_curve_data.get('H_bep', '')
                eta_bep = water_curve_data.get('eta_bep', '')

                coef_df = pd.DataFrame({
                    'Parámetro': ['Coef A', 'Coef B', 'Coef C', 'Gravedad Específica', 'Q BEP', 'H BEP', 'Eta BEP'],
                    'H(Q)': [coef_H[0], coef_H[1], coef_H[2], sg, q_bep, h_bep, eta_bep],
                    'BHP(Q)': [
                        (coef_BHP[0] if coef_BHP is not None else ''),
                        (coef_BHP[1] if coef_BHP is not None else ''),
                        (coef_BHP[2] if coef_BHP is not None else ''),
                        '', '', '', ''
                    ]
                })

                if leyes_data and 'nuevos' in leyes_data:
                    nuevos = leyes_data['nuevos']
                    extra_rows = [
                        ['Nuevo Q BEP', nuevos.get('Q_bep', ''), ''],
                        ['Nuevo H BEP', nuevos.get('H_bep', ''), ''],
                        ['Nuevo Eta BEP', nuevos.get('eta_bep', ''), ''],
                    ]
                    df_extra = pd.DataFrame(extra_rows, columns=['Parámetro', 'H(Q)', 'BHP(Q)'])
                    coef_df = pd.concat([coef_df, df_extra], ignore_index=True)

                if viscosidad_data and 'B' in viscosidad_data:
                    extra_rows = [
                        ['Parámetro B', viscosidad_data['B'], ''],
                        ['CQ', viscosidad_data['CQ'], ''],
                        ['Cη', viscosidad_data['Ceta'], ''],
                    ]
                    ch_list = viscosidad_data.get('CH_list', [])
                    for i, ch in enumerate(ch_list):
                        pct = [60,80,100,120][i] if i < 4 else i+1
                        extra_rows.append([f'CH {pct}%', ch, ''])

                    if 'puntos_vis' in viscosidad_data:
                        pts = viscosidad_data['puntos_vis']
                        incrementos = [p[4] for p in pts if len(p) > 4]
                        if incrementos:
                            promedio_inc = sum(incrementos) / len(incrementos)
                            extra_rows.append(['Incremento P promedio (%)', f'{promedio_inc:.2f}', ''])

                    df_extra = pd.DataFrame(extra_rows, columns=['Parámetro', 'H(Q)', 'BHP(Q)'])
                    coef_df = pd.concat([coef_df, df_extra], ignore_index=True)

                coef_df.to_excel(writer, sheet_name='Coeficientes', index=False)

            if leyes_data and 'nuevos' in leyes_data:
                nuevos = leyes_data['nuevos']
                df_nuevos = pd.DataFrame({
                    'Q (gpm)': nuevos['Q'],
                    'H (ft)': nuevos['H'],
                    'BHP (HP)': nuevos.get('BHP', []),
                    'Pot. Hid (HP)': nuevos.get('Pot_Hid', []),
                    'Eta (%)': nuevos.get('Eta', [])
                })
                df_nuevos.to_excel(writer, sheet_name='Nueva Curva', index=False)

            if viscosidad_data:
                if 'puntos_vis' in viscosidad_data:
                    pts = viscosidad_data['puntos_vis']
                    df_pts = pd.DataFrame({
                        'Q vis (gpm)': [p[0] for p in pts],
                        'H vis (ft)': [p[1] for p in pts],
                        'Eta vis (%)': [p[2]*100 for p in pts],
                        'P vis (HP)': [p[3] for p in pts],
                        'Incremento P (%)': [p[4] for p in pts]
                    })
                    df_pts.to_excel(writer, sheet_name='Viscosidad_Puntos', index=False)

                if 'Q_curve' in viscosidad_data:
                    df_curve = pd.DataFrame({
                        'Q (gpm)': viscosidad_data['Q_curve'],
                        'H (ft)': viscosidad_data['H_curve'],
                        'BHP (HP)': viscosidad_data['BHP_curve'],
                        'Pot. Hid (HP)': viscosidad_data.get('Pot_Hid_curve', []),
                        'Eta (%)': viscosidad_data.get('Eta_curve', [])
                    })
                    df_curve.to_excel(writer, sheet_name='Viscosidad_Curva', index=False)

        return True, f"Datos exportados exitosamente a {filename}"
    except Exception as e:
        return False, f"Error al exportar: {str(e)}"

def exportar_grafica_html(filename, fig):
    try:
        fig.write_html(filename)
        return True, f"Gráfica exportada exitosamente a {filename}"
    except Exception as e:
        return False, f"Error al exportar gráfica: {str(e)}"

def cargar_datos_desde_excel(filename):
    try:
        xlsx = pd.ExcelFile(filename)
        datos = {}
        if 'Curva de Agua' in xlsx.sheet_names:
            df_agua = pd.read_excel(filename, sheet_name='Curva de Agua')
            datos['agua'] = df_agua
        if 'Coeficientes' in xlsx.sheet_names:
            df_coef = pd.read_excel(filename, sheet_name='Coeficientes')
            datos['coeficientes'] = df_coef
        if 'Nueva Curva' in xlsx.sheet_names:
            df_nueva = pd.read_excel(filename, sheet_name='Nueva Curva')
            datos['nueva'] = df_nueva
        if 'Viscosidad_Curva' in xlsx.sheet_names:
            df_visc_curve = pd.read_excel(filename, sheet_name='Viscosidad_Curva')
            datos['visc_curve'] = df_visc_curve
        if 'Viscosidad_Puntos' in xlsx.sheet_names:
            df_visc_pts = pd.read_excel(filename, sheet_name='Viscosidad_Puntos')
            datos['visc_pts'] = df_visc_pts
        return True, datos
    except Exception as e:
        return False, f"Error al cargar: {str(e)}"

# ----------------------------------------------------------------------
# SECCIÓN: ESTADO GLOBAL
# ----------------------------------------------------------------------
class AppState:
    def __init__(self):
        self.water_curve = None
        self.figura_agua = None
        self.figura_leyes = None
        self.figura_visc = None
        self.leyes_data = None
        self.visc_data = None
        self.output_dir = None
        self.original_points = None  # Siempre serán los 4 puntos principales (sin shut-off)

app_state = AppState()

# ----------------------------------------------------------------------
# SECCIÓN: FUNCIONES PARA GRÁFICOS PLOTLY (ESTILO OSCURO)
# ----------------------------------------------------------------------
def crear_figura_agua(Q, H, BHP=None, Pot_Hid=None, Eta=None, titulo="Curva de Bomba (Agua)"):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=Q, y=H, mode="lines+markers", name="H-Q (Altura, ft)",
        line=dict(color="cyan", width=2), marker=dict(size=6),
        hovertemplate="Caudal: %{x:.1f} gpm<br>Altura: %{y:.1f} ft<extra></extra>"
    ), secondary_y=False)
    if BHP is not None:
        fig.add_trace(go.Scatter(
            x=Q, y=BHP, mode="lines", name="BHP (HP)",
            line=dict(color="red", width=2, dash="dash"),
            hovertemplate="Caudal: %{x:.1f} gpm<br>BHP: %{y:.2f} HP<extra></extra>"
        ), secondary_y=True)
    if Pot_Hid is not None:
        fig.add_trace(go.Scatter(
            x=Q, y=Pot_Hid, mode="lines", name="Potencia Hidráulica (HP)",
            line=dict(color="lime", width=2),
            hovertemplate="Caudal: %{x:.1f} gpm<br>Pot. Hid: %{y:.3f} HP<extra></extra>"
        ), secondary_y=True)
    if Eta is not None:
        fig.add_trace(go.Scatter(
            x=Q, y=Eta, mode="lines", name="Eficiencia (%)",
            line=dict(color="white", width=2, dash="dash"),
            hovertemplate="Caudal: %{x:.1f} gpm<br>Eficiencia: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)
        idx_max = np.nanargmax(Eta)
        Q_max, H_max, eta_max = Q[idx_max], H[idx_max], Eta[idx_max]
        fig.add_trace(go.Scatter(
            x=[Q_max], y=[H_max], mode="markers+text",
            name="Máxima eficiencia",
            marker=dict(size=12, color="gold", symbol="star"),
            text=[f"{eta_max:.1f}%"], textposition="top center",
            hovertemplate=f"Caudal: {Q_max:.1f} gpm<br>Altura: {H_max:.1f} ft<br>Eficiencia: {eta_max:.1f}%<extra></extra>"
        ), secondary_y=False)

    fig.update_layout(
        title=titulo, xaxis_title="Caudal (gpm)", hovermode="x unified",
        template="plotly_dark", width=900, height=500,
        legend=dict(title="Series", bgcolor="rgba(0,0,0,0.5)")
    )
    fig.update_yaxes(title_text="Altura (ft)", secondary_y=False, gridcolor="#334155")
    fig.update_yaxes(title_text="Potencia / BHP / Eficiencia (HP / %)", secondary_y=True, gridcolor="#334155")
    fig.update_xaxes(gridcolor="#334155")
    return fig

def crear_figura_leyes(Q_orig, H_orig, BHP_orig, Pot_Hid_orig, Eta_orig,
                       Q_new, H_new, BHP_new, Pot_Hid_new, Eta_new, titulo, sg=1.0):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Curva original
    fig.add_trace(go.Scatter(
        x=Q_orig, y=H_orig, mode="lines", name="H-Q Original (ft)",
        line=dict(color="cyan"), hovertemplate="Caudal: %{x:.1f} gpm<br>Altura: %{y:.1f} ft<extra></extra>"
    ), secondary_y=False)
    if BHP_orig is not None:
        fig.add_trace(go.Scatter(
            x=Q_orig, y=BHP_orig, mode="lines", name="BHP Original (HP)",
            line=dict(color="red", dash="dash"), hovertemplate="Caudal: %{x:.1f} gpm<br>BHP: %{y:.2f} HP<extra></extra>"
        ), secondary_y=True)
    if Pot_Hid_orig is not None:
        fig.add_trace(go.Scatter(
            x=Q_orig, y=Pot_Hid_orig, mode="lines", name="Pot. Hid. Original (HP)",
            line=dict(color="lime", dash="dot"), hovertemplate="Caudal: %{x:.1f} gpm<br>Pot. Hid: %{y:.3f} HP<extra></extra>"
        ), secondary_y=True)
    if Eta_orig is not None:
        fig.add_trace(go.Scatter(
            x=Q_orig, y=Eta_orig, mode="lines", name="Eta Original (%)",
            line=dict(color="white", dash="dash"), hovertemplate="Caudal: %{x:.1f} gpm<br>Eficiencia: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)
        idx_max_orig = np.argmax(Eta_orig)
        fig.add_trace(go.Scatter(
            x=[Q_orig[idx_max_orig]], y=[H_orig[idx_max_orig]], mode="markers",
            name="Máxima eficiencia", legendgroup="bep", showlegend=True,
            marker=dict(color="gold", size=10, symbol="star"),
            hovertemplate=f"BEP Original: Q={Q_orig[idx_max_orig]:.1f}, H={H_orig[idx_max_orig]:.1f}, Eta={Eta_orig[idx_max_orig]:.1f}%<extra></extra>"
        ), secondary_y=False)

    # Curva nueva (afinidad)
    fig.add_trace(go.Scatter(
        x=Q_new, y=H_new, mode="lines", name="H-Q Nuevo (ft)",
        line=dict(color="yellow"), hovertemplate="Caudal: %{x:.1f} gpm<br>Altura: %{y:.1f} ft<extra></extra>"
    ), secondary_y=False)
    if BHP_new is not None:
        fig.add_trace(go.Scatter(
            x=Q_new, y=BHP_new, mode="lines", name="BHP Nuevo (HP)",
            line=dict(color="orange", dash="dash"), hovertemplate="Caudal: %{x:.1f} gpm<br>BHP: %{y:.2f} HP<extra></extra>"
        ), secondary_y=True)
    if Pot_Hid_new is not None:
        fig.add_trace(go.Scatter(
            x=Q_new, y=Pot_Hid_new, mode="lines", name="Pot. Hid. Nuevo (HP)",
            line=dict(color="lime", width=2), hovertemplate="Caudal: %{x:.1f} gpm<br>Pot. Hid: %{y:.3f} HP<extra></extra>"
        ), secondary_y=True)
    if Eta_new is not None:
        fig.add_trace(go.Scatter(
            x=Q_new, y=Eta_new, mode="lines", name="Eta Nuevo (%)",
            line=dict(color="white", dash="dot"), hovertemplate="Caudal: %{x:.1f} gpm<br>Eficiencia: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)
        idx_max_new = np.argmax(Eta_new)
        fig.add_trace(go.Scatter(
            x=[Q_new[idx_max_new]], y=[H_new[idx_max_new]], mode="markers",
            name="Máxima eficiencia", legendgroup="bep", showlegend=False,
            marker=dict(color="gold", size=10, symbol="star"),
            hovertemplate=f"BEP Nuevo: Q={Q_new[idx_max_new]:.1f}, H={H_new[idx_max_new]:.1f}, Eta={Eta_new[idx_max_new]:.1f}%<extra></extra>"
        ), secondary_y=False)

    fig.update_layout(
        title=titulo, xaxis_title="Caudal (gpm)", hovermode="x unified",
        template="plotly_dark", width=900, height=500,
        legend=dict(title="Series", bgcolor="rgba(0,0,0,0.5)")
    )
    fig.update_yaxes(title_text="Altura (ft)", secondary_y=False, gridcolor="#334155")
    fig.update_yaxes(title_text="Potencia / BHP / Eficiencia (HP / %)", secondary_y=True, gridcolor="#334155")
    fig.update_xaxes(gridcolor="#334155")
    return fig

def crear_figura_viscosidad(Q_agua, H_agua, BHP_agua, Pot_Hid_agua, Eta_agua,
                            Q_vis, H_vis, BHP_vis, Pot_Hid_vis, Eta_vis,
                            Q_puntos, H_puntos, BHP_puntos, titulo, sg_agua=1.0, sg_visc=1.0):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Curva de agua
    fig.add_trace(go.Scatter(
        x=Q_agua, y=H_agua, mode="lines", name="H-Q Agua (ft)",
        line=dict(color="cyan"), hovertemplate="Caudal: %{x:.1f} gpm<br>Altura: %{y:.1f} ft<extra></extra>"
    ), secondary_y=False)
    if BHP_agua is not None:
        fig.add_trace(go.Scatter(
            x=Q_agua, y=BHP_agua, mode="lines", name="BHP Agua (HP)",
            line=dict(color="red", dash="dash"), hovertemplate="Caudal: %{x:.1f} gpm<br>BHP: %{y:.2f} HP<extra></extra>"
        ), secondary_y=True)
    if Pot_Hid_agua is not None:
        fig.add_trace(go.Scatter(
            x=Q_agua, y=Pot_Hid_agua, mode="lines", name="Pot. Hid. Agua (HP)",
            line=dict(color="lime", dash="dot"), hovertemplate="Caudal: %{x:.1f} gpm<br>Pot. Hid: %{y:.3f} HP<extra></extra>"
        ), secondary_y=True)
    if Eta_agua is not None:
        fig.add_trace(go.Scatter(
            x=Q_agua, y=Eta_agua, mode="lines", name="Eta Agua (%)",
            line=dict(color="white", dash="dash"), hovertemplate="Caudal: %{x:.1f} gpm<br>Eficiencia: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)
        idx_max_agua = np.argmax(Eta_agua)
        fig.add_trace(go.Scatter(
            x=[Q_agua[idx_max_agua]], y=[H_agua[idx_max_agua]], mode="markers",
            name="Máxima eficiencia", legendgroup="bep", showlegend=True,
            marker=dict(color="gold", size=10, symbol="star"),
            hovertemplate=f"BEP Agua: Q={Q_agua[idx_max_agua]:.1f}, H={H_agua[idx_max_agua]:.1f}, Eta={Eta_agua[idx_max_agua]:.1f}%<extra></extra>"
        ), secondary_y=False)

    # Curva viscosa
    fig.add_trace(go.Scatter(
        x=Q_vis, y=H_vis, mode="lines", name="H-Q Viscoso (ft)",
        line=dict(color="magenta"), hovertemplate="Caudal: %{x:.1f} gpm<br>Altura: %{y:.1f} ft<extra></extra>"
    ), secondary_y=False)
    if BHP_vis is not None:
        fig.add_trace(go.Scatter(
            x=Q_vis, y=BHP_vis, mode="lines", name="BHP Viscoso (HP)",
            line=dict(color="orange", dash="dash"), hovertemplate="Caudal: %{x:.1f} gpm<br>BHP: %{y:.2f} HP<extra></extra>"
        ), secondary_y=True)
    if Pot_Hid_vis is not None:
        fig.add_trace(go.Scatter(
            x=Q_vis, y=Pot_Hid_vis, mode="lines", name="Pot. Hid. Viscoso (HP)",
            line=dict(color="lime", width=2), hovertemplate="Caudal: %{x:.1f} gpm<br>Pot. Hid: %{y:.3f} HP<extra></extra>"
        ), secondary_y=True)
    if Eta_vis is not None:
        fig.add_trace(go.Scatter(
            x=Q_vis, y=Eta_vis, mode="lines", name="Eta Viscoso (%)",
            line=dict(color="white", dash="dot"), hovertemplate="Caudal: %{x:.1f} gpm<br>Eficiencia: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)
        idx_max_vis = np.argmax(Eta_vis)
        fig.add_trace(go.Scatter(
            x=[Q_vis[idx_max_vis]], y=[H_vis[idx_max_vis]], mode="markers",
            name="Máxima eficiencia", legendgroup="bep", showlegend=False,
            marker=dict(color="gold", size=10, symbol="star"),
            hovertemplate=f"BEP Viscoso: Q={Q_vis[idx_max_vis]:.1f}, H={H_vis[idx_max_vis]:.1f}, Eta={Eta_vis[idx_max_vis]:.1f}%<extra></extra>"
        ), secondary_y=False)

    # Puntos base de corrección
    fig.add_trace(go.Scatter(
        x=Q_puntos, y=H_puntos, mode="markers", name="Puntos viscosos (base)",
        marker=dict(color="magenta", size=8), hovertemplate="Caudal: %{x:.1f} gpm<br>Altura: %{y:.1f} ft<extra></extra>"
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=Q_puntos, y=BHP_puntos, mode="markers", name="Puntos BHP Viscoso",
        marker=dict(color="orange", size=8), hovertemplate="Caudal: %{x:.1f} gpm<br>BHP: %{y:.2f} HP<extra></extra>"
    ), secondary_y=True)

    fig.update_layout(
        title=titulo, xaxis_title="Caudal (gpm)", hovermode="x unified",
        template="plotly_dark", width=900, height=500,
        legend=dict(title="Series", bgcolor="rgba(0,0,0,0.5)")
    )
    fig.update_yaxes(title_text="Altura (ft)", secondary_y=False, gridcolor="#334155")
    fig.update_yaxes(title_text="Potencia / BHP / Eficiencia (HP / %)", secondary_y=True, gridcolor="#334155")
    fig.update_xaxes(gridcolor="#334155")
    return fig

# ----------------------------------------------------------------------
# SECCIÓN: APLICACIÓN PRINCIPAL (FLET)
# ----------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "Analizador de Bombas Centrífugas"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = ft.Colors.TRANSPARENT

    # Panel informativo (esquina inferior izquierda)
    info_panel = ft.Container(
        content=ft.Text("", color=ft.Colors.WHITE70, size=11),
        alignment=ft.alignment.Alignment(-1, 1),
        padding=ft.Padding.all(4),
        bgcolor=ft.Colors.with_opacity(0.7, COLORES["sidebar"]),
        border_radius=ft.BorderRadius.all(6),
        width=180, height=60,
        animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
    )

    def set_info_message(text, is_error=False):
        color = ft.Colors.RED_300 if is_error else ft.Colors.WHITE70
        info_panel.content = ft.Text(text, color=color, size=11)
        info_panel.update()

    def show_message(text):
        page.snack_bar = ft.SnackBar(content=ft.Text(text, color="white"), bgcolor=COLORES["success"], open=True)
        page.update()

    def show_error(text):
        page.snack_bar = ft.SnackBar(content=ft.Text(text, color="white"), bgcolor=COLORES["danger"], open=True)
        page.update()

    # Contenedor principal con barra lateral y área de contenido
    main_container = ft.Container(
        expand=True,
        bgcolor=COLORES["bg"],
        content=ft.Row(
            spacing=0,
            controls=[
                ft.Container(
                    width=220,
                    content=ft.Column(alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    bgcolor=COLORES["sidebar"],
                    border_radius=ft.BorderRadius.only(top_right=25, bottom_right=25),
                    padding=ft.Padding.symmetric(vertical=30, horizontal=15),
                    shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
                ft.Container(
                    expand=True,
                    padding=40,
                    content=ft.Column(
                        controls=[ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)],
                        spacing=6,
                    ),
                ),
            ],
        ),
    )

    page.add(ft.Stack([main_container, info_panel], expand=True))

    content_area = main_container.content.controls[2].content.controls[0]
    sidebar_area = main_container.content.controls[0].content

    def ensure_output_dir(name=None):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            script_dir = os.getcwd()
        path = os.path.join(script_dir, "Resultados_bomba") if name is None else os.path.abspath(name)
        os.makedirs(path, exist_ok=True)
        app_state.output_dir = path
        set_info_message(f"Carpeta: {path}")

    ensure_output_dir()
    selected_button_index = [0]

    def cambiar_contenido(index):
        if len(content_area.controls) == 0:
            vista0 = crear_vista_agua()
            vista1 = crear_vista_leyes()
            vista2 = crear_vista_viscosidad()
            vista0.visible = (index == 0)
            vista1.visible = (index == 1)
            vista2.visible = (index == 2)
            content_area.controls.extend([vista0, vista1, vista2])
        else:
            for i, c in enumerate(content_area.controls):
                c.visible = (i == index)
        page.update()

    def crear_boton_menu(index, label, icon):
        def click_handler(e):
            selected_button_index[0] = index
            cambiar_contenido(index)
            actualizar_botones()
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=20, color=COLORES["text_sec"]),
                    ft.Text(label, size=14, weight=ft.FontWeight.W_500, color=COLORES["text_sec"])
                ],
                spacing=10, alignment=ft.MainAxisAlignment.CENTER
            ),
            on_click=click_handler,
            width=190, height=55, ink=True,
            border_radius=ft.BorderRadius.only(top_left=15, bottom_left=15),
            bgcolor=ft.Colors.TRANSPARENT,
            padding=ft.Padding.symmetric(horizontal=15),
        )

    def actualizar_botones():
        for i, boton in enumerate(botones_menu):
            if i == selected_button_index[0]:
                boton.bgcolor = ft.Colors.with_opacity(0.15, COLORES["accent"])
                boton.content.controls[0].color = COLORES["accent"]
                boton.content.controls[1].color = "white"
            else:
                boton.bgcolor = ft.Colors.TRANSPARENT
                boton.content.controls[0].color = COLORES["text_sec"]
                boton.content.controls[1].color = COLORES["text_sec"]
        page.update()

    botones_menu = [
        crear_boton_menu(0, "Curva de Agua", ft.Icons.WATER_DROP),
        crear_boton_menu(1, "Leyes de Afinidad", ft.Icons.STRAIGHTEN),
        crear_boton_menu(2, "Corrección por\nViscosidad", ft.Icons.OIL_BARREL),
    ]

    sidebar_area.expand = True
    top_spacer = ft.Container(expand=True)
    bottom_spacer = ft.Container(expand=True)
    credit_text = ft.Text("Realizado por: Jean Morales", size=12, color=COLORES["text_sec"], text_align=ft.TextAlign.CENTER)
    sidebar_area.controls = [top_spacer] + botones_menu + [bottom_spacer, credit_text]
    actualizar_botones()

    HAVE_HTML = hasattr(ft, "Html")
    if HAVE_HTML:
        grafico_agua = ft.Html(content="", expand=True)
        grafico_leyes = ft.Html(content="", expand=True)
        grafico_visc = ft.Html(content="", expand=True)
    else:
        grafico_agua = ft.Text("Gráfico de agua (placeholder)")
        grafico_leyes = ft.Text("Gráfico leyes (placeholder)")
        grafico_visc = ft.Text("Gráfico viscosidad (placeholder)")

    # ------------------------------------------------------------------
    # VISTA 1: CURVA DE AGUA (con shut-off, pero guarda los 4 puntos principales)
    # ------------------------------------------------------------------
    def crear_vista_agua():
        puntos_q = []
        puntos_h = []
        puntos_bhp = []
        puntos_eta = []
        defaults_q = ["264", "352", "440", "528"]
        defaults_h = ["340", "323", "300", "272"]
        defaults_bhp = ["34", "40", "45", "50"]
        defaults_eta = ["60.2", "66.0", "68.0", "66.0"]

        modo = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="hq", label="Solo H-Q"),
                ft.Radio(value="bhp", label="Con BHP"),
                ft.Radio(value="eta", label="Con Eficiencia"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            value="bhp"
        )

        # Controles para shut-off
        usar_shutoff = ft.Checkbox(label="Incluir punto de shut-off (Q=0)", value=False)
        h_shutoff = estilo_campo("Altura a Q=0 (ft)", width=120)
        h_shutoff.value = "356.1"
        h_shutoff.visible = False
        shutoff_bhp = estilo_campo("BHP a Q=0 (HP)", width=120)
        shutoff_bhp.value = "25"
        shutoff_bhp.visible = False

        def toggle_shutoff(e):
            if usar_shutoff.value:
                # Solo permitir shut-off en modos bhp o eta
                if modo.value == "hq":
                    usar_shutoff.value = False
                    set_info_message("El modo Solo H-Q no permite shut-off", is_error=True)
                    page.update()
                    return
                h_shutoff.visible = True
                shutoff_bhp.visible = True
            else:
                h_shutoff.visible = False
                shutoff_bhp.visible = False
            page.update()
        usar_shutoff.on_change = toggle_shutoff

        bhp_fields = []
        eta_fields = []

        for i in range(4):
            q = estilo_campo(f"Q{i+1} (gpm)", width=120)
            q.value = defaults_q[i]
            h = estilo_campo(f"H{i+1} (ft)", width=120)
            h.value = defaults_h[i]
            bhp = estilo_campo(f"BHP{i+1} (HP)", width=120)
            bhp.value = defaults_bhp[i]
            eta = estilo_campo(f"Eta{i+1} (%)", width=120)
            eta.value = defaults_eta[i]
            puntos_q.append(q)
            puntos_h.append(h)
            puntos_bhp.append(bhp)
            puntos_eta.append(eta)
            bhp_fields.append(bhp)
            eta_fields.append(eta)

        def cambiar_modo(e=None):
            if modo.value == "hq":
                for b in bhp_fields:
                    b.visible = False
                for e_ in eta_fields:
                    e_.visible = False
            elif modo.value == "bhp":
                for b in bhp_fields:
                    b.visible = True
                for e_ in eta_fields:
                    e_.visible = False
            else:  # eta
                for b in bhp_fields:
                    b.visible = False
                for e_ in eta_fields:
                    e_.visible = True
            # Si se cambia a modo hq, desactivar shut-off si estaba activo
            if modo.value == "hq" and usar_shutoff.value:
                usar_shutoff.value = False
                h_shutoff.visible = False
                shutoff_bhp.visible = False
                set_info_message("Shut-off desactivado porque el modo Solo H-Q no lo soporta", is_error=True)
            # Si está en modo bhp o eta y shut-off activo, mostrar los campos
            elif usar_shutoff.value:
                h_shutoff.visible = True
                shutoff_bhp.visible = True
            else:
                h_shutoff.visible = False
                shutoff_bhp.visible = False
            page.update()

        modo.on_change = cambiar_modo
        cambiar_modo()

        sg_agua = estilo_campo("Gravedad específica (agua)", width=220)
        sg_agua.value = "0.9"
        coef_text = ft.Text("Coeficientes: ", size=14, color=COLORES["text_sec"])

        def generar_curva_agua(e):
            set_info_message("Generando curva de agua...")
            try:
                Q_pts = [float(q.value) for q in puntos_q]
                H_pts = [float(h.value) for h in puntos_h]
                sg = float(sg_agua.value)

                # Guardar los 4 puntos originales (sin shut-off)
                if modo.value == "bhp":
                    BHP_orig = [float(b.value) for b in puntos_bhp]
                    Eta_orig = [(Q_pts[i] * H_pts[i] * sg) / (3960 * BHP_orig[i]) * 100 for i in range(4)]
                    app_state.original_points = [(Q_pts[i], H_pts[i], BHP_orig[i], Eta_orig[i]) for i in range(4)]
                elif modo.value == "eta":
                    Eta_orig = [float(e_.value) for e_ in puntos_eta]
                    BHP_orig = [(Q_pts[i] * H_pts[i] * sg) / (3960 * (Eta_orig[i]/100)) for i in range(4)]
                    app_state.original_points = [(Q_pts[i], H_pts[i], BHP_orig[i], Eta_orig[i]) for i in range(4)]
                else:
                    app_state.original_points = None

                # Construir listas para el polinomio (pueden incluir shut-off)
                Q_list = Q_pts.copy()
                H_list = H_pts.copy()
                if modo.value == "bhp":
                    BHP_list = [float(b.value) for b in puntos_bhp]
                elif modo.value == "eta":
                    Eta_list = [float(e_.value) for e_ in puntos_eta]
                    BHP_list = None
                else:
                    BHP_list = None
                    Eta_list = None

                if usar_shutoff.value:
                    h0 = float(h_shutoff.value)
                    bhp0 = float(shutoff_bhp.value)
                    Q_list.insert(0, 0.0)
                    H_list.insert(0, h0)
                    if modo.value == "bhp":
                        BHP_list.insert(0, bhp0)
                        # Calcular eficiencia para todos los puntos
                        Eta_list = []
                        for i in range(len(Q_list)):
                            if BHP_list[i] != 0:
                                eta = (Q_list[i] * H_list[i] * sg) / (3960 * BHP_list[i]) * 100
                            else:
                                eta = 0.0
                            Eta_list.append(eta)
                    elif modo.value == "eta":
                        # Insertar BHP0 al inicio
                        BHP_list = [bhp0] + [(Q_list[i] * H_list[i] * sg) / (3960 * (Eta_list[i-1]/100)) for i in range(1, len(Q_list))]
                        Eta_list.insert(0, 0.0)
                else:
                    if modo.value == "bhp":
                        Eta_list = [(Q_list[i] * H_list[i] * sg) / (3960 * BHP_list[i]) * 100 for i in range(4)]
                    elif modo.value == "eta":
                        BHP_list = [(Q_list[i] * H_list[i] * sg) / (3960 * (Eta_list[i]/100)) for i in range(4)]
                    else:
                        BHP_list = None
                        Eta_list = None
            except ValueError:
                set_info_message("Error: valores numéricos inválidos", is_error=True)
                return

            if BHP_list is not None:
                coef_H, coef_BHP = ajustar_polinomio(np.array(Q_list), np.array(H_list), np.array(BHP_list))
            else:
                coef_H, coef_BHP = ajustar_polinomio(np.array(Q_list), np.array(H_list), None)

            Q_min = 0 if usar_shutoff.value else min(Q_list)
            Q_max = max(Q_list)
            paso = 1

            if BHP_list is not None:
                Q_vals, H_vals, BHP_vals, Pot_Hid, Eta = generar_curva(Q_min, Q_max, coef_H, coef_BHP, sg, paso)
                idx_max = np.argmax(Eta)
                app_state.water_curve = {
                    'Q': Q_vals, 'H': H_vals, 'BHP': BHP_vals, 'Pot_Hid': Pot_Hid, 'Eta': Eta,
                    'coef_H': coef_H, 'coef_BHP': coef_BHP, 'sg': sg,
                    'Q_bep': Q_vals[idx_max], 'H_bep': H_vals[idx_max], 'eta_bep': Eta[idx_max]
                }
                fig = crear_figura_agua(Q_vals, H_vals, BHP_vals, Pot_Hid, Eta)
            else:
                Q_vals, H_vals = generar_curva(Q_min, Q_max, coef_H, None, sg, paso)
                app_state.water_curve = {'Q': Q_vals, 'H': H_vals, 'coef_H': coef_H, 'coef_BHP': None, 'sg': sg,
                                         'Q_bep': None, 'H_bep': None, 'eta_bep': None}
                fig = crear_figura_agua(Q_vals, H_vals)

            coef_text.value = f"Coeficientes H(Q): A={coef_H[0]:.4f}, B={coef_H[1]:.4f}, C={coef_H[2]:.2f}"
            if coef_BHP is not None:
                coef_text.value += f" | BHP(Q): A={coef_BHP[0]:.4f}, B={coef_BHP[1]:.4f}, C={coef_BHP[2]:.2f}"

            app_state.figura_agua = fig
            if HAVE_HTML:
                try:
                    grafico_agua.content = app_state.figura_agua.to_html(full_html=True, include_plotlyjs='cdn')
                except Exception as ex:
                    grafico_agua.content = f"<div style='color:white; text-align:center; padding:20px;'>Error al renderizar gráfico: {ex}</div>"
            else:
                grafico_agua.value = "Gráfico generado (simulado)"
            set_info_message("Curva de agua generada")
            page.update()

        boton_generar = ft.Button("Generar curva", on_click=generar_curva_agua, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.PLAY_ARROW)

        def exportar_datos(e):
            if app_state.water_curve is None:
                set_info_message("Primero genere una curva", is_error=True)
                return
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"datos_bomba_{timestamp}.xlsx"
                filepath = os.path.join(app_state.output_dir, filename) if app_state.output_dir else filename
                success, msg = exportar_a_excel(filepath, app_state.water_curve)
                set_info_message(msg)
            except Exception as ex:
                set_info_message(f"Error exportar: {ex}", is_error=True)

        def exportar_grafica(e):
            if app_state.figura_agua is None:
                set_info_message("Primero genere una curva", is_error=True)
                return
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"grafica_agua_{timestamp}.html"
                filepath = os.path.join(app_state.output_dir, filename) if app_state.output_dir else filename
                success, msg = exportar_grafica_html(filepath, app_state.figura_agua)
                set_info_message(msg)
            except Exception as ex:
                set_info_message(f"Error exportar gráfica: {ex}", is_error=True)

        def cargar_datos(e):
            set_info_message("Función de carga no modificada en esta versión")
            pass

        def abrir_carpeta(e):
            path = app_state.output_dir
            try:
                if os.name == 'nt':
                    import subprocess
                    subprocess.Popen(['explorer', os.path.normpath(path)])
                else:
                    try:
                        import subprocess, sys
                        if sys.platform == 'darwin':
                            subprocess.Popen(['open', path])
                        else:
                            subprocess.Popen(['xdg-open', path])
                    except Exception:
                        os.startfile(path)
            except Exception as ex:
                set_info_message(f"No se puede abrir carpeta: {ex}", is_error=True)

        boton_exportar_datos = ft.Button("Exportar Excel", on_click=exportar_datos, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.TABLE_CHART)
        boton_exportar_grafica = ft.Button("Exportar Gráfica HTML", on_click=exportar_grafica, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.IMAGE)
        boton_cargar = ft.Button("Cargar Datos", on_click=cargar_datos, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.UPLOAD_FILE)
        boton_carpeta = ft.Button("Abrir Carpeta", on_click=abrir_carpeta, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.FOLDER_OPEN)

        input_container = ft.Container(
            content=ft.Column([
                ft.Text("Puntos de la Curva", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Row([modo], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([usar_shutoff, h_shutoff, shutoff_bhp], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Column([
                    ft.Row([q, h, bhp, eta], spacing=15, alignment=ft.MainAxisAlignment.CENTER)
                    for q, h, bhp, eta in zip(puntos_q, puntos_h, puntos_bhp, puntos_eta)
                ], spacing=5),
                ft.Row([sg_agua, boton_generar], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        acciones_container = ft.Container(
            content=ft.Column([
                ft.Text("Acciones", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Row([boton_exportar_datos, boton_exportar_grafica, boton_cargar, boton_carpeta], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(content=coef_text, bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE), border_radius=10, padding=15, margin=ft.Margin.only(top=10)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        return ft.Column([
            ft.Text("Curva de Bomba (Agua)", size=28, weight=ft.FontWeight.BOLD, color="white"),
            input_container, acciones_container,
            ft.Container(content=grafico_agua, bgcolor=COLORES["card"], border_radius=20, padding=10,
                         shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))),
        ], spacing=25, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    # ------------------------------------------------------------------
    # VISTA 2: LEYES DE AFINIDAD (CORREGIDA)
    # ------------------------------------------------------------------
    def crear_vista_leyes():
        diam_actual = estilo_campo("Característica Actual", width=150)
        diam_nuevo = estilo_campo("Nueva Característica", width=150)

        def calcular_leyes(e):
            if app_state.water_curve is None:
                set_info_message("Primero genere una curva de agua (Opción 1)", is_error=True)
                return
            set_info_message("Calculando leyes de afinidad...")
            try:
                D1 = float(diam_actual.value)
                D2 = float(diam_nuevo.value)
            except ValueError:
                set_info_message("Ingrese diámetros válidos", is_error=True)
                return

            factor = D2 / D1
            w = app_state.water_curve
            Q_new = w['Q'] * factor
            H_new = w['H'] * (factor ** 2)
            if w.get('BHP') is not None:
                Pot_Hid_new = (Q_new * H_new * w['sg']) / 3960
                Eta_new = w['Eta']
                with np.errstate(divide='ignore', invalid='ignore'):
                    BHP_new = np.where(Eta_new != 0, Pot_Hid_new / (Eta_new / 100), 0.0)
                if Q_new[0] == 0:
                    BHP_new[0] = 0.0
                    Pot_Hid_new[0] = 0.0
                    Eta_new[0] = 0.0
            else:
                BHP_new = None
                Pot_Hid_new = None
                Eta_new = None

            Q_list = Q_new.tolist() if hasattr(Q_new, 'tolist') else list(Q_new)
            H_list = H_new.tolist() if hasattr(H_new, 'tolist') else list(H_new)
            BHP_list = BHP_new.tolist() if BHP_new is not None else []
            Pot_Hid_list = Pot_Hid_new.tolist() if Pot_Hid_new is not None else []
            Eta_list = Eta_new.tolist() if Eta_new is not None else []

            if BHP_new is not None:
                idx_max_new = np.argmax(Eta_new)
                Q_bep_new = Q_new[idx_max_new]
                H_bep_new = H_new[idx_max_new]
                eta_bep_new = Eta_new[idx_max_new]
            else:
                Q_bep_new = H_bep_new = eta_bep_new = None

            nuevos = {
                'Q': Q_list,
                'H': H_list,
                'BHP': BHP_list,
                'Pot_Hid': Pot_Hid_list,
                'Eta': Eta_list,
                'Q_bep': Q_bep_new,
                'H_bep': H_bep_new,
                'eta_bep': eta_bep_new
            }

            app_state.leyes_data = {'nuevos': nuevos, 'factor': factor}

            fig = crear_figura_leyes(
                w['Q'], w['H'], w.get('BHP'), w.get('Pot_Hid'), w.get('Eta'),
                Q_new, H_new, BHP_new, Pot_Hid_new, Eta_new,
                f"Leyes de Afinidad (D2/D1 = {factor:.3f})", sg=w.get('sg', 1.0)
            )

            app_state.figura_leyes = fig
            if HAVE_HTML:
                try:
                    grafico_leyes.content = app_state.figura_leyes.to_html(full_html=True, include_plotlyjs='cdn')
                except Exception as ex:
                    grafico_leyes.content = f"<div style='color:white; text-align:center; padding:20px;'>Error al renderizar gráfico: {ex}</div>"
            else:
                grafico_leyes.value = "Gráfico de leyes generado (simulado)"
            set_info_message("Leyes de afinidad calculadas")
            page.update()

        boton_calcular = ft.Button("Calcular", on_click=calcular_leyes, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.CALCULATE)

        def exportar_leyes_datos(e):
            if app_state.leyes_data is None:
                set_info_message("Primero calcule las leyes de afinidad", is_error=True)
                return
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"leyes_afinidad_{timestamp}.xlsx"
                filepath = os.path.join(app_state.output_dir, filename) if app_state.output_dir else filename
                success, msg = exportar_a_excel(filepath, app_state.water_curve, leyes_data=app_state.leyes_data)
                set_info_message(msg)
            except Exception as ex:
                set_info_message(f"Error al exportar leyes: {ex}", is_error=True)

        def exportar_leyes_grafica(e):
            if app_state.figura_leyes is None:
                set_info_message("Primero calcule las leyes de afinidad", is_error=True)
                return
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"grafica_leyes_{timestamp}.html"
                filepath = os.path.join(app_state.output_dir, filename) if app_state.output_dir else filename
                success, msg = exportar_grafica_html(filepath, app_state.figura_leyes)
                set_info_message(msg)
            except Exception as ex:
                set_info_message(f"Error al exportar gráfica de leyes: {ex}", is_error=True)

        boton_exp_leyes = ft.Button("Exportar Excel", on_click=exportar_leyes_datos, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.TABLE_CHART)
        boton_exp_leyes_graf = ft.Button("Exportar Gráfica", on_click=exportar_leyes_grafica, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.IMAGE)

        input_container = ft.Container(
            content=ft.Column([
                ft.Text("Parámetros de Conversión", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Row([diam_actual, diam_nuevo, boton_calcular], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        acciones_container = ft.Container(
            content=ft.Column([
                ft.Text("Exportar Resultados", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Row([boton_exp_leyes, boton_exp_leyes_graf], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        return ft.Column([
            ft.Text("Leyes de Afinidad", size=28, weight=ft.FontWeight.BOLD, color="white"),
            input_container, acciones_container,
            ft.Container(content=grafico_leyes, bgcolor=COLORES["card"], border_radius=20, padding=10,
                         shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))),
        ], spacing=25, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    # ------------------------------------------------------------------
    # VISTA 3: CORRECCIÓN POR VISCOSIDAD (manual usa los 4 puntos para BEP pero la curva completa con shut-off)
    # ------------------------------------------------------------------
    def crear_vista_viscosidad():
        rpm_field = estilo_campo("Velocidad (rpm)", width=120)
        vis_field = estilo_campo("Viscosidad (cSt)", width=120)
        sg_visc_field = estilo_campo("Gravedad específica (viscoso)", width=200)

        bep_option = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="auto", label="Automático (usar BEP de la curva generada)"),
                ft.Radio(value="manual", label="Manual (usar punto de máxima eficiencia de los 4 ingresados)"),
            ]),
            value="auto"
        )

        tabla = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Q vis (gpm)", color="white")),
                ft.DataColumn(ft.Text("H vis (ft)", color="white")),
                ft.DataColumn(ft.Text("Eta vis", color="white")),
                ft.DataColumn(ft.Text("P vis (HP)", color="white")),
                ft.DataColumn(ft.Text("Inc P (%)", color="white")),
            ],
            rows=[], width=700,
            heading_row_color=ft.Colors.with_opacity(0.3, COLORES["accent"]),
            data_row_color={"hovered": ft.Colors.with_opacity(0.1, COLORES["accent"])},
            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            border_radius=10,
        )

        coef_visc_text = ft.Text("Parámetros de corrección: ", size=14, color=COLORES["text_sec"])

        def corregir_visc(e):
            if app_state.water_curve is None or app_state.water_curve.get('BHP') is None:
                set_info_message("Primero genere una curva de agua con BHP (Opción 1)", is_error=True)
                return
            set_info_message("Corrigiendo por viscosidad...")
            try:
                N = float(rpm_field.value)
                vis = float(vis_field.value)
                sg_visc = float(sg_visc_field.value)
            except ValueError:
                set_info_message("Ingrese valores numéricos válidos", is_error=True)
                return

            w = app_state.water_curve
            sg_agua = w['sg']

            if bep_option.value == "auto":
                Q_bep = w['Q_bep']
                H_bep = w['H_bep']
                eta_bep = w['eta_bep'] / 100
            else:  # manual: BEP desde los 4 puntos originales, pero curva de agua completa (con shut-off si existe)
                if app_state.original_points is None:
                    set_info_message("No hay puntos originales guardados. Use la opción automática o genere la curva con BHP.", is_error=True)
                    return
                max_eta = -1
                best_idx = 0
                for i, (q, h, bhp, eta) in enumerate(app_state.original_points):
                    if eta is not None and eta > max_eta:
                        max_eta = eta
                        best_idx = i
                Q_bep, H_bep, _, _ = app_state.original_points[best_idx]
                eta_bep = max_eta / 100 if max_eta > 0 else 0.68

                # Usar la curva de agua completa (que puede incluir shut-off) para la interpolación
                Q_agua_manual = w['Q']
                H_agua_manual = w['H']
                BHP_agua_manual = w['BHP']
                Eta_agua_manual = w['Eta']

            # Si es automático, también usamos la curva de agua completa (w)
            if bep_option.value == "auto":
                Q_agua_manual = w['Q']
                H_agua_manual = w['H']
                BHP_agua_manual = w['BHP']
                Eta_agua_manual = w['Eta']

            # Interpoladores para puntos base (sobre la curva de agua que corresponda)
            f_H = interp1d(Q_agua_manual, H_agua_manual, kind='linear', fill_value='extrapolate')
            f_BHP = interp1d(Q_agua_manual, BHP_agua_manual, kind='linear', fill_value='extrapolate')
            f_Eta = interp1d(Q_agua_manual, Eta_agua_manual, kind='linear', fill_value='extrapolate')

            fracciones = [0.6, 0.8, 1.0, 1.2]
            puntos_agua = []
            for frac in fracciones:
                Q_frac = Q_bep * frac
                H_frac = float(f_H(Q_frac))
                BHP_frac = float(f_BHP(Q_frac))
                eta_frac = f_Eta(Q_frac) / 100.0
                puntos_agua.append({'Q': Q_frac, 'H': H_frac, 'BHP': BHP_frac, 'eta': eta_frac})

            B = calcular_B('US', Q_bep, H_bep, N, vis)
            CQ = calcular_CQ(B) if B > 1.0 else 1.0
            Ceta = calcular_Ceta(B) if B > 1.0 else 1.0
            C_BEP_H = CQ

            # Puntos base corregidos
            puntos_vis = []
            ch_list = []
            for p in puntos_agua:
                r = p['Q'] / Q_bep
                Q_vis = CQ * p['Q']
                CH = calcular_CH(C_BEP_H, r) if B > 1.0 else 1.0
                H_vis = CH * p['H']
                eta_vis = Ceta * p['eta'] if B > 1.0 else p['eta']
                P_vis = potencia_vis(Q_vis, H_vis, sg_visc, eta_vis)
                incremento_pot = ((P_vis - p['BHP']) / p['BHP']) * 100 if p['BHP'] != 0 else 0
                puntos_vis.append((Q_vis, H_vis, eta_vis, P_vis, incremento_pot))
                ch_list.append(CH)

            # Curva completa de viscosidad (sobre la misma curva de agua)
            Q_vis_full = []
            H_vis_full = []
            BHP_vis_full = []
            Pot_Hid_vis_full = []
            Eta_vis_full = []

            for i in range(len(Q_agua_manual)):
                Q_a = Q_agua_manual[i]
                H_a = H_agua_manual[i]
                eta_a = Eta_agua_manual[i] / 100.0
                ratio = Q_a / Q_bep
                CH = calcular_CH(C_BEP_H, ratio) if B > 1.0 else 1.0
                Q_v = CQ * Q_a
                H_v = CH * H_a
                eta_v = Ceta * eta_a if B > 1.0 else eta_a
                Pot_Hid_v = (Q_v * H_v * sg_visc) / 3960
                BHP_v = Pot_Hid_v / eta_v if eta_v != 0 else 0
                Q_vis_full.append(Q_v)
                H_vis_full.append(H_v)
                BHP_vis_full.append(BHP_v)
                Pot_Hid_vis_full.append(Pot_Hid_v)
                Eta_vis_full.append(eta_v * 100)

            idx_max_vis = np.argmax(Eta_vis_full)
            Q_bep_vis = Q_vis_full[idx_max_vis]
            H_bep_vis = H_vis_full[idx_max_vis]
            eta_bep_vis = Eta_vis_full[idx_max_vis]

            # Actualizar tabla
            tabla.rows = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(f"{q:.1f}", color="white")),
                    ft.DataCell(ft.Text(f"{h:.1f}", color="white")),
                    ft.DataCell(ft.Text(f"{eta*100:.1f}%", color="white")),
                    ft.DataCell(ft.Text(f"{p:.1f}", color="white")),
                    ft.DataCell(ft.Text(f"{inc:.2f}%", color="white")),
                ]) for q, h, eta, p, inc in puntos_vis
            ]

            app_state.visc_data = {
                'B': B, 'CQ': CQ, 'Ceta': Ceta, 'CH_list': ch_list,
                'puntos_vis': puntos_vis,
                'Q_curve': Q_vis_full, 'H_curve': H_vis_full, 'BHP_curve': BHP_vis_full,
                'Pot_Hid_curve': Pot_Hid_vis_full, 'Eta_curve': Eta_vis_full,
                'visc': {'Q_bep': Q_bep_vis, 'H_bep': H_bep_vis, 'eta_bep': eta_bep_vis},
                'sg': sg_visc,
            }

            coef_visc_text.value = (f"B = {B:.3f} | CQ = {CQ:.3f} | Cη = {Ceta:.3f} | "
                                    f"CH: 60%={ch_list[0]:.3f}, 80%={ch_list[1]:.3f}, "
                                    f"100%={ch_list[2]:.3f}, 120%={ch_list[3]:.3f}")

            # Para el gráfico, la curva de agua original es w (con o sin shut-off)
            fig = crear_figura_viscosidad(
                w['Q'], w['H'], w.get('BHP'), w.get('Pot_Hid'), w.get('Eta'),
                np.array(Q_vis_full), np.array(H_vis_full), np.array(BHP_vis_full),
                np.array(Pot_Hid_vis_full), np.array(Eta_vis_full),
                np.array([p[0] for p in puntos_vis]), np.array([p[1] for p in puntos_vis]), np.array([p[3] for p in puntos_vis]),
                f"Corrección por Viscosidad ({vis} cSt, SG={sg_visc})",
                sg_agua=w.get('sg', 1.0), sg_visc=sg_visc
            )
            app_state.figura_visc = fig
            if HAVE_HTML:
                try:
                    grafico_visc.content = app_state.figura_visc.to_html(full_html=True, include_plotlyjs='cdn')
                except Exception as ex:
                    grafico_visc.content = f"<div style='color:#ef4444; text-align:center; padding:20px;'>Error al renderizar gráfico: {ex}</div>"
            else:
                grafico_visc.value = "Gráfico generado"
            set_info_message("Corrección por viscosidad completada")
            page.update()

        boton_corregir = ft.Button("Corregir", on_click=corregir_visc, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.AUTO_FIX_HIGH)

        def exportar_visc_datos(e):
            if app_state.visc_data is None:
                set_info_message("Primero corrija por viscosidad", is_error=True)
                return
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"viscosidad_{timestamp}.xlsx"
                filepath = os.path.join(app_state.output_dir, filename) if app_state.output_dir else filename
                success, msg = exportar_a_excel(filepath, app_state.water_curve, viscosidad_data=app_state.visc_data)
                set_info_message(msg)
            except Exception as ex:
                set_info_message(f"Error al exportar (viscosidad): {ex}", is_error=True)

        def exportar_visc_grafica(e):
            if app_state.figura_visc is None:
                set_info_message("Primero corrija por viscosidad", is_error=True)
                return
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"grafica_viscosidad_{timestamp}.html"
                filepath = os.path.join(app_state.output_dir, filename) if app_state.output_dir else filename
                success, msg = exportar_grafica_html(filepath, app_state.figura_visc)
                set_info_message(msg)
            except Exception as ex:
                set_info_message(f"Error al exportar gráfica (viscosidad): {ex}", is_error=True)

        boton_exp_visc = ft.Button("Exportar Excel", on_click=exportar_visc_datos, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.TABLE_CHART)
        boton_exp_visc_graf = ft.Button("Exportar Gráfica", on_click=exportar_visc_grafica, style=estilo_boton(color_fondo=COLORES["accent"]), icon=ft.Icons.IMAGE)

        input_container = ft.Container(
            content=ft.Column([
                ft.Text("Propiedades del Fluido", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Row([rpm_field, vis_field, sg_visc_field, boton_corregir], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        acciones_container = ft.Container(
            content=ft.Column([
                ft.Text("Exportar Resultados", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Row([boton_exp_visc, boton_exp_visc_graf], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([bep_option], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(content=coef_visc_text, bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                             border_radius=10, padding=15, margin=ft.Margin.only(top=10)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        tabla_container = ft.Container(
            content=ft.Column([
                ft.Text("Puntos corregidos", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ft.Container(content=tabla, bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLACK), border_radius=15, padding=15)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORES["card"], border_radius=20, padding=25,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
        )

        return ft.Column([
            ft.Text("Corrección por Viscosidad", size=28, weight=ft.FontWeight.BOLD, color="white"),
            input_container, acciones_container, tabla_container,
            ft.Container(content=grafico_visc, bgcolor=COLORES["card"], border_radius=20, padding=10,
                         shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))),
        ], spacing=25, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    cambiar_contenido(0)

if __name__ == "__main__":
    ft.run(main)