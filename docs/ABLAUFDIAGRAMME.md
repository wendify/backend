# Ablaufdiagramme - Energiewendesimulation

Diese Dokumentation enthält detaillierte Mermaid.js-Diagramme für alle Datenflüsse und Algorithmen.

---

## 1. Gesamtablauf der Anwendung

```mermaid
flowchart TD
    subgraph START["🚀 Anwendungsstart"]
        A[main.py] --> B[App.__init__]
    end

    subgraph SMARD["📊 SMARD Datenladung"]
        B --> C{Pickle existiert?}
        C -->|Ja| D[Pickle laden]
        C -->|Nein| E[CSV laden/downloaden]
        E --> F[Erzeuger erstellen]
        F --> G[Verbraucher erstellen]
        G --> H[Pickle speichern]
        D --> I[Smard-Objekt bereit]
        H --> I
    end

    subgraph SCENARIO["📋 Szenario"]
        I --> J[create_default_scenario]
        J --> K[ErzeugerDatenpunkte]
        J --> L[VerbraucherDatenpunkte]
    end

    subgraph AUSBAUPFAD["📈 Ausbaupfad"]
        K --> M[Ausbaupfad.__init__]
        L --> M
        M --> N[Validierung]
        N --> O[Fehlende Arten ergänzen]
        O --> P[Prognose berechnen]
        P --> Q[prognose_datenreihen]
    end

    subgraph STACKMODEL["⚡ Stack-Modell"]
        Q --> R[apply_stack_model_to_ausbaupfad]
        R --> S[calculate_realized_generation]
        S --> T[Zeitschritt-Schleife]
        T --> U[realisiert_datenreihen]
    end

    subgraph VISUALIZATION["📊 Visualisierung"]
        U --> V[show_all_plots]
        V --> W[Prognose Stackplot]
        V --> X[Installed Capacity]
        V --> Y[Realized Stackplot]
        V --> Z[Debug Comparison]
        W --> AA[Browser öffnen]
        X --> AA
        Y --> AA
        Z --> AA
    end

    style START fill:#e1f5fe
    style SMARD fill:#fff3e0
    style SCENARIO fill:#f3e5f5
    style AUSBAUPFAD fill:#e8f5e9
    style STACKMODEL fill:#ffebee
    style VISUALIZATION fill:#e0f7fa
```

---

## 2. SMARD-Datenladung im Detail

```mermaid
flowchart LR
    subgraph API["SMARD API"]
        A1[smard.de/api]
    end

    subgraph DOWNLOAD["Download Handler"]
        B1[handler.download]
        B2["timestamp_from: 2024-01-01"]
        B3["timestamp_to: 2025-10-31"]
        B4["resolution: quarterhour"]
    end

    subgraph FILES["CSV Dateien"]
        C1[installiert.csv]
        C2[realisiert.csv]
        C3[verbraucht.csv]
    end

    subgraph LOADER["CSV Loader"]
        D1[loader.load_csv]
        D2[read_csv mit pandas]
        D3[Datumskonvertierung]
        D4[Spalten umbenennen]
    end

    subgraph OBJECTS["Datenobjekte"]
        E1[installiert DataFrame]
        E2[realisiert DataFrame]
        E3[verbraucht DataFrame]
    end

    A1 -->|HTTP POST| B1
    B1 --> B2 & B3 & B4
    B1 --> C1 & C2 & C3
    C1 & C2 & C3 --> D1
    D1 --> D2 --> D3 --> D4
    D4 --> E1 & E2 & E3

    style API fill:#ffcdd2
    style DOWNLOAD fill:#fff9c4
    style FILES fill:#c8e6c9
    style LOADER fill:#bbdefb
    style OBJECTS fill:#d1c4e9
```

---

## 3. Datenstruktur eines Erzeugers

