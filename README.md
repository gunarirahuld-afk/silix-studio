---
title: SILIX Studio
emoji: 🔬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
license: mit
---

# SILIX — Silicon RTL Studio 🔬⚡

[![Live Web Studio](https://img.shields.io/badge/Live%20Web%20Studio-trycloudflare-38bdf8?style=for-the-badge&logo=cloudflare)](https://yrs-readily-guide-limitation.trycloudflare.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-10b981?style=for-the-badge)](LICENSE)
[![Silicon PDK: SkyWater 130nm](https://img.shields.io/badge/PDK-SkyWater%20130nm-f59e0b?style=for-the-badge)](https://github.com/google/skywater-pdk)

**SILIX** is an open-access, cloud-native semiconductor EDA platform that allows anyone—from university students and freshers to silicon hardware engineers—to design, simulate, inspect, and synthesize digital ASIC circuits directly in their web browser for free.

🌐 **Public Live URL:** [https://yrs-readily-guide-limitation.trycloudflare.com](https://yrs-readily-guide-limitation.trycloudflare.com)  
📖 **Interactive Swagger Docs:** [https://yrs-readily-guide-limitation.trycloudflare.com/docs](https://yrs-readily-guide-limitation.trycloudflare.com/docs)  
🐙 **GitHub Repository:** [https://github.com/gunarirahuld-afk/silix-studio](https://github.com/gunarirahuld-afk/silix-studio)

---

## 🌟 Core Silicon Capabilities

1. **Interactive Sub-Circuit Drill-Down Inspector 🔬**
   - Click on **any block** in the generated circuit schematic to open the internal hardware inspector:
     - **ALU**: Multi-function arithmetic units with parallel CLA adder/subtractor, bitwise logic, barrel shifter, comparator, opcode MUX tree, and condition flags (`Z`, `C`, `V`, `N`).
     - **Counters & Shift Registers**: Synchronous incrementers with feedback loop routing and terminal count detectors.
     - **D-Flip-Flop (DFF)**: Master-Slave transmission gate latch stages (`TG1`, `TG2`), back-to-back CMOS inverter loops, clock buffer, and reset logic.
     - **Multiplexers (MUX)**: Binary address decoding matrix and wide OR summing gate.
     - **Finite State Machines (FSM)**: Next-State combinational decoding, State Register DFF array, and output decode logic.
     - **Logic Gates**: Transistor-level complementary CMOS PMOS pull-up and NMOS pull-down networks.
   - **Live Simulation Probes**: Displays the live probed logic values on all input/output pins.
   - **SkyWater 130nm PDK Cell Breakdown**: Lists physical standard cells (`sky130_fd_sc_hd__dfxtp_1`, `sky130_fd_sc_hd__fa_1`, etc.).

2. **Cycle-Accurate Event Simulation & Waveforms 📊**
   - Simulates sequential and combinational RTL designs.
   - Outputs standard **IEEE-1364 VCD (Value Change Dump)** files.
   - Renders interactive visual timing diagrams powered by **WaveDrom**.

3. **SkyWater 130nm ASIC Silicon Synthesis 🏭**
   - Synthesizes Verilog RTL into standard cells from Google & SkyWater's open-source 130nm PDK.
   - Computes total standard cell count, sequential flip-flops, estimated silicon area ($\mu m^2$), and maximum clock frequency ($F_{\text{max}}$ in MHz).

4. **AI Hardware Mentor & Synthesizability Diagnostics 💡**
   - Automatically detects educational hardware design bugs:
     - Inferred latches from incomplete `if-else` or missing `default:` in `case`.
     - Blocking assignments (`=`) inside sequential `always @(posedge clk)` blocks.
     - Race conditions and multi-driven net contention.

---

## 🚀 Instant Quickstart (Local)

### Prerequisites
- Python 3.10+

```bash
# Clone the repository
git clone https://github.com/gunarirahuld-afk/silix-studio.git
cd silix-studio

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the SILIX server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser to: **`http://localhost:8000`**

---

## ☁️ 1-Click Permanent Free Cloud Deployment

### Deploy to Render
1. Fork or push this repository to your GitHub.
2. In [Render.com](https://render.com), click **New +** → **Web Service**.
3. Select your repository.
4. Set Environment to **Docker** and Port to `8000`.
5. Click **Deploy**!

### Deploy to Hugging Face Spaces (24/7 Free)
1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space).
2. Choose **Docker** as the SDK.
3. Push this repository's code to the Space's Git URL.

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Health check & engine status |
| `/v1/info` | `GET` | Platform specifications and capabilities |
| `/v1/rtl/lint` | `POST` | Hardware syntax & synthesizability linting |
| `/v1/rtl/simulate` | `POST` | Cycle-accurate simulation with VCD & WaveDrom |
| `/v1/rtl/schematic` | `POST` | Port map, netlist, and sub-circuit blocks |
| `/v1/rtl/synthesize` | `POST` | SkyWater 130nm ASIC cell mapping and area calculation |

---

## 📄 License
Released under the MIT License. Open-source and free for students, educators, and silicon engineers worldwide.
