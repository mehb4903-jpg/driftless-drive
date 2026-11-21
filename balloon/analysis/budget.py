#!/usr/bin/env python3
"""Mass, cost, float-altitude, power and link budgets for the Driftless-1 pico balloon.

The BOM (../BOM.csv) is the single source of truth for mass and cost.
Run:  python3 budget.py
"""
import csv, math, pathlib

HERE = pathlib.Path(__file__).resolve().parent
BOM = HERE.parent / "BOM.csv"

# ---------------------------------------------------------------- BOM
def load_bom():
    with open(BOM, newline="") as f:
        return list(csv.DictReader(f))

def mass_cost(rows):
    flight = [r for r in rows if r["flight"] == "Y"]
    m = sum(float(r["qty"]) * float(r["unit_mass_g"]) for r in flight)
    c_flight = sum(float(r["qty"]) * float(r["unit_cost_usd"]) for r in flight)
    c_all = sum(float(r["qty"]) * float(r["unit_cost_usd"]) for r in rows)
    env = {r["ref"]: r for r in rows if r["flight"] == "ENV"}
    return m, c_flight, c_all, env, flight

# ---------------------------------------------------------------- ISA atmosphere
G0, R_AIR = 9.80665, 287.053
LAYERS = [(0, 288.15, -0.0065), (11000, 216.65, 0.0), (20000, 216.65, 0.001), (32000, 228.65, 0.0028)]

def isa(h):
    p, T = 101325.0, 288.15
    for i, (hb, Tb, L) in enumerate(LAYERS):
        htop = LAYERS[i + 1][0] if i + 1 < len(LAYERS) else 47000
        dh = min(h, htop) - hb
        if dh <= 0:
            break
        if L == 0:
            p *= math.exp(-G0 * dh / (R_AIR * Tb)); T = Tb
        else:
            T = Tb + L * dh
            p *= (T / Tb) ** (-G0 / (R_AIR * L))
        if h <= htop:
            break
    return p, T, p / (R_AIR * T)

def alt_for_density(rho):
    lo, hi = 0.0, 40000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if isa(mid)[2] > rho: lo = mid
        else: hi = mid
    return (lo + hi) / 2

# ---------------------------------------------------------------- float altitude
def float_altitude(m_env_g, m_payload_g, free_lift_g, vol_m3, gas="H2", t_launch_c=15.0):
    """Super-pressure: envelope is volume-limited at float, gas mass is fixed at launch.
    Float when rho_air * V = m_env + m_payload + m_gas.  Ignores super-heat (conservative
    at night, optimistic in day the other way round -> see DESIGN.md)."""
    M = {"H2": 2.016e-3, "He": 4.0026e-3}[gas]
    # party-grade He is often ~80% He; we assume pure gas here.
    p0, _, _ = isa(0)
    T0 = 273.15 + t_launch_c
    rho_air0 = p0 / (R_AIR * T0)
    rho_gas0 = p0 * M / (8.314462 * T0)
    neck_lift = m_payload_g + free_lift_g             # what the scale reads at the neck
    gross = m_env_g + neck_lift                       # buoyancy minus gas weight
    v_gas0 = gross / 1000 / (rho_air0 - rho_gas0)     # m^3 at launch
    m_gas = v_gas0 * rho_gas0 * 1000                  # g
    rho_f = (m_env_g + m_payload_g + m_gas) / 1000 / vol_m3
    return alt_for_density(rho_f), m_gas, v_gas0, rho_f

# ---------------------------------------------------------------- power
LOADS_MW = {   # at 3V3 rail unless noted
    "RP2040 active 48 MHz + flash": 60,
    "RT6150 loss (85%)": 0,  # applied below
    "MAX-M10S tracking": 25,
    "OV5640 capture (JPEG 5MP)": 160,
    "RFM96W TX 10 dBm": 3.3 * 45,
    "RFM96W RX/idle": 3.3 * 1.5,
}

def daily_energy():
    # schedule per hour of daylight (seconds)
    sched = {
        "RP2040 active 48 MHz + flash": 3600 * 0.30,   # 30 % duty, else dormant-ish (~5 mW)
        "MAX-M10S tracking": 3600 * 0.15,
        "OV5640 capture (JPEG 5MP)": 4 * 6,            # 4 photos/h x 6 s incl warm-up
        "RFM96W TX 10 dBm": 3600 * 0.20,               # 20 % TX duty (SSDV + APRS)
        "RFM96W RX/idle": 3600 * 0.0,
    }
    e = sum(LOADS_MW[k] / 1000 * s for k, s in sched.items())   # J at 3V3
    e += 5e-3 * 3600 * 0.70                                      # sleep floor
    return e / 0.85                                              # regulator