```mermaid
classDiagram
    class Smard {
        +erzeuger: List~Erzeuger~
        +verbraucher: List~Datenreihe~
        +installiert: DataFrame
        +realisiert: DataFrame
        +verbraucht: DataFrame
        +get_erzeuger(art) Erzeuger
        +get_verbraucher(art) Datenreihe
    }

    class Erzeuger {
        +art: ErzeugerArt
        +installiert: Datenreihe
        +realisiert: Datenreihe
        +normiert: Datenreihe
        +regulation: float
    }

    class Datenreihe {
        +art: T
        +df: DataFrame
        +anfang: Series
        +ende: Series
        +werte: Series
        +get_row(timestamp) Series
    }

    class ErzeugerArt {
        <<enumeration>>
        Photovoltaik
        WindOnshore
        WindOffshore
        Erdgas
        Steinkohle
        Braunkohle
        ...
    }

    Smard "1" --> "*" Erzeuger : enthält
    Smard "1" --> "*" Datenreihe : enthält
    Erzeuger "1" --> "3" Datenreihe : hat
    Erzeuger --> ErzeugerArt : verwendet
    Datenreihe --> ErzeugerArt : generisch T
```

---

## 4. Normiertes Profil Berechnung

```mermaid
flowchart TD
    subgraph INPUT["Eingabe aus SMARD"]
        A[Realisierte Erzeugung<br/>in MW]
        B[Installierte Leistung<br/>in MW]
    end

    subgraph CALCULATION["Berechnung"]
        C["ENorm = Realisiert / Installiert"]
        D["Werte zwischen 0.0 und 1.0"]
    end

    subgraph EXAMPLE["Beispiel Photovoltaik"]
        E1["12:00 Uhr: 40.000 MW / 80.000 MW = 0.5"]
        E2["15:00 Uhr: 56.000 MW / 80.000 MW = 0.7"]
        E3["22:00 Uhr: 0 MW / 80.000 MW = 0.0"]
    end

    subgraph OUTPUT["Ausgabe"]
        F[Normiertes Profil<br/>Datenreihe]
    end

    A --> C
    B --> C
    C --> D
    D --> E1 & E2 & E3
    E1 & E2 & E3 --> F

    style INPUT fill:#fff3e0
    style CALCULATION fill:#e8f5e9
    style EXAMPLE fill:#e3f2fd
    style OUTPUT fill:#f3e5f5
```

---

## 5. Szenario-Datenpunkte

```mermaid
timeline
    title Ausbaupfad Photovoltaik (GW installiert)

    2024 : Heute ~80 GW
         : (SMARD Daten)
    
    2026 : Ziel 130 GW
         : (+50 GW in 2 Jahren)
    
    2030 : Ziel 215 GW
         : (+85 GW in 4 Jahren)
    
    2035 : Ziel 260 GW
         : (+45 GW in 5 Jahren)
```

```mermaid
timeline
    title Rückbaupfad Steinkohle (GW installiert)

    2024 : Heute ~20 GW
         : (SMARD Daten)
    
    2026 : Ziel 12 GW
         : (-8 GW Abbau)
    
    2030 : Ziel 3 GW
         : (-9 GW Abbau)
    
    2035 : Ziel 0 GW
         : (Kompletter Ausstieg)
```

---

## 6. Ausbaupfad-Berechnung

```mermaid
flowchart TD
    subgraph INPUT["Eingaben"]
        A[ErzeugerDatenpunkte<br/>z.B. PV: 130GW@2026]
        B[SMARD historische Daten]
    end

    subgraph STEP1["Schritt 1: Zeitraster"]
        C[Erstelle Zeitraster]
        D["15-Minuten-Intervalle<br/>von heute bis 2035"]
    end

    subgraph STEP2["Schritt 2: Interpolation"]
        E[Interpoliere Zielwerte]
        F["Linear zwischen<br/>Kontrollpunkten"]
        G["Ergebnis: installiert[t]<br/>für jeden Zeitschritt"]
    end

    subgraph STEP3["Schritt 3: Erzeugertyp prüfen"]
        H{"regulation == 0?"}
    end

    subgraph STEP4A["Schritt 4a: Erneuerbare (regulation=0)"]
        I[Extrapoliere ENorm]
        J{"Modus?"}
        K["daily: Tagesprofil"]
        L["yearly: Jahresprofil"]
        M["ENorm[t]"]
        N["Prognose = Heute + Delta × ENorm"]
    end

    subgraph STEP4B["Schritt 4b: Regelbare (regulation>0)"]
        O["Prognose = installiert[t]"]
        P["Keine Profil-Anwendung"]
    end

    subgraph OUTPUT["Ausgabe"]
        Q["Ergebnis: Prognose[t] in MW"]
    end

    A --> C
    B --> C
    C --> D --> E
    E --> F --> G
    G --> H
    H -->|Ja<br/>Wetterabhängig| I
    H -->|Nein<br/>Dispatchable| O
    I --> J
    J -->|daily| K
    J -->|yearly| L
    K & L --> M --> N
    O --> P
    N --> Q
    P --> Q

    style INPUT fill:#fff3e0
    style STEP1 fill:#e8f5e9
    style STEP2 fill:#e3f2fd
    style STEP3 fill:#ffe0b2
    style STEP4A fill:#f3e5f5
    style STEP4B fill:#ffccbc
    style OUTPUT fill:#c8e6c9
```

