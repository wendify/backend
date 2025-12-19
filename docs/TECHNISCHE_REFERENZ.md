# Technische Referenz - Formeln und Berechnungen

Diese Dokumentation enthält alle mathematischen Formeln und Berechnungsdetails der Energiewendesimulation.

---

## 1. Grundlegende Einheiten

| Größe | Einheit | Symbol | Beschreibung |
|-------|---------|--------|--------------|
| Leistung | Megawatt | MW | Momentane elektrische Leistung |
| Zeit | 15 Minuten | Δt | Zeitschritt der Simulation |
| Energie | MWh | - | Leistung × Zeit (wird nicht direkt verwendet) |
| Normierter Wert | Dimensionslos | - | Werte zwischen 0.0 und 1.0 |

**Wichtig:** Alle Werte in der Simulation sind **Leistungswerte in MW**, nicht Energiewerte in MWh. Die SMARD-Daten liefern durchschnittliche Leistung pro 15-Minuten-Intervall.

---

## 2. Normiertes Profil (ENorm)

### 2.1 Definition

Das normierte Profil beschreibt die typische Auslastung eines Erzeugers relativ zur installierten Kapazität:

$$
ENorm(t) = \frac{Realisiert(t)}{Installiert(t)}
$$

### 2.2 Wertebereich

$$
0 \leq ENorm(t) \leq 1
$$

- `ENorm = 0`: Keine Erzeugung (z.B. PV nachts)
- `ENorm = 0.5`: 50% Auslastung
- `ENorm = 1.0`: Volllast (100% der installierten Kapazität)

### 2.3 Beispiel Photovoltaik

```
Zeitpunkt: 12:00 Uhr, sonniger Tag
Installiert: 80.000 MW
Realisiert: 56.000 MW

ENorm = 56.000 / 80.000 = 0.7 (70% Auslastung)
```

---

## 3. Interpolation der Zielwerte

### 3.1 Lineare Interpolation

Für die installierte Leistung zwischen Kontrollpunkten:

$$
Installiert(t) = Installiert_{start} + \frac{t - t_{start}}{t_{end} - t_{start}} \times (Installiert_{end} - Installiert_{start})
$$

### 3.2 Beispiel

```
Kontrollpunkte:
- 01.01.2024: 80 GW (Baseline)
- 01.01.2030: 215 GW (Ziel)

Berechnung für 01.01.2027 (Mitte):
Installiert = 80 + (3/6) × (215 - 80)
            = 80 + 0.5 × 135
            = 147.5 GW
```

---

## 4. Prognose-Berechnung

Die Prognose-Berechnung unterscheidet zwischen **Erneuerbaren** (regulation = 0) und **Regelbaren** (regulation > 0) Erzeugern.

### 4.1 Erneuerbare Erzeuger (regulation = 0)

Für wetterabhängige Erzeuger wird das normierte Profil angewendet:

#### 4.1.1 Hauptformel

$$
Prognose_{EE}(t) = Heute(t) + \Delta \times ENorm(t)
$$

Wobei:
$$
\Delta = Installiert_{Ziel}(t) - Installiert_{Baseline}
$$

#### 4.1.2 Erweiterte Form

$$
Prognose_{EE}(t) = Realisiert_{historisch}(t) + (Installiert_{Ziel}(t) - Installiert_{Baseline}) \times ENorm(t)
$$

#### 4.1.3 Beispielrechnung Photovoltaik

```
Photovoltaik am 15.07.2028, 12:00 Uhr:

Gegeben:
- Baseline (heute): 80 GW installiert
- Ziel (interpoliert für 2028): 170 GW installiert
- ENorm (12:00, Juli): 0.65
- Historisch realisiert (12:00, Juli): 80 × 0.65 = 52 GW

Berechnung:
Delta = 170 - 80 = 90 GW
Prognose = 52 + 90 × 0.65 = 52 + 58.5 = 110.5 GW
```

### 4.2 Regelbare Erzeuger (regulation > 0)

Für dispatchable Erzeuger wird die installierte Leistung direkt verwendet:

#### 4.2.1 Formel

$$
Prognose_{Disp}(t) = Installiert_{Ziel}(t)
$$

