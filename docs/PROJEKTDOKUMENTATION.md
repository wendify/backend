# Energiewendesimulation - Vollständige Projektdokumentation

## Inhaltsverzeichnis

1. [Überblick](#1-überblick)
2. [Datenquellen (SMARD)](#2-datenquellen-smard)
3. [Datenstrukturen](#3-datenstrukturen)
4. [Szenario-Definition](#4-szenario-definition)
5. [Ausbaupfad & Prognose](#5-ausbaupfad--prognose)
6. [Stack-Modell Simulation](#6-stack-modell-simulation)
7. [Visualisierung](#7-visualisierung)
8. [Ablaufdiagramme](#8-ablaufdiagramme)

---

## 1. Überblick

Die Energiewendesimulation ist ein Python-basiertes Tool zur Simulation der deutschen Energiewende. Es berechnet, wie sich die Stromerzeugung basierend auf geplanten Ausbauzielen (z.B. EEG-Ziele) entwickeln könnte.

### Kernkonzept

```
SMARD-Daten (historisch) → Szenario (Zielwerte) → Ausbaupfad (Interpolation) → Stack-Modell (Simulation) → Visualisierung
```

### Hauptkomponenten

| Komponente | Datei | Funktion |
|------------|-------|----------|
| App | `src/core/app.py` | Haupteinstiegspunkt, orchestriert alle Schritte |
| SMARD | `src/core/setup/smard.py` | Lädt historische Daten von der SMARD-API |
| Szenario | `src/core/scenarios/default.py` | Definiert Ausbauziele für die Zukunft |
| Ausbaupfad | `src/core/prognose/ausbaupfad.py` | Interpoliert und berechnet Prognosen |
| Stack-Modell | `src/core/simulation/stack_model.py` | Berechnet realisierte Erzeugung |
| Visualisierung | `src/core/visualization/plots.py` | Erstellt interaktive Plotly-Diagramme |

---

## 2. Datenquellen (SMARD)

### 2.1 Was ist SMARD?

SMARD (Strommarktdaten) ist eine öffentliche Plattform der Bundesnetzagentur, die Echtzeitdaten zum deutschen Strommarkt bereitstellt.

### 2.2 Datendownload (`src/core/data/handler.py`)

Die Daten werden über die SMARD-API heruntergeladen:

```python
# Zeitraum: 01.01.2024 bis 31.10.2025
# Auflösung: 15 Minuten (quarterhour)
form = {
    "format": "CSV",
    "language": "de",
    "moduleIds": ids,        # SMARD-Modul-IDs
    "region": "DE",          # Deutschland
    "resolution": "quarterhour",  # 15-Minuten-Intervalle
    "timestamp_from": ...,   # Startzeit in Millisekunden
    "timestamp_to": ...,     # Endzeit in Millisekunden
}
```

### 2.3 Drei Datensätze

| Datensatz | Datei | Beschreibung | Einheit |
|-----------|-------|--------------|---------|
| Installiert | `installiert.csv` | Installierte Leistung je Erzeugerart | MW |
| Realisiert | `realisiert.csv` | Tatsächlich erzeugte Leistung | MW |
| Verbraucht | `verbraucht.csv` | Netzlast/Verbrauch | MW |

### 2.4 Daten laden (`src/core/data/loader.py`)

```python
def load_csv() -> tuple[DataFrame, DataFrame, DataFrame]:
    # 1. Download falls Dateien nicht existieren
    # 2. CSV einlesen mit pandas
    # 3. Datumspalten konvertieren
    # 4. Spaltennamen bereinigen (Einheiten entfernen)
    return installiert, realisiert, verbraucht
```

### 2.5 SMARD-Klasse (`src/core/setup/smard.py`)

Die `Smard`-Klasse ist der zentrale Datenzugriffspunkt:

```python
class Smard:
    def __init__(self):
        # Lädt entweder aus Pickle-Cache oder neu von CSV
        self.installiert, self.realisiert, self.verbraucht = loader.load_csv()
        self.erzeuger: list[Erzeuger] = []      # Pro ErzeugerArt ein Objekt
        self.verbraucher: list[Datenreihe] = [] # Pro VerbraucherArt ein Objekt
```

### 2.6 Erzeuger-Arten (ErzeugerArt)

```python
class ErzeugerArt(StrEnum):
    Biomasse = "Biomasse"
    Braunkohle = "Braunkohle"
    Erdgas = "Erdgas"
    Kernenergie = "Kernenergie"
    Photovoltaik = "Photovoltaik"
    Pumpspeicher = "Pumpspeicher"
    SonstigeErneuerbare = "Sonstige Erneuerbare"
    SonstigeKonventionelle = "Sonstige Konventionelle"
    Steinkohle = "Steinkohle"
    Wasserkraft = "Wasserkraft"
    WindOffshore = "Wind Offshore"
    WindOnshore = "Wind Onshore"
```

### 2.7 Regulation (Regelbarkeit)

Jeder Erzeuger hat einen `regulation`-Wert (0.0 bis 1.0):

| Erzeuger | Regulation | Bedeutung |
|----------|------------|-----------|
| Photovoltaik | 0.0 | Nicht regelbar (Wetter-abhängig) |
| Wind Onshore/Offshore | 0.0 | Nicht regelbar (Wetter-abhängig) |
| Wasserkraft | 0.0 | Nicht regelbar |
| Braunkohle | 0.02 | Sehr träge (2% pro Zeitschritt) |
| Kernenergie | 0.02 | Sehr träge |
| Steinkohle | 0.05 | Träge (5% pro Zeitschritt) |
| Biomasse | 0.4 | Moderat regelbar |
| Erdgas | 1.0 | Schnell regelbar (Spitzenlast) |
| Pumpspeicher | 1.0 | Schnell regelbar |

---

## 3. Datenstrukturen

### 3.1 Datenreihe (`src/core/datenreihe.py`)

Grundlegende Zeitreihen-Klasse:

```python
class Datenreihe[T]:
    def __init__(self, art: T, df: DataFrame):
        self.art = art  # ErzeugerArt oder VerbraucherArt
        self.df = df    # DataFrame mit "Datum von", "Datum bis", {art}
```

**DataFrame-Struktur:**
| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| Datum von | datetime | Start des Intervalls |
| Datum bis | datetime | Ende des Intervalls |
| {art} | float | Wert in MW |

### 3.2 Erzeuger (`src/core/erzeuger.py`)

Repräsentiert einen Energieerzeuger mit allen Zeitreihen:

```python
class Erzeuger:
    def __init__(self, art, installiert, realisiert, regulation):
        self.art = art                    # ErzeugerArt
        self.installiert = installiert    # Datenreihe: Installierte Leistung (MW)
        self.realisiert = realisiert      # Datenreihe: Tatsächliche Erzeugung (MW)
        self.regulation = regulation      # float: Regelbarkeit (0.0-1.0)
        
        # Berechne normiertes Profil
        self.normiert = realisiert / installiert  # Dimensionslos (0.0-1.0)
```

### 3.3 Normiertes Profil (ENorm)

Das normierte Profil zeigt die typische Erzeugungsform **für wetterabhängige Erzeuger** (regulation = 0):

```
ENorm = Realisiert / Installiert
```

**Verwendung:**
- ✅ **Erneuerbare** (PV, Wind, Wasserkraft): ENorm wird für Prognose verwendet
- ❌ **Regelbare** (Erdgas, Kohle, Biomasse): ENorm wird NICHT verwendet

**Beispiel Photovoltaik:**
- Mittags: ENorm ≈ 0.7 (70% der installierten Leistung)
- Nachts: ENorm = 0.0 (keine Erzeugung)
- Bewölkt: ENorm ≈ 0.3

### 3.4 Datenpunkte (`src/core/prognose/datenpunkt.py`)

```python
@dataclass
class ErzeugerDatenpunkt:
    art: ErzeugerArt          # Welcher Erzeuger
    datetime: datetime        # Ziel-Zeitpunkt (z.B. 2030-01-01)
    installiert: float        # Ziel-Leistung in MW

@dataclass
class VerbraucherDatenpunkt:
    art: VerbraucherArt       # Welcher Verbraucher
    datetime: datetime        # Ziel-Zeitpunkt
    verbraucht: float         # Ziel-Verbrauch in MW
```

---

## 4. Szenario-Definition

### 4.1 Default-Szenario (`src/core/scenarios/default.py`)

Das Standard-Szenario basiert auf EEG-Zielen und Kohleausstiegsplanungen:

```python
def create_default_scenario(smard: Smard) -> Tuple[List, List]:
    # Definiert Ausbauziele für jeden Erzeugertyp
    return erzeuger_datenpunkte, verbraucher_datenpunkte
```

### 4.2 Beispiel: Photovoltaik-Ausbau

```python
erzeuger_datenpunkte = [
    # Photovoltaik: Starker Ausbau
    ErzeugerDatenpunkt(ErzeugerArt.Photovoltaik, datetime(2026, 1, 1), 130_000),  # 130 GW
    ErzeugerDatenpunkt(ErzeugerArt.Photovoltaik, datetime(2030, 1, 1), 215_000),  # 215 GW
    ErzeugerDatenpunkt(ErzeugerArt.Photovoltaik, datetime(2035, 1, 1), 260_000),  # 260 GW
    
    # Steinkohle: Ausstieg bis 2030
    ErzeugerDatenpunkt(ErzeugerArt.Steinkohle, datetime(2026, 1, 1), 12_000),
    ErzeugerDatenpunkt(ErzeugerArt.Steinkohle, datetime(2030, 1, 1), 3_000),
    ErzeugerDatenpunkt(ErzeugerArt.Steinkohle, datetime(2035, 1, 1), 0),
]
```

### 4.3 Ausbautrends nach Erzeugertyp

| Erzeuger | Trend | 2026 | 2030 | 2035 |
|----------|-------|------|------|------|
| Photovoltaik | ⬆️ Stark steigend | 130 GW | 215 GW | 260 GW |
| Wind Onshore | ⬆️ Steigend | 70 GW | 85 GW | 100 GW |
| Wind Offshore | ⬆️ Steigend | 11 GW | 25 GW | 40 GW |
| Steinkohle | ⬇️ Ausstieg | 12 GW | 3 GW | 0 GW |
| Braunkohle | ⬇️ Rückbau | 13 GW | 8 GW | 2 GW |
| Erdgas | ↔️ Brückentechnologie | 36 GW | 40 GW | 38 GW |

---

## 5. Ausbaupfad & Prognose

### 5.1 Überblick

Der `Ausbaupfad` (`src/core/prognose/ausbaupfad.py`) berechnet aus diskreten Datenpunkten eine kontinuierliche Prognose-Zeitreihe.

### 5.2 Berechnungsschritte

```
1. Datenpunkte validieren und ergänzen
2. Zeitraster erstellen (15-Minuten-Intervalle)
3. Zielwerte linear interpolieren
4. Erzeugertyp prüfen (regulation == 0?)
5a. Erneuerbare (regulation = 0):
    - Normiertes Profil extrapolieren
    - Prognose berechnen: Heute + Delta × Profil
5b. Regelbare (regulation > 0):
    - Prognose = Interpolierte installierte Leistung
```

### 5.3 Interpolation der Zielwerte

```python
def interpolate_target_values(times, baseline_time, baseline_value, target_points):
    """
    Interpoliert linear zwischen Kontrollpunkten.
    
    Beispiel:
    - Baseline (heute): 50 GW am 01.01.2024
    - Ziel: 100 GW am 01.01.2030
    - Ergebnis: Lineare Steigerung von 50 auf 100 GW
    """
```

**Visualisierung:**
```
Installiert (GW)
     ^
 100 |                    ●───────●  (Ziel 2030/2035)
     |              ●────/
  50 |    ●────────/             (Ziel 2026)
     |────/  (Baseline heute)
     +────────────────────────────────> Zeit
         2024      2026    2030    2035
```

### 5.4 Normiertes Profil (ENorm) extrapolieren

Für Zeitpunkte in der Zukunft wird das historische Profil fortgeschrieben:

| Modus | Beschreibung | Anwendung |
|-------|--------------|-----------|
| `daily` | Tagesprofil (Durchschnitt pro Uhrzeit) | Standard für Erzeuger |
| `yearly` | Jahresprofil (Durchschnitt pro Tag+Uhrzeit) | Standard für Verbraucher |
| `last` | Letzter bekannter Wert | Fallback |

**Beispiel Tagesprofil:**
```
ENorm
  ^
1.0|         ████
   |       ██    ██
0.5|     ██        ██
   |   ██            ██
0.0|███                ███
   +──────────────────────> Uhrzeit
    00:00   12:00   00:00
```

### 5.5 Prognose-Formel

Die Prognose-Berechnung unterscheidet zwischen **Erneuerbaren** und **Regelbaren** Erzeugern:

#### 5.5.1 Erneuerbare Erzeuger (regulation = 0)

Für wetterabhängige Erzeuger (PV, Wind, Wasserkraft):

```
Prognose[t] = Heute[t] + (Ziel[t] - Baseline) × Profil[t]
```

**Komponenten:**
- `Heute[t]`: Historische/fortgeschriebene Werte
- `Ziel[t]`: Interpolierter Zielwert (installierte Leistung)
- `Baseline`: Ausgangswert (letzte bekannte installierte Leistung)
- `Profil[t]`: Normiertes Profil (ENorm)

**Beispielrechnung Photovoltaik:**
```
Photovoltaik am 01.07.2027, 12:00 Uhr:
- Baseline (heute): 80 GW installiert
- Ziel (interpoliert): 150 GW installiert
- Delta: 150 - 80 = 70 GW zusätzlich
- ENorm (mittags, Juli): 0.7
- Heute[t]: 80 GW × 0.7 = 56 GW
- Prognose: 56 + 70 × 0.7 = 105 GW
```

#### 5.5.2 Regelbare Erzeuger (regulation > 0)

Für dispatchable Erzeuger (Erdgas, Kohle, Biomasse):

```
Prognose[t] = Ziel[t] (installierte Leistung)
```

Das Stack-Modell regelt dann die tatsächliche Nutzung basierend auf Bedarf und Ramp-Rates.

**Beispielrechnung Steinkohle:**
```
Steinkohle am 01.07.2027, 12:00 Uhr:
- Ziel (interpoliert): 8.000 MW installiert
- Prognose: 8.000 MW (volle Verfügbarkeit)
- Realisiert (Stack-Modell): ~2.000 MW (basierend auf Bedarf)
```

### 5.6 Ausbaupfad-Klasse

```python
class Ausbaupfad:
    def __init__(self, erzeuger_datenpunkte, verbraucher_datenpunkte, smard):
        # 1. Validierung
        validate_datenpunkte(erzeuger_datenpunkte)
        
        # 2. Fehlende Arten ergänzen (konstant fortschreiben)
        self.datenpunkte = ergaenze_erzeuger_datenpunkte(erzeuger_datenpunkte, smard)
        
        # 3. Prognose-Zeitreihen berechnen
        self.prognose_datenreihen = create_prognose_datenreihen(self.datenpunkte, smard)
        self.prognose_verbraucher_datenreihen = create_prognose_verbraucher_datenreihen(...)
```

---

## 6. Stack-Modell Simulation

### 6.1 Überblick

Das Stack-Modell (`src/core/simulation/stack_model.py`) simuliert, wie viel von der maximal verfügbaren Erzeugung tatsächlich genutzt wird.

**Kernfrage:** Wenn 200 GW erneuerbare Energie verfügbar sind, aber nur 60 GW Verbrauch besteht – wer wird abgeregelt?

### 6.2 Algorithmus pro Zeitschritt

```
Für jeden Zeitschritt t:

1. MUSS-Erzeugung berechnen (träge Kraftwerke können nicht abschalten)
   MUSS[t] = Realisiert[t-1] × (1 - regulation)

2. Erneuerbare Erzeuger hinzufügen (regulation = 0)
   - Anteilige Abregelung wenn Überangebot

3. Konventionelle nach Priorität auffüllen
   - Mit Ramp-Rate begrenzt: max_delta = 2 × regulation × max_available

4. Ergebnis speichern und zum nächsten Zeitschritt
```

### 6.3 MUSS-Erzeugung

Träge Kraftwerke (Braunkohle, Kernenergie) können nicht beliebig schnell herunterfahren:

```python
MUSS = vorheriger_Wert × (1 - regulation)
```

**Beispiel Braunkohle (regulation = 0.02):**
```
Zeitschritt t-1: 5000 MW realisiert
Zeitschritt t:   MUSS = 5000 × 0.98 = 4900 MW mindestens
```

→ Die Braunkohle kann maximal 2% pro 15 Minuten herunterfahren.

### 6.4 Erneuerbare Integration

Erneuerbare werden mit Priorität integriert. Bei Überangebot erfolgt **proportionale Abregelung**:

```python
# Wenn mehr Erneuerbare als benötigt
if renewable_available > remaining_demand:
    curtailment_factor = remaining_demand / renewable_available
    
    for renewable in renewables:
        realized = available × curtailment_factor
```

### 6.5 Prioritätsreihenfolge

Bei Unterdeckung werden konventionelle Erzeuger nach Priorität zugeschaltet:

```python
PRIORITY_ORDER = [
    ErzeugerArt.Kernenergie,        # Höchste Priorität (Grundlast)
    ErzeugerArt.Pumpspeicher,       # Flexibel
    ErzeugerArt.Biomasse,           # Erneuerbar & regelbar
    ErzeugerArt.Erdgas,             # Spitzenlast
    ErzeugerArt.Steinkohle,         # Mittellast
    ErzeugerArt.Braunkohle,         # Grundlast
    ErzeugerArt.SonstigeKonventionelle,
]
```

### 6.6 Ramp-Rate (Hochfahren)

Die Hochfahr-Geschwindigkeit ist begrenzt:

```python
max_delta_up = 2.0 × regulation × max_available
new_value = min(prev_value + max_delta_up, max_available, target)
```

**Beispiel Erdgas (regulation = 1.0):**
```
max_delta_up = 2.0 × 1.0 × 30000 MW = 60000 MW pro Zeitschritt
→ Kann quasi sofort auf Volllast hochfahren
```

**Beispiel Steinkohle (regulation = 0.05):**
```
max_delta_up = 2.0 × 0.05 × 10000 MW = 1000 MW pro Zeitschritt
→ Braucht mehrere Stunden zum Hochfahren
```

### 6.7 Optimierung mit NumPy

Der Algorithmus wurde für ~400.000 Zeitschritte optimiert:

```python
# Vorher (pandas): ~5 Minuten
# Nachher (numpy): ~3-10 Sekunden

# Optimierungen:
# 1. Regulation-Werte einmal vorberechnen
# 2. pandas → numpy Arrays konvertieren
# 3. Erzeuger nach Typ vorkategorisieren
# 4. Ergebnis-Array einmal allokieren
```

---

## 7. Visualisierung

### 7.1 Plotly-basierte Diagramme

Die Visualisierung (`src/core/visualization/plots.py`) erstellt interaktive Plotly-Diagramme:

| Plot | Funktion | Beschreibung |
|------|----------|--------------|
| Prognose Stackplot | `create_prognose_stackplot()` | Alle Erzeuger gestapelt |
| Installierte Leistung | `create_installed_capacity_plot()` | Ausbaukurven pro Erzeuger |
| Realisierte Erzeugung | `create_realized_stackplot()` | Output des Stack-Modells |
| Debug-Vergleich | `create_debug_comparison_plot()` | Einzelner Erzeuger im Detail |

### 7.2 Interaktive Features

- **Hover:** MW-Werte anzeigen
- **Zoom/Pan:** Zeitbereich vergrößern
- **Legende:** Erzeuger ein-/ausblenden
- **Auflösung:** 15 Min / 1 Tag / 1 Woche / 1 Monat

### 7.3 Farbschema

Jeder Erzeugertyp hat eine konsistente Farbe über alle Plots hinweg:

```python
GENERATOR_COLORS = {
    ErzeugerArt.Photovoltaik: "#FFD700",      # Gold
    ErzeugerArt.WindOnshore: "#4169E1",       # Royal Blue
    ErzeugerArt.WindOffshore: "#1E90FF",      # Dodger Blue
    ErzeugerArt.Biomasse: "#228B22",          # Forest Green
    ErzeugerArt.Wasserkraft: "#00CED1",       # Dark Turquoise
    ErzeugerArt.Erdgas: "#FF6347",            # Tomato
    ErzeugerArt.Steinkohle: "#2F4F4F",        # Dark Slate Gray
    ErzeugerArt.Braunkohle: "#8B4513",        # Saddle Brown
    # ...
}
```

---

## 8. Ablaufdiagramme

### 8.1 Haupt-Ablauf

Siehe [ABLAUFDIAGRAMME.md](./ABLAUFDIAGRAMME.md) für detaillierte Mermaid-Diagramme.

### 8.2 Kurzübersicht

```
┌─────────────────┐
│  App.run()      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Smard.__init__()│──────│ SMARD-API/CSV   │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ create_default_ │──────│ ErzeugerDaten-  │
│ scenario()      │      │ punkte          │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Ausbaupfad()    │
│ - interpolate   │
│ - prognose      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ apply_stack_    │
│ model_to_       │
│ ausbaupfad()    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ show_all_plots()│──────▶ Browser
└─────────────────┘
```

---

## Anhang: Konfiguration (`src/config.py`)

| Variable | Beschreibung |
|----------|--------------|
| `DATA_DIR` | Verzeichnis für CSV/Pickle-Dateien |
| `SMARD_URL` | SMARD-API-Endpunkt |
| `ENORM_EXTRAPOLATION_MODE` | daily/yearly/last |
| `ENVIRONMENT` | dev/prod (Pickle-Caching nur in prod) |

---

*Dokumentation erstellt: Dezember 2024*