def solar_power(n_cells=5, area_cm2=3.8 * 1.9, eff=0.20, cos_inc=0.6, s0=1361):
    return n_cells * area_cm2 * 1e-4 * s0 * eff * cos_inc

# ---------------------------------------------------------------- LoRa airtime
def lora_airtime(payload_b, sf, bw=125e3, cr=1, preamble=8, explicit=True, crc=True, ldro=None):
    tsym = (2 ** sf) / bw
    if ldro is None: ldro = tsym > 16e-3
    ih = 0 if explicit else 1
    n = 8 + max(math.ceil((8 * payload_b - 4 * sf + 28 + 16 * crc - 20 * ih) / (4 * (sf - 2 * ldro))) * (cr + 4), 0)
    return (preamble + 4.25) * tsym + n * tsym

def main():
    rows = load_bom()
    m, c_flight, c_all, env, flight = mass_cost(rows)
    print("=== MASS (flight payload) ===")
    for r in sorted(flight, key=lambda r: -float(r["qty"]) * float(r["unit_mass_g"])):
        print(f"  {r['ref']:7s} {float(r['qty'])*float(r['unit_mass_g']):6.3f} g  {r['part'][:60]}")
    print(f"  TOTAL   {m:6.3f} g   (limit 10.000 g, margin {10-m:+.3f} g)")
    print(f"\n=== COST ===\n  flight unit ${c_flight:.2f}   all incl envelope/gas/ground ${c_all:.2f}")

    m_env = float(env["BAL"]["unit_mass_g"])
    print("\n=== FLOAT ALTITUDE (SAG 32in clear, V=0.25 m3 stretched) ===")
    for gas in ("H2", "He"):
        for fl in (5, 7, 9):
            h, mg, v0, rho = float_altitude(m_env, m, fl, 0.25, gas)
            print(f"  {gas}  free-lift {fl} g: float {h/1000:5.2f} km  (gas {mg:4.1f} g, launch vol {v0*1000:4.0f} L, rho {rho:.3f})")
    # sensitivity: payload mass
    print("  sensitivity H2/7 g FL:", ", ".join(
        f"{p} g -> {float_altitude(m_env, p, 7, 0.25)[0]/1000:.2f} km" for p in (8, 9, 10, 11)))

    print("\n=== POWER ===")
    e_h = daily_energy()
    print(f"  load energy per daylight hour {e_h:.0f} J  (avg {e_h/3600*1000:.0f} mW)")
    for cosv in (0.2, 0.4, 0.6, 0.9):
        print(f"  solar @cos {cosv}: {solar_power(cos_inc=cosv)*1000:.0f} mW")
    peak = (60 + 25 + 160 + 3.3 * 45) / 0.85
    print(f"  worst-case simultaneous peak (scheduler forbids) {peak:.0f} mW; "
          f"scheduled peak (TX or camera, not both) {(60+25+160)/0.85:.0f} mW")

    print("\n=== SSDV DOWNLINK (RFM96W, BW125, CR4/5) ===")
    for sf in (7, 8, 9):
        t = lora_airtime(255, sf)
        print(f"  SF{sf}: 255 B packet {t*1000:.0f} ms  -> 190 kB image {190e3/205*t/60:.1f} min,"
              f" 640x480 thumb (25 kB) {25e3/205*t:.0f} s")
    print(f"  LoRa-APRS SF12 BW125 CR4/5 60 B position: {lora_airtime(60, 12, cr=1)*1000:.0f} ms")

    print("\n=== NIGHT BEACON (0.22 F, 3.0 -> 2.2 V) ===")
    e_cap = 0.5 * 0.22 * (3.0 ** 2 - 2.2 ** 2)
    e_flash = 3.0 * 0.020 * 0.002
    for period in (2, 4, 8):
        rate_h = 3600 / period
        leak = 3.0 * 2e-6 * 3600 + 3.0 * 35e-9 * 3600
        hours = e_cap / (rate_h * e_flash + leak)
        print(f"  flash 20 mA x 2 ms every {period} s: {hours:4.1f} h after sunset")

if __name__ == "__main__":
    main()