Das Stack-Modell bestimmt dann die tatsächliche Nutzung basierend auf:
- Bedarf (demand)
- MUSS-Erzeugung (vorheriger Zeitschritt)
- Ramp-Rate Limitierungen
- Prioritätenreihenfolge

#### 4.2.2 Beispielrechnung Steinkohle

```
Steinkohle am 15.07.2028, 12:00 Uhr:

Gegeben:
- Baseline (heute): 20 GW installiert
- Ziel (interpoliert für 2028): 8 GW installiert

Berechnung:
Prognose = 8 GW (volle Verfügbarkeit)

Stack-Modell Simulation:
- Verbrauch: 60 GW
- Erneuerbare decken: 50 GW
- Verbleibend: 10 GW
- Steinkohle kann liefern: 8 GW (max)
- Realisiert: 3 GW (durch Ramp-Rate limitiert)
```

---

## 5. Stack-Modell Algorithmus

### 5.1 Übersicht pro Zeitschritt

```
Input:
- max_available[art]: Maximal verfügbare Leistung je Erzeuger (MW)
- demand: Verbrauch/Netzlast (MW)
- prev_realized[art]: Realisierung des vorherigen Zeitschritts (MW)
- regulation[art]: Regelbarkeit je Erzeuger (0.0 - 1.0)

Output:
- realized[art]: Realisierte Erzeugung je Erzeuger (MW)
```

### 5.2 MUSS-Erzeugung

Für Erzeuger mit $0 < regulation < 1$:

$$
MUSS(t) = Realisiert(t-1) \times (1 - regulation)
$$

**Bedeutung:** Ein Erzeuger kann pro Zeitschritt maximal $regulation \times 100\%$ seiner Leistung reduzieren.

### 5.3 Beispiel MUSS

```
Braunkohle (regulation = 0.02):
- Vorheriger Zeitschritt: 5000 MW
- MUSS = 5000 × (1 - 0.02) = 5000 × 0.98 = 4900 MW

→ Mindestens 4900 MW müssen erzeugt werden
→ Nur 100 MW Reduktion pro 15 Minuten möglich
```

### 5.4 Erneuerbare Abregelung

Bei Überangebot erneuerbarer Energie:

$$
curtailment\_factor = \frac{remaining\_demand}{\sum_{EE} available_{EE}}
$$

$$
realized_{EE}(t) = available_{EE}(t) \times curtailment\_factor
$$

### 5.5 Beispiel Abregelung

```
Gegeben:
- Verbrauch: 50.000 MW
- MUSS (Braunkohle): 10.000 MW
- Verbleibend: 40.000 MW

Erneuerbare verfügbar:
- PV: 60.000 MW
- Wind: 40.000 MW
- Summe: 100.000 MW

Berechnung:
curtailment_factor = 40.000 / 100.000 = 0.4

Realisiert:
- PV: 60.000 × 0.4 = 24.000 MW
- Wind: 40.000 × 0.4 = 16.000 MW
- Summe: 40.000 MW ✓
```

### 5.6 Ramp-Rate (Hochfahren)

Für konventionelle Erzeuger ist die Hochfahr-Geschwindigkeit begrenzt:

$$
max\_delta_{up} = 2 \times regulation \times max\_available
$$

$$
candidate = prev\_realized + max\_delta_{up}
$$

$$
new\_value = \min(candidate,\ target,\ max\_available)
$$

### 5.7 Beispiel Ramp-Rate

```
Steinkohle (regulation = 0.05):
- max_available: 10.000 MW
- prev_realized: 2.000 MW
- Benötigt: 7.000 MW

Berechnung:
max_delta_up = 2 × 0.05 × 10.000 = 1.000 MW
candidate = 2.000 + 1.000 = 3.000 MW
target = 7.000 MW
new_value = min(3.000, 7.000, 10.000) = 3.000 MW

→ Nur 3.000 MW möglich (Ramp-Rate limitiert)
→ Benötigt 5 Zeitschritte (75 min) um 7.000 MW zu erreichen
```

---

## 6. Regulation-Werte