---

## 6b. Prognose-Berechnung: Erneuerbare vs. Regelbare

```mermaid
flowchart LR
    subgraph RENEWABLE["Erneuerbare (regulation = 0)"]
        R1[Photovoltaik<br/>Wind Onshore<br/>Wind Offshore<br/>Wasserkraft]
        R2["installiert[t]<br/>z.B. 150 GW"]
        R3["ENorm[t]<br/>z.B. 0.6 (mittags)"]
        R4["Prognose = 150 × 0.6<br/>= 90 GW"]
    end

    subgraph DISPATCHABLE["Regelbare (regulation > 0)"]
        D1[Erdgas<br/>Steinkohle<br/>Braunkohle<br/>Biomasse]
        D2["installiert[t]<br/>z.B. 30 GW"]
        D3["Kein ENorm!<br/>Volle Verfügbarkeit"]
        D4["Prognose = 30 GW<br/>(max. verfügbar)"]
        D5["Stack-Modell regelt<br/>tatsächliche Nutzung"]
    end

    R1 --> R2 --> R3 --> R4
    D1 --> D2 --> D3 --> D4 --> D5

    style RENEWABLE fill:#c8e6c9
    style DISPATCHABLE fill:#ffccbc
```

**Warum diese Unterscheidung?**
- **Erneuerbare** sind wetterabhängig → ENorm zeigt typische Erzeugungsmuster
- **Regelbare** können nach Bedarf gesteuert werden → Stack-Modell entscheidet über Einsatz

---

## 7. Stack-Modell Algorithmus

```mermaid
flowchart TD
    subgraph INIT["Initialisierung"]
        A[max_available_datenreihen]
        B[verbrauch_datenreihe]
        C[previous_realisiert<br/>aus SMARD]
    end

    subgraph LOOP["Für jeden Zeitschritt t"]
        D[Lade max_avail_t und demand_t]
        
        subgraph MUSS["1. MUSS-Erzeugung"]
            E["Für Erzeuger mit 0 < regulation < 1"]
            F["MUSS = prev_realized × (1 - regulation)"]
            G["current_stack += MUSS"]
        end

        subgraph RENEWABLE["2. Erneuerbare"]
            H["Für Erzeuger mit regulation = 0"]
            I{"Überangebot?"}
            J["Proportionale<br/>Abregelung"]
            K["Volles<br/>Hinzufügen"]
            L["current_stack += erneuerbar"]
        end

        subgraph CONVENTIONAL["3. Konventionelle"]
            M["Nach PRIORITY_ORDER"]
            N["max_delta = 2 × regulation × max_avail"]
            O["candidate = prev + max_delta"]
            P["new_value = min(candidate, target, max_avail)"]
            Q["current_stack += konventionell"]
        end

        subgraph SAVE["4. Speichern"]
            R["result[t] = MUSS + erneuerbar + konv"]
            S["prev_realized = result[t]"]
        end
    end

    subgraph OUTPUT["Ausgabe"]
        T[realisiert_datenreihen]
    end

    A & B & C --> D
    D --> E --> F --> G
    G --> H --> I
    I -->|Ja| J
    I -->|Nein| K
    J & K --> L
    L --> M --> N --> O --> P --> Q
    Q --> R --> S
    S -->|Nächster Zeitschritt| D
    R --> T

    style INIT fill:#fff3e0
    style LOOP fill:#e3f2fd
    style MUSS fill:#ffcdd2
    style RENEWABLE fill:#c8e6c9
    style CONVENTIONAL fill:#fff9c4
    style SAVE fill:#d1c4e9
    style OUTPUT fill:#b2dfdb
```

