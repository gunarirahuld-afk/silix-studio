import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "version" in data
    print("[PASS] /health test passed.")

def test_info():
    res = client.get("/v1/info")
    assert res.status_code == 200
    data = res.json()
    assert len(data["endpoints"]) >= 4
    print("[PASS] /v1/info test passed.")

def test_lint_with_student_bugs():
    # Buggy code:
    # 1. Blocking assignment '=' inside always @(posedge clk)
    # 2. Inferred latch risk in case statement without default
    buggy_verilog = """
    module bad_counter (
        input clk,
        input rst,
        input [1:0] mode,
        output reg [3:0] q,
        output reg [1:0] state_out
    );

        always @(posedge clk) begin
            if (rst)
                q = 4'b0000; // BUG: blocking '=' in sequential
            else
                q = q + 1;   // BUG: blocking '=' in sequential
        end

        always @(*) begin
            case (mode)
                2'b00: state_out = 2'b00;
                2'b01: state_out = 2'b10;
                // BUG: Missing default branch causes inferred latch!
            endcase
        end

    endmodule
    """
    res = client.post("/v1/rtl/lint", json={"code": buggy_verilog})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True or data["total_warnings"] > 0
    assert data["total_warnings"] >= 2
    
    rules = [issue["rule"] for issue in data["issues"]]
    assert "BLOCKING_IN_SEQUENTIAL" in rules
    assert "INFERRED_LATCH" in rules
    print(f"[PASS] /v1/rtl/lint identified {data['total_warnings']} educational hardware warnings.")

def test_lint_clean_code():
    clean_verilog = """
    module clean_counter (
        input clk,
        input rst_n,
        output reg [3:0] q
    );
        always @(posedge clk) begin
            if (!rst_n)
                q <= 4'b0000;
            else
                q <= q + 1'b1;
        end
    endmodule
    """
    res = client.post("/v1/rtl/lint", json={"code": clean_verilog})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["total_errors"] == 0
    assert data["total_warnings"] == 0
    print("[PASS] /v1/rtl/lint validated clean RTL code.")

def test_simulate():
    verilog = """
    module counter_4bit (
        input clk,
        input rst_n,
        input enable,
        output reg [3:0] count
    );
        always @(posedge clk) begin
            if (!rst_n)
                count <= 4'b0000;
            else if (enable)
                count <= count + 1'b1;
        end
    endmodule
    """
    res = client.post("/v1/rtl/simulate", json={
        "module_code": verilog,
        "cycles": 8,
        "reset_active_low": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["cycles_simulated"] == 8
    assert "$date" in data["vcd_content"]
    assert "$scope module" in data["vcd_content"]
    assert "wavedrom" in data
    assert len(data["wavedrom"]["signal"]) > 0
    print("[PASS] /v1/rtl/simulate generated VCD and WaveDrom timing diagrams.")

def test_schematic():
    verilog = """
    module alu (
        input [7:0] a,
        input [7:0] b,
        input [2:0] opcode,
        output reg [7:0] result,
        output reg carry_out
    );
        always @(*) begin
            case (opcode)
                3'b000: result = a + b;
                3'b001: result = a - b;
                default: result = 8'h00;
            endcase
        end
    endmodule
    """
    res = client.post("/v1/rtl/schematic", json={"code": verilog})
    assert res.status_code == 200
    data = res.json()
    assert data["module_name"] == "alu"
    assert len(data["ports"]) >= 3
    assert "flowchart LR" in data["mermaid_diagram"]
    print("[PASS] /v1/rtl/schematic generated port map & Mermaid schematic.")

def test_schematic_cpu_drilldown():
    cpu_verilog = """
    module cpu_pipeline (
        input clk,
        input rst_n,
        input [31:0] instr_in,
        input [31:0] alu_in_a,
        input [31:0] alu_in_b,
        input [2:0] idex_funct3,
        output reg [31:0] pc,
        output reg [31:0] ifid_pc,
        output reg [31:0] ifid_instr,
        output reg [31:0] alu_result
    );
        always @(posedge clk) begin
            if (!rst_n)
                pc <= 32'h0;
            else
                pc <= pc + 4;
        end

        always @(posedge clk) begin
            if (!rst_n) begin
                ifid_pc <= 32'h0;
                ifid_instr <= 32'h0;
            end else begin
                ifid_pc <= pc;
                ifid_instr <= instr_in;
            end
        end

        always @(*) begin
            case (idex_funct3)
                3'b000: alu_result = alu_in_a + alu_in_b;
                3'b001: alu_result = alu_in_a << 1;
                default: alu_result = 32'h0;
            endcase
        end
    endmodule
    """
    res = client.post("/v1/rtl/schematic", json={"code": cpu_verilog})
    assert res.status_code == 200
    data = res.json()
    assert "blocks" in data
    blocks = data["blocks"]
    assert len(blocks) >= 3
    
    # Check ALU block
    alu_blk = next((b for b in blocks if b["type"] == "alu"), None)
    assert alu_blk is not None
    assert "alu_result" in alu_blk["label"] or "ALU" in alu_blk["label"]
    assert alu_blk["verilog_snippet"] != ""
    assert len(alu_blk["internal_components"]) > 0
    assert alu_blk["bit_width"] == 32

    # Check Counter block
    cnt_blk = next((b for b in blocks if b["type"] == "counter" and "pc" in b["id"]), None)
    assert cnt_blk is not None
    assert cnt_blk["bit_width"] == 32
    assert "Adder" in " ".join(cnt_blk["internal_components"])

    # Check DFF blocks
    dff_blks = [b for b in blocks if b["type"] == "dff"]
    assert len(dff_blks) >= 2
    for d in dff_blks:
        assert d["bit_width"] == 32
        assert len(d["internal_components"]) > 0
        assert d["verilog_snippet"] != ""

    print("[PASS] /v1/rtl/schematic CPU blocks with drill-down metadata verified.")

def test_synthesize():
    verilog = """
    module counter_4bit (
        input clk,
        input rst_n,
        output reg [3:0] q
    );
        always @(posedge clk) begin
            if (!rst_n)
                q <= 4'b0000;
            else
                q <= q + 1;
        end
    endmodule
    """
    res = client.post("/v1/rtl/synthesize", json={
        "code": verilog,
        "target": "skywater130"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["module_name"] == "counter_4bit"
    assert data["flip_flops"] == 4
    assert data["total_cells"] > 0
    assert data["estimated_area_um2"] > 0
    assert "Yosys-Compatible Logic Synthesis" in data["report"]
    print(f"[PASS] /v1/rtl/synthesize: {data['total_cells']} cells, {data['estimated_area_um2']} um² SkyWater area, {data['estimated_fmax_mhz']} MHz Fmax.")

if __name__ == "__main__":
    test_health()
    test_info()
    test_lint_with_student_bugs()
    test_lint_clean_code()
    test_simulate()
    test_schematic()
    test_schematic_cpu_drilldown()
    test_synthesize()
    print("\nALL RTL CLOUD API TESTS PASSED SUCCESSFULLY! [OK]")