| Erzeugerart | Regulation | Max. Änderung/15min | Charakteristik |
|-------------|------------|---------------------|----------------|
| Photovoltaik | 0.0 | - | Wetterabhängig |
| Wind Onshore | 0.0 | - | Wetterabhängig |
| Wind Offshore | 0.0 | - | Wetterabhängig |
| Wasserkraft | 0.0 | - | Natürlicher Zufluss |
| Kernenergie | 0.02 | 2% | Sehr träge |
| Braunkohle | 0.02 | 2% | Sehr träge |
| Steinkohle | 0.05 | 5% | Träge |
| Sonstige Konv. | 0.2 | 20% | Moderat |
| Biomasse | 0.4 | 40% | Regelbar |
| Erdgas | 1.0 | 100% | Schnell |
| Pumpspeicher | 1.0 | 100% | Schnell |

---

## 7. Prioritätenreihenfolge

Bei Unterdeckung werden Erzeuger in dieser Reihenfolge zugeschaltet:

1. **Kernenergie** - Grundlast, läuft ohnehin
2. **Pumpspeicher** - Flexibel, speicherbasiert
3. **Biomasse** - Erneuerbar und regelbar
4. **Erdgas** - Spitzenlast, schnell
5. **Steinkohle** - Mittellast
6. **Braunkohle** - Grundlast
7. **Sonstige Konventionelle** - Rest

---

## 8. Zeitraster und Datenmengen

### 8.1 Zeitraster

$$
\Delta t = 15\ Minuten = 0.25\ Stunden
$$

### 8.2 Zeitschritte pro Zeitraum

| Zeitraum | Anzahl Zeitschritte |
|----------|---------------------|
| 1 Tag | 96 |
| 1 Woche | 672 |
| 1 Monat | ~2.880 |
| 1 Jahr | ~35.040 |
| 10 Jahre | ~350.400 |

### 8.3 Gesamtdatenmenge (12 Erzeuger × 10 Jahre)

$$
Datenpunkte = 12 \times 350.400 \approx 4.200.000
$$

---

## 9. Extrapolation der Profile

### 9.1 Tagesprofil (daily)

$$
ENorm_{daily}(h) = \frac{1}{N_{tage}} \sum_{d=1}^{N_{tage}} ENorm(d, h)
$$

Wobei $h$ die Uhrzeit (0:00 - 23:45) ist.

### 9.2 Jahresprofil (yearly)

$$
ENorm_{yearly}(d_{Jahr}, h) = \frac{1}{N_{Jahre}} \sum_{y=1}^{N_{Jahre}} ENorm(y, d_{Jahr}, h)
$$

Wobei $d_{Jahr}$ der Tag im Jahr (1-365) und $h$ die Uhrzeit ist.

---

## 10. Formelzusammenfassung

| Berechnung | Formel |
|------------|--------|
| Normiertes Profil | $ENorm = \frac{Realisiert}{Installiert}$ |
| Lineare Interpolation | $I(t) = I_0 + \frac{t-t_0}{t_1-t_0} \times (I_1 - I_0)$ |
| Prognose (Erneuerbare) | $P_{EE}(t) = R_{hist}(t) + (I_{Ziel}(t) - I_{Basis}) \times ENorm(t)$ |
| Prognose (Regelbare) | $P_{Disp}(t) = I_{Ziel}(t)$ |
| MUSS-Erzeugung | $MUSS(t) = R(t-1) \times (1 - reg)$ |
| Abregelungsfaktor | $cf = \frac{remaining}{\sum available_{EE}}$ |
| Ramp-Rate | $\Delta_{max} = 2 \times reg \times max\_avail$ |

---

## 11. Konsistenzprüfungen

### 11.1 Energieerhaltung

$$
\sum_{Erzeuger} Realisiert(t) \leq Verbrauch(t) + Toleranz
$$

### 11.2 Kapazitätsgrenzen

$$
0 \leq Realisiert(t) \leq max\_available(t)
$$

Wobei:
- Für **Erneuerbare**: $max\_available(t) = Installiert(t) \times ENorm(t)$
- Für **Regelbare**: $max\_available(t) = Installiert(t)$

### 11.3 MUSS-Grenzen

$$
MUSS(t) \leq Realisiert(t) \leq max\_available(t)
$$

---

*Technische Referenz - Dezember 2024*