---

## 8. MUSS-Erzeugung im Detail

```mermaid
flowchart LR
    subgraph T_MINUS_1["Zeitschritt t-1"]
        A["Braunkohle realisiert:<br/>5000 MW"]
    end

    subgraph CALC["Berechnung"]
        B["regulation = 0.02"]
        C["MUSS = 5000 × (1 - 0.02)"]
        D["MUSS = 5000 × 0.98"]
        E["MUSS = 4900 MW"]
    end

    subgraph T["Zeitschritt t"]
        F["Mindestens 4900 MW<br/>müssen erzeugt werden"]
        G["Kann nur 2% pro<br/>Zeitschritt runterfahren"]
    end

    A --> B --> C --> D --> E --> F
    E --> G

    style T_MINUS_1 fill:#e3f2fd
    style CALC fill:#fff9c4
    style T fill:#c8e6c9
```

---

## 9. Proportionale Erneuerbare Abregelung

```mermaid
flowchart TD
    subgraph SITUATION["Ausgangssituation"]
        A["Verbrauch: 50.000 MW"]
        B["MUSS bereits: 10.000 MW"]
        C["Verbleibend: 40.000 MW"]
        D["PV verfügbar: 60.000 MW"]
        E["Wind verfügbar: 40.000 MW"]
        F["Gesamt EE: 100.000 MW"]
    end

    subgraph PROBLEM["Problem"]
        G["100.000 MW EE > 40.000 MW Bedarf"]
        H["→ 60.000 MW müssen abgeregelt werden"]
    end

    subgraph SOLUTION["Lösung: Proportionale Abregelung"]
        I["curtailment_factor = 40.000 / 100.000 = 0.4"]
        J["PV realisiert = 60.000 × 0.4 = 24.000 MW"]
        K["Wind realisiert = 40.000 × 0.4 = 16.000 MW"]
        L["Summe: 40.000 MW ✓"]
    end

    A & B --> C
    D & E --> F
    C & F --> G --> H
    H --> I --> J & K --> L

    style SITUATION fill:#e3f2fd
    style PROBLEM fill:#ffcdd2
    style SOLUTION fill:#c8e6c9
```

---

## 10. Konventionelle Hochfahren (Ramp-Rate)

```mermaid
flowchart TD
    subgraph INIT["Ausgangslage"]
        A["Steinkohle (regulation=0.05)"]
        B["max_available: 10.000 MW"]
        C["prev_realized: 2.000 MW"]
        D["Benötigt: 5.000 MW mehr"]
    end

    subgraph CALC["Berechnung"]
        E["max_delta = 2 × 0.05 × 10.000"]
        F["max_delta = 1.000 MW"]
        G["candidate = 2.000 + 1.000 = 3.000 MW"]
        H["target = MUSS + remaining = 7.000 MW"]
        I["new_value = min(3.000, 7.000, 10.000)"]
        J["new_value = 3.000 MW"]
    end

    subgraph RESULT["Ergebnis"]
        K["Nur 3.000 MW realisiert"]
        L["Nicht 7.000 MW wie benötigt"]
        M["→ Ramp-Rate limitiert!"]
    end

    A & B & C & D --> E --> F --> G
    G --> I
    H --> I --> J --> K --> L --> M

    style INIT fill:#fff3e0
    style CALC fill:#e3f2fd
    style RESULT fill:#ffcdd2
```

---

## 11. Visualisierungs-Pipeline

