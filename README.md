# Global RTL Design Cloud API 🌐⚡

An open, high-performance API for digital chip designers, university students, freshers, and semiconductor teams worldwide.

---

## 🚀 Key Features

* **Instant RTL Linting (`POST /v1/rtl/lint`):** Checks Verilog/SystemVerilog for common hardware bugs:
  * Inferred latches (missing `else` or missing `default:` in `case`).
  * Blocking assignments (`=`) in sequential `always @(posedge clk)` blocks.
  * Non-blocking assignments (`<=`) in combinational blocks.
  * Multi-driven net short circuits.
  * Educational explanations tailored for students & freshers.
* **Cycle-Accurate Simulation (`POST /v1/rtl/simulate`):**
  * Outputs standard **IEEE 1364 VCD (Value Change Dump)** files.
  * Generates **WaveDrom JSON** for direct visual rendering in any web browser or UI.
* **Hardware Schematic Extraction (`POST /v1/rtl/schematic`):**
  * Parses I/O ports, registers, and interconnects.
  * Outputs a **Mermaid.js Flowchart** showing physical hardware topology.
* **Interactive OpenAPI / Swagger Documentation:** Available at `http://localhost:8000/docs`.

---

## 🛠️ Quickstart (Local Development)

### 1. Activate Environment & Run
```powershell
# From the project root
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### 2. View Interactive Swagger Docs
Open your browser to:
```
http://localhost:8000/docs
```

---

## 📡 API Endpoints & Examples

### 1. Lint Verilog Code
```bash
curl -X POST "http://localhost:8000/v1/rtl/lint" \
     -H "Content-Type: application/json" \
     -d '{
       "code": "module bad_counter(input clk, output reg [3:0] q); always @(posedge clk) q = q + 1; endmodule"
     }'
```

### 2. Run Simulation & Get Waveforms
```bash
curl -X POST "http://localhost:8000/v1/rtl/simulate" \
     -H "Content-Type: application/json" \
     -d '{
       "module_code": "module counter(input clk, input rst_n, output reg [3:0] count); always @(posedge clk) if (!rst_n) count <= 0; else count <= count + 1; endmodule",
       "cycles": 16,
       "reset_active_low": true
     }'
```

### 3. Generate Circuit Schematic
```bash
curl -X POST "http://localhost:8000/v1/rtl/schematic" \
     -H "Content-Type: application/json" \
     -d '{
       "code": "module adder(input [3:0] a, input [3:0] b, output [3:0] sum); assign sum = a + b; endmodule"
     }'
```

---

## 🐳 Docker Deployment

To run in a container with full open-source EDA tools (`iverilog`, `yosys`, `verilator`):

```bash
docker build -t rtl-cloud-api .
docker run -p 8000:8000 rtl-cloud-api
```
