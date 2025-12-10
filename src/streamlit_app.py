import datetime
import streamlit as st
import pandas as pd

# Project-specific imports
try:
    from core.erzeuger import ErzeugerArt
    from core.prognose.ausbaupfad import Ausbaupfad
    from core.prognose.datenpunkt import ErzeugerDatenpunkt
    from core.setup.smard import Smard
    from core.simulation import Simulation
except ImportError as e:
    st.error(f"Import error: {e}. Make sure you are running this from the 'src' directory.")
    st.stop()

def main():
    st.set_page_config(page_title="Energiewendesimulation", layout="wide")
    st.title("Energiewendesimulation Test GUI")

    # Initialize Session State
    if "datenpunkte_list" not in st.session_state:
        st.session_state["datenpunkte_list"] = []

    # --- Sidebar Configuration ---
    st.sidebar.header("Konfiguration")
    
    # 1. Select Multiple Erzeuger
    erzeuger_options = [e.value for e in ErzeugerArt]
    selected_erzeuger_names = st.sidebar.multiselect(
        "Erzeuger Typen wählen", 
        erzeuger_options, 
        default=["Photovoltaik"]
    )
    
    # 2. Drought Intensity
    st.sidebar.subheader("Simulation Einstellungen")
    drought_intensity = st.sidebar.slider("Dürre Intensität (0=keine, 1=stark)", 0.0, 1.0, 0.8, 0.1)

    # 3. Add Datenpunkte (Per Erzeuger)
    st.sidebar.subheader("Datenpunkte verwalten")
    
    with st.sidebar.form("add_datenpunkt"):
        # Only allow adding points for selected erzeuger
        if not selected_erzeuger_names:
            st.warning("Bitte erst Erzeuger wählen.")
            dp_erzeuger_name = None
        else:
            dp_erzeuger_name = st.selectbox("Für Erzeuger", selected_erzeuger_names)
            
        new_date = st.date_input("Datum", datetime.date(2026, 1, 1))
        new_value = st.number_input("Installierte Leistung (MW)", min_value=0.0, value=1000.0, step=100.0)
        
        submitted = st.form_submit_button("ErzeugerDatenpunkt hinzufügen")
        if submitted and dp_erzeuger_name:
            st.session_state["datenpunkte_list"].append({
                "erzeuger": dp_erzeuger_name,
                "date": new_date,
                "value": new_value
            })
            st.success(f"Hinzugefügt für {dp_erzeuger_name}!")

    # Display current list
    st.sidebar.write("Aktuelle ErzeugerDatenpunkte:")
    if st.session_state["datenpunkte_list"]:
        for i, dp in enumerate(st.session_state["datenpunkte_list"]):
            st.sidebar.text(f"{dp['erzeuger']} | {dp['date']}: {dp['value']} MW")
            if st.sidebar.button(f"Löschen #{i}", key=f"del_{i}"):
                st.session_state["datenpunkte_list"].pop(i)
                st.rerun()
    else:
        st.sidebar.info("Keine ErzeugerDatenpunkte definiert.")

    # --- Main Content ---
    
    if not selected_erzeuger_names:
        st.info("Bitte wählen Sie mindestens einen Erzeuger aus.")
        return

    col_sim_1, col_sim_2 = st.columns([1, 3])
    with col_sim_1:
        run_sim = st.button("Simulation starten", type="primary")
        
    if run_sim:
        with st.spinner("Lade Daten und berechne Prognose..."):
            smard = Smard()
            
            # Prepare results storage
            results = {}
            combined_forecast = None
            combined_forecast_sim = None
            
            for name in selected_erzeuger_names:
                art = ErzeugerArt(name)
                erzeuger = smard.get_erzeuger(art)
                
                # Filter datenpunkte for this erzeuger
                erzeuger_dps = [
                    ErzeugerDatenpunkt(art, datetime.datetime(d['date'].year, d['date'].month, d['date'].day), d['value'])
                    for d in st.session_state["datenpunkte_list"]
                    if d['erzeuger'] == name
                ]
                
                # Fallback if no points defined
                if not erzeuger_dps:
                     current_max = erzeuger.installiert.werte.max()
                     erzeuger_dps = [ErzeugerDatenpunkt(art, datetime.datetime(2030, 1, 1), current_max)]

                ausbaupfad = Ausbaupfad(erzeuger_dps, smard=smard)
                prognose = ausbaupfad.get_prognose_datenreihe(art)
                
                # Simulation
                simulation = Simulation.create_drought(intensity=drought_intensity)
                prognose_sim = simulation.apply_to_datenreihe(prognose, art)
                
                results[name] = {
                    'prognose': prognose,
                    'prognose_sim': prognose_sim,
                    'erzeuger_obj': erzeuger
                }
                
                # Sum up for combined view
                if combined_forecast is None:
                    combined_forecast = prognose.df[["Datum von", name]].rename(columns={name: "Summe"})
                    combined_forecast_sim = prognose_sim.df[["Datum von", name]].rename(columns={name: "Summe"})
                else:
                    combined_forecast["Summe"] += prognose.df[name]
                    combined_forecast_sim["Summe"] += prognose_sim.df[name]
            
            st.session_state['last_multis_result'] = {
                'individual': results,
                'combined_forecast': combined_forecast,
                'combined_forecast_sim': combined_forecast_sim,
                'drought_intensity': drought_intensity
            }

    # Display Results
    if 'last_multis_result' in st.session_state:
        res = st.session_state['last_multis_result']
        
        st.markdown("---")
        st.subheader("Ergebnis Visualisierung")
        st.info("Hinweis: Die Daten werden für die Anzeige auf Tagesmittelwerte reduziert.")
        
        view_option = st.radio(
            "Ansicht wählen:",
            ("Summe aller Erzeuger", "Einzeln"),
            horizontal=True
        )
        
        if view_option == "Summe aller Erzeuger":
            # Prepare interactive chart data
            chart_data = res['combined_forecast'][['Datum von']].copy()
            chart_data = chart_data.rename(columns={'Datum von': 'Datum'})
            chart_data.set_index('Datum', inplace=True)
            
            chart_data['Basis Prognose (MW)'] = res['combined_forecast']['Summe'].values
            chart_data[f'Mit Dürre {res["drought_intensity"]} (MW)'] = res['combined_forecast_sim']['Summe'].values
            
            # Downsample to daily averages to prevent crashing
            chart_data_resampled = chart_data.resample('D').mean()
            
            st.line_chart(chart_data_resampled)
            
        else:
            # Prepare individual interactive chart data
            first_key = list(res['individual'].keys())[0]
            chart_data = res['individual'][first_key]['prognose'].df[['Datum von']].copy()
            chart_data = chart_data.rename(columns={'Datum von': 'Datum'})
            chart_data.set_index('Datum', inplace=True)
            
            for name, data in res['individual'].items():
                chart_data[f'{name} (Basis)'] = data['prognose'].df[name].values
                chart_data[f'{name} (Dürre)'] = data['prognose_sim'].df[name].values

            # Downsample to daily averages to prevent crashing
            chart_data_resampled = chart_data.resample('D').mean()

            st.line_chart(chart_data_resampled)

if __name__ == "__main__":
    main()