```mermaid
flowchart LR
    subgraph DATA["Datenquellen"]
        A[ausbaupfad.prognose_datenreihen]
        B[realisiert_datenreihen]
        C[smard.erzeuger]
    end

    subgraph PREPARE["Vorbereitung"]
        D[prepare_plot_dataframes]
        E[merge_datenreihen_to_dataframe]
        F[resample_dataframe]
    end

    subgraph PLOTS["Plot-Erstellung"]
        G[create_prognose_stackplot]
        H[create_installed_capacity_plot]
        I[create_realized_stackplot]
        J[create_debug_comparison_plot]
    end

    subgraph OUTPUT["Ausgabe"]
        K[Plotly Figure]
        L[fig.show]
        M[Browser]
    end

    A & B & C --> D --> E --> F
    F --> G & H & I & J
    G & H & I & J --> K --> L --> M

    style DATA fill:#fff3e0
    style PREPARE fill:#e8f5e9
    style PLOTS fill:#e3f2fd
    style OUTPUT fill:#f3e5f5
```

---

## 12. Datenfluss Gesamtübersicht

```mermaid
flowchart TB
    subgraph EXTERNAL["Externe Daten"]
        EXT1[("SMARD API<br/>smard.de")]
    end

    subgraph RAW["Rohdaten"]
        RAW1[(installiert.csv)]
        RAW2[(realisiert.csv)]
        RAW3[(verbraucht.csv)]
    end

    subgraph PROCESSED["Verarbeitete Daten"]
        PROC1[Erzeuger-Objekte<br/>mit ENorm]
        PROC2[Verbraucher-Objekte]
    end

    subgraph SCENARIO["Szenario"]
        SCEN1[ErzeugerDatenpunkte<br/>Ausbauziele]
        SCEN2[VerbraucherDatenpunkte<br/>Verbrauchsziele]
    end

    subgraph PROGNOSE["Prognose"]
        PROG1[Interpolierte<br/>Installiert-Zeitreihe]
        PROG2[Prognose-Zeitreihe<br/>Erneuerbare: Installiert × ENorm<br/>Regelbare: Installiert]
        PROG3[Verbrauchs-Prognose]
    end

    subgraph SIMULATION["Simulation"]
        SIM1[Stack-Modell]
        SIM2[Realisierte<br/>Erzeugung]
    end

    subgraph VIZ["Visualisierung"]
        VIZ1[Stackplots]
        VIZ2[Liniendiagramme]
        VIZ3[Debug-Plots]
    end

    EXT1 --> RAW1 & RAW2 & RAW3
    RAW1 & RAW2 --> PROC1
    RAW3 --> PROC2
    PROC1 --> PROG1
    PROG1 --> PROG2
    PROC2 --> PROG3
    SCEN1 --> PROG1
    SCEN2 --> PROG3
    PROG2 --> SIM1
    PROG3 --> SIM1
    SIM1 --> SIM2
    SIM2 --> VIZ1 & VIZ2 & VIZ3
    PROG2 --> VIZ1

    style EXTERNAL fill:#ffcdd2
    style RAW fill:#fff9c4
    style PROCESSED fill:#c8e6c9
    style SCENARIO fill:#bbdefb
    style PROGNOSE fill:#d1c4e9
    style SIMULATION fill:#ffccbc
    style VIZ fill:#b2dfdb
```

---

## 13. Zeitliche Auflösung

```mermaid
gantt
    title Zeitliche Auflösung der Simulation
    dateFormat YYYY-MM-DD
    
    section SMARD Daten
    Historische Daten (15min)     :done, smard, 2024-01-01, 2025-10-31
    
    section Prognose
    Interpolation (15min)         :active, prog, 2024-01-01, 2035-12-31
    
    section Simulation
    Stack-Modell (15min)          :sim, 2024-01-01, 2035-12-31
    
    section Visualisierung
    Aggregiert (Tag/Woche/Monat)  :viz, 2024-01-01, 2035-12-31
```

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| 🟡 Gelb | Rohdaten / Eingabe |
| 🟢 Grün | Verarbeitung / Berechnung |
| 🔵 Blau | Zwischenergebnisse |
| 🟣 Lila | Prognose / Simulation |
| 🔴 Rot | Probleme / Limitierungen |
| 🩵 Türkis | Ausgabe / Visualisierung |

---

*Diagramme erstellt mit Mermaid.js - Dezember 2024*

