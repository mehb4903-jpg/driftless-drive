# Driftless-1 — super-pressure pico balloon with camera

Status: **v1 draft (pre-review)**. Numbers come from `analysis/budget.py`, which reads `BOM.csv`.

## 1. Requirements

| # | Requirement | Source |
|---|---|---|
| R1 | Super-pressure envelope that floats at a constant density altitude for days to weeks | user |
| R2 | Payload (everything below the envelope) **< 10.0 g** | user |
| R3 | Solar powered, no battery | user (+ batteries fail at −55 °C) |
| R4 | Raspberry Pi Pico (RP2040) as flight computer | user |
| R5 | High-resolution camera (≥ 5 MP) | user |
| R6 | GPS position | user |
| R7 | A light (LED beacon) | user |
| R8 | Images and position must reach the ground (no recovery is assumed) | derived |
| R9 | Legal: FAA 14 CFR 101 exempt class (< 6 lb payload, < 4 lb per package), FCC Part 97 | derived |

## 2. System overview

```
          SAG 32" clear foil sphere (47 g, 0.25 m³ stretched, H2)
                         │  0.3 mm Dyneema, 300 mm
                ┌────────┴────────┐
                │  solar array    │  5 × 38×19 mm mono-Si in series, horizontal, on CF rods
                │  GPS patch (up) │
                └────────┬────────┘
                 flex carrier + Pico (vertical, hangs below array)
                   ├─ OV5640 looking 30° below horizon
                   ├─ RFM96W  ── 164 mm ¼-wave wire down, 164 mm counterpoise up
                   ├─ MAX-M10S
                   └─ LED (down-facing)
```

## 3. Envelope and float altitude

* Envelope: SAG "Orbs" 32″ clear foil sphere, ~47 g (community-measured 47–49 g), ~0.25 m³ stretched.
  Clear film runs cooler than silvered film, so less day/night super-heat swing.
* Gas: hydrogen (leaks slower than helium through foil, half the gas mass → ~0.5 km higher).
  Helium is the safe fallback.
* Pre-stretch: inflate with air to 0.3 psi (~2 kPa) for 24 h, deflate, then fill. This removes the
  creep that otherwise makes the balloon grow and sink in the first nights.
* Free lift: 7 g (enough ascent rate ~1–1.5 m/s to climb through icing layers in ~3 h).

| Gas | Free lift | Float altitude (ISA, payload 9.40 g) |
|---|---|---|
| H₂ | 7 g | **13.5 km** |
| He | 7 g | 13.0 km |

Payload sensitivity is weak (~0.12 km per gram) because the envelope dominates the gross mass.
This matches the community report of ~13.5 km for an ~8 g payload on the same envelope.

## 4. Mass budget (flight payload)

See `analysis/budget.py` output. Total **9.40 g**, margin **0.60 g** against the 10 g limit.
The Pico is the largest single item (2.6 g after removing USB socket and BOOTSEL switch).

## 5. Electrical architecture

### 5.1 Power
* 5S string of mono-Si cells → VSYS directly (Vmp ≈ 2.8 V warm, 3.2 V cold; Voc ≤ 4.6 V at −60 °C).
* Pico's on-board RT6150 buck-boost (1.8–5.5 V in) makes 3V3.
* D2 5.6 V clamp on VSYS. 2 × 100 µF X5R on VSYS as a burst reservoir.
* U6 TPS3840 (3.0 V) holds RUN low until VSYS is comfortably above the brown-out region, so the
  RP2040 does not chatter at dawn.
* Firmware reads VSYS (GPIO29/ADC3) before every heavy action and only starts a camera capture or a
  long TX when VSYS > 3.1 V. Camera and TX are never simultaneous (scheduled peak ≈ 290 mW).
* Solar yield ≈ 200–880 mW depending on sun incidence; mean load ≈ 70 mW in daylight.

### 5.2 Flight computer
Raspberry Pi Pico, 125 MHz max, run at 48 MHz most of the time. Firmware in C (pico-sdk).
Every dawn is a cold boot; state lives in the W25Q128 (U5) log, not RAM.

### 5.3 Camera
OV5640 5 MP, DVP 8-bit into PIO0 + DMA. On-sensor JPEG, mode 2560×1920 (multiple of 16 for SSDV).
JPEG quality is adapted so each frame fits in a 192 kB SRAM buffer, then copied to U5
(16 MB → ~80 full images). Camera power is switched off between shots (Q1).

### 5.4 Radio / downlink
RFM96W (SX1276) 433 MHz, 10 dBm.
* LoRa-APRS position every 2 min at 433.775 MHz (SF12) → global iGate network.
* SSDV image packets (SF7, BW125) on 434.x MHz → SondeHub SSDV / own ground station.
  Thumbnails (640×480, ~25 kB, ~50 s) sent first, full images when over a ground station.
* Amateur licence required (Part 97, Technician in the US; ITU-region rules elsewhere).

### 5.5 GNSS
u-blox MAX-M10S, airborne <2 g model, 10×10 mm passive patch facing zenith. Powered via Q2, fix
then off; time from GPS seeds the RTC.

### 5.6 Light
White/red 0603 LED, two drivers:
* Day: Pico GPIO flashes it (status + visual ID at launch).
* Night: TPL5010 nano-timer runs from a 0.22 F supercap charged by the 3V3 rail; its WAKE pulse is
  RC-differentiated to a ~2 ms gate pulse → one flash every 4 s, ~3.5 h after sunset.

## 6. Pin map (RP2040)

| GPIO | Function | GPIO | Function |
|---|---|---|---|
| 0–7 | CAM D2–D9 (PIO0) | 18 | SPI0 SCK (LoRa + flash) |
| 8 | CAM PCLK | 19 | SPI0 MOSI |
| 9 | CAM HREF | 20 | UART1 TX → GPS RX |
| 10 | CAM VSYNC | 21 | UART1 RX ← GPS TX |
| 11 | CAM XCLK (PWM5B, 24 MHz) | 22 | LoRa DIO0 |
| 12 | I²C0 SDA (SCCB) | 26 | GPS power enable (Q2) |
| 13 | I²C0 SCL (SCCB) | 27 | LED day drive (Q3) |
| 14 | CAM power enable (Q1) | 28 | ADC2 supercap voltage |
| 15 | Flash CS | 29 | ADC3 VSYS/3 (on-board) |
| 16 | SPI0 MISO | 23 | RT6150 PS (PWM/PFM) |
| 17 | LoRa NSS | | |

## 7. Operations
1. Pre-stretch envelope 24 h. 2. Measure payload on 0.01 g scale. 3. Fill H₂ to neck lift = payload + 7 g.
4. Launch at dawn so the solar array powers the climb. 5. Float at ~13.5 km, circumnavigate.

## 8. Risks (open)
* Supercap low-temperature ESR / capacity at −55 °C.
* OV5640 image quality below −30 °C (self-heating by warm-up before capture).
* Payload rotation blurring photos.
* 0.60 g mass margin is thin.
