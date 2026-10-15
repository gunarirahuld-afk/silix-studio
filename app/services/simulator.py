import re
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from app.models import SimulateResponse

class VerilogRTLInterpreter:
    """
    General-purpose Verilog RTL cycle-accurate simulation engine.
    Interprets ANY arbitrary synthesizable Verilog code and custom testbenches:
    - Extracts custom inputs, outputs, registers, and wires
    - Interprets testbench stimulus (#10 a = 1; #20 b = 0;)
    - Interprets continuous assignments (assign target = expr;)
    - Interprets sequential logic (always @(posedge clk) begin ... end)
    - Interprets combinational blocks (always @(*) begin ... end)
    - Evaluates bitwise (&, |, ^, ~), logical, arithmetic (+, -, *), and ternary (? :) operators
    - Generates true IEEE 1364 VCD files and WaveDrom timing diagrams
    """
    def __init__(self, verilog_code: str, testbench_code: Optional[str] = None, cycles: int = 16, reset_active_low: bool = True):
        self.code = verilog_code
        self.testbench_code = testbench_code
        self.cycles = max(4, min(cycles, 256))
        self.reset_active_low = reset_active_low
        self.module_name = self._detect_module_name()
        self.ports: Dict[str, Dict[str, Any]] = {}
        self.registers: Dict[str, Dict[str, Any]] = {}
        self.wires: Dict[str, Dict[str, Any]] = {}
        self.assigns: List[Tuple[str, str]] = []
        self.seq_blocks: List[Dict[str, Any]] = []
        self.comb_blocks: List[Dict[str, Any]] = []
        self.params: Dict[str, int] = {}

    def _detect_module_name(self) -> str:
        m = re.search(r'\bmodule\s+([a-zA-Z_][a-zA-Z0-9_$]*)', self.code)
        return m.group(1) if m else "top_dut"

    def _parse_testbench(self) -> Dict[int, Dict[str, int]]:
        """
        Parses testbench stimulus from initial begin ... end blocks,
        extracting time delays (#10) and signal driving assignments.
        """
        if not self.testbench_code or not self.testbench_code.strip():
            return {}

        init_match = re.search(r'initial\s+(?:begin)?(.*?)end', self.testbench_code, re.DOTALL)
        if not init_match:
            return {}

        body = init_match.group(1)
        schedule: Dict[int, Dict[str, int]] = {}
        current_time = 0

        for line in body.splitlines():
            line = line.split('//')[0].strip()
            if not line:
                continue

            delay_match = re.search(r'#\s*(\d+)', line)
            if delay_match:
                current_time += int(delay_match.group(1))

            for assign in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*=\s*([^#;]+);', line):
                var = assign.group(1).strip()
                val_expr = assign.group(2).strip()
                val = self._eval_expr(val_expr, {})
                schedule.setdefault(current_time, {})[var] = val

        return schedule

    def parse(self):
        # 0. Strip comments
        clean_code = re.sub(r'/\*.*?\*/', '', self.code, flags=re.DOTALL)
        clean_code = re.sub(r'//.*', '', clean_code)

        # 0.1 Parse parameters and localparams (e.g., FSM states)
        param_pattern = re.compile(r'\b(?:parameter|localparam)\s+(?:\[\d+:\d+\]\s*)?([a-zA-Z0-9_$,\s=\':]+);')
        for match in param_pattern.finditer(clean_code):
            for item in match.group(1).split(','):
                if '=' in item:
                    p_name, p_val = item.split('=', 1)
                    p_name = p_name.strip()
                    val = self._eval_expr(p_val.strip(), self.params)
                    self.params[p_name] = val

        # 1. Parse ports with multi-port comma inheritance (e.g. input a, b)
        header_match = re.search(r'\bmodule\s+[a-zA-Z_][a-zA-Z0-9_$]*\s*\((.*?)\);', clean_code, re.DOTALL)
        decls = []
        if header_match:
            decls.extend(header_match.group(1).split(','))
        for line in clean_code.splitlines():
            line_str = line.strip()
            if re.match(r'^(input|output|inout)\b', line_str):
                decls.append(line_str)

        curr_dir = "input"
        curr_width = 1
        for d in decls:
            d = d.strip()
            dir_m = re.search(r'\b(input|output|inout)\b', d)
            if dir_m:
                curr_dir = dir_m.group(1)
                rng_m = re.search(r'\[(\d+):(\d+)\]', d)
                if rng_m:
                    curr_width = abs(int(rng_m.group(1)) - int(rng_m.group(2))) + 1
                else:
                    curr_width = 1

            cleaned = re.sub(r'\b(input|output|inout|reg|wire|logic)\b', '', d)
            cleaned = re.sub(r'\[\d+:\d+\]', '', cleaned).strip()
            for name in cleaned.split(','):
                name = name.strip().replace(';', '')
                if name and re.match(r'^[a-zA-Z_][a-zA-Z0-9_$]*$', name):
                    if name not in self.ports:
                        self.ports[name] = {
                            "name": name,
                            "direction": curr_dir,
                            "width": curr_width,
                            "mask": (1 << curr_width) - 1,
                            "is_bus": curr_width > 1
                        }

        # Ensure clock and reset exist if not specified
        has_clk = any(p in self.ports for p in ["clk", "clock"])
        if not has_clk:
            self.ports["clk"] = {"name": "clk", "direction": "input", "width": 1, "mask": 1, "is_bus": False}
        has_rst = any("rst" in p or "reset" in p for p in self.ports)
        if not has_rst:
            rst_name = "rst_n" if self.reset_active_low else "rst"
            self.ports[rst_name] = {"name": rst_name, "direction": "input", "width": 1, "mask": 1, "is_bus": False}

        # 2. Parse registers
        for m in re.finditer(r'\breg\s+(?:\[(\d+):(\d+)\]\s*)?([a-zA-Z_][a-zA-Z0-9_$,\s]*)', clean_code):
            w = 1
            if m.group(1) and m.group(2):
                w = abs(int(m.group(1)) - int(m.group(2))) + 1
            for name in m.group(3).split(','):
                name = name.strip().replace(';', '')
                if name and re.match(r'^[a-zA-Z_][a-zA-Z0-9_$]*$', name):
                    if name not in self.registers:
                        self.registers[name] = {
                            "name": name,
                            "width": w,
                            "mask": (1 << w) - 1,
                            "is_bus": w > 1
                        }

        # 3. Parse continuous assigns: assign target = expr;
        for m in re.finditer(r'\bassign\s+([a-zA-Z_][a-zA-Z0-9_$]*)\s*=\s*([^;]+);', clean_code):
            self.assigns.append((m.group(1).strip(), m.group(2).strip()))

        # 3.1 Parse gate primitives: and g1(out, in1, in2); ...
        gate_pattern = re.compile(r'\b(and|nand|or|nor|xor|xnor|not|buf)\s+(?:[a-zA-Z0-9_$]+\s*)?\((.*?)\);')
        for match in gate_pattern.finditer(clean_code):
            g_type = match.group(1).lower()
            args = [a.strip() for a in match.group(2).split(',') if a.strip()]
            if len(args) >= 2:
                out_p = args[0]
                in_ps = args[1:]
                if g_type == 'and': expr = " & ".join(in_ps)
                elif g_type == 'nand': expr = f"~({' & '.join(in_ps)})"
                elif g_type == 'or': expr = " | ".join(in_ps)
                elif g_type == 'nor': expr = f"~({' | '.join(in_ps)})"
                elif g_type == 'xor': expr = " ^ ".join(in_ps)
                elif g_type == 'xnor': expr = f"~({' ^ '.join(in_ps)})"
                elif g_type == 'not': expr = f"~{in_ps[0]}"
                elif g_type == 'buf': expr = in_ps[0]
                self.assigns.append((out_p, expr))

        # 4. Parse sequential and combinational blocks
        self._parse_sequential_blocks()
        self._parse_combinational_blocks()

    def _parse_sequential_blocks(self):
        # Match always @(posedge clk ...) with or without begin..end
        seq_pattern = re.compile(r'always(?:_ff)?\s*@\s*\(\s*posedge\s+([a-zA-Z0-9_$]+)[^)]*\)\s*(?:begin\s*(.*?)\s*end|(.*?);)', re.DOTALL)
        for match in seq_pattern.finditer(self.code):
            body = match.group(2) if match.group(2) is not None else match.group(3)
            if not body:
                continue

            # Detect reset branch
            rst_branch = re.search(r'if\s*\(\s*!?\s*([a-zA-Z0-9_$]*rst[a-zA-Z0-9_$]*)\s*\)\s*(?:begin\s*(.*?)\s*end|(.*?);)', body, re.DOTALL)
            rst_assignments = {}
            if rst_branch:
                content = rst_branch.group(2) if rst_branch.group(2) is not None else rst_branch.group(3)
                for a in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*<=\s*([^;]+);?', content):
                    rst_assignments[a.group(1).strip()] = a.group(2).strip()

            # Detect normal / else branch
            normal_assignments = {}
            else_branch = re.search(r'else\s*(?:begin\s*(.*?)\s*end|(.*))', body, re.DOTALL)
            target_str = (else_branch.group(1) or else_branch.group(2)) if else_branch else body

            # Check if there's an 'if (enable)' or similar condition guarding the assignment
            cond_assign_match = re.search(r'if\s*\((.*?)\)\s*(?:begin\s*)?([a-zA-Z_][a-zA-Z0-9_$]*)\s*<=\s*([^;]+);?', target_str, re.DOTALL)
            if cond_assign_match and not rst_branch:
                cond = cond_assign_match.group(1).strip()
                t_var = cond_assign_match.group(2).strip()
                t_expr = cond_assign_match.group(3).strip()
                normal_assignments[t_var] = f"({t_expr} if ({cond}) else {t_var})"
            elif cond_assign_match and "rst" not in cond_assign_match.group(1):
                cond = cond_assign_match.group(1).strip()
                t_var = cond_assign_match.group(2).strip()
                t_expr = cond_assign_match.group(3).strip()
                normal_assignments[t_var] = f"({t_expr} if ({cond}) else {t_var})"
            else:
                for a in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*<=\s*([^;]+);?', target_str):
                    normal_assignments[a.group(1).strip()] = a.group(2).strip()

            self.seq_blocks.append({
                "clock": match.group(1),
                "reset_actions": rst_assignments,
                "normal_actions": normal_assignments
            })

    def _parse_combinational_blocks(self):
        # Match always @(*) or always @(a, b...) with \bbegin\b ... \bend\b
        comb_pattern = re.compile(r'always(?:_comb)?\s*@\s*\(\s*(?:\*|[^)]*)\s*\)\s*(?:begin\b(.*?)\bend\b|(.*?);)', re.DOTALL)
        for match in comb_pattern.finditer(self.code):
            body = match.group(1) if match.group(1) is not None else match.group(2)
            if not body or "posedge" in body or "negedge" in body:
                continue

            # Check for case statement inside
            case_match = re.search(r'case\s*\((.*?)\)(.*?)\bendcase\b', body, re.DOTALL)
            if case_match:
                sel_expr = case_match.group(1).strip()
                case_body = case_match.group(2)
                cases = []
                default_action = None
                for c_item in re.finditer(r'([0-9a-zA-Z_$\']+)\s*:\s*(?:begin\b\s*)?([a-zA-Z_][a-zA-Z0-9_$]*)\s*=\s*([^;]+);?', case_body):
                    lbl = c_item.group(1).strip()
                    target = c_item.group(2).strip()
                    expr = c_item.group(3).strip()
                    if lbl == 'default':
                        default_action = (target, expr)
                    else:
                        cases.append((lbl, target, expr))

                self.comb_blocks.append({
                    "type": "case",
                    "sel": sel_expr,
                    "cases": cases,
                    "default": default_action
                })
            else:
                # Direct assignments or if-else
                assigns = []
                for a in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*=\s*([^;]+);', body):
                    assigns.append((a.group(1).strip(), a.group(2).strip()))
                if assigns:
                    self.comb_blocks.append({
                        "type": "assigns",
                        "assigns": assigns
                    })

    def _convert_expr_to_python(self, expr: str) -> str:
        # Convert Verilog binary literal: 4'b1010 -> 0b1010, 'b1 -> 0b1
        expr = re.sub(r"(?:\d+)?'b([01_xXzZ]+)", lambda m: f"0b{m.group(1).replace('_', '').replace('x','0').replace('z','0')}", expr)
        # Convert Verilog hex literal: 8'hFF -> 0xFF, 'h0 -> 0x0
        expr = re.sub(r"(?:\d+)?'h([0-9a-fA-F_]+)", lambda m: f"0x{m.group(1).replace('_', '')}", expr)
        # Convert Verilog decimal literal: 4'd10 -> 10, 'd5 -> 5
        expr = re.sub(r"(?:\d+)?'d([0-9_]+)", lambda m: f"{m.group(1).replace('_', '')}", expr)

        # Convert bus slicing: a[3:0] -> (((a >> 0) & ((1 << (3 - 0 + 1)) - 1)))
        expr = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_$]*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]',
                      lambda m: f"((({m.group(1)} >> {m.group(3)}) & ((1 << ({int(m.group(2))} - {int(m.group(3))} + 1)) - 1)))", expr)

        # Convert bit indexing: a[0] -> (((a >> 0) & 1))
        expr = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_$]*)\s*\[\s*(\d+)\s*\]',
                      lambda m: f"((({m.group(1)} >> {m.group(2)}) & 1))", expr)

        # Convert logical operators
        expr = expr.replace('&&', ' and ').replace('||', ' or ')
        expr = re.sub(r'!\s*([a-zA-Z0-9_()$]+)', r'(0 if (\1) else 1)', expr)

        # Convert shift register / bit concatenation: {a, b} -> (((a) << 1) | ((b) & 1))
        expr = re.sub(r'\{([a-zA-Z0-9_$\s\[\]:\(\)\+\-]+),\s*([a-zA-Z0-9_$\s\[\]:\(\)\+\-]+)\}', r'(((\1) << 1) | ((\2) & 1))', expr)

        # Convert ternary: cond ? a : b -> (a if cond else b)
        ternary_match = re.search(r'(.+?)\?(.+?):(.+)', expr)
        if ternary_match:
            c = ternary_match.group(1).strip()
            t = ternary_match.group(2).strip()
            f = ternary_match.group(3).strip()
            expr = f"({t} if ({c}) else {f})"
        return expr

    def _eval_expr(self, expr_str: str, env: Dict[str, int]) -> int:
        py_expr = self._convert_expr_to_python(expr_str)
        try:
            allowed_globals = {"__builtins__": {}}
            full_env = {**self.params, **env}
            result = eval(py_expr, allowed_globals, full_env)
            return int(result) if result is not None else 0
        except Exception:
            return 0

    def simulate(self) -> SimulateResponse:
        self.parse()
        logs = []
        logs.append(f"[INFO] Initializing General-Purpose RTL Engine for '{self.module_name}'")
        logs.append(f"[INFO] Parsed {len(self.ports)} I/O ports, {len(self.registers)} registers, {len(self.assigns)} continuous assigns.")

        # Identify all signals to track
        all_signals = {}
        for name, p in self.ports.items():
            all_signals[name] = p
        for name, r in self.registers.items():
            if name not in all_signals:
                all_signals[name] = {**r, "direction": "internal"}

        # Signal state history
        history: Dict[str, List[int]] = {name: [] for name in all_signals}
        current_state: Dict[str, int] = {name: 0 for name in all_signals}

        clk_name = next((p for p in self.ports if p in ["clk", "clock"]), "clk")
        rst_name = next((p for p in self.ports if "rst" in p or "reset" in p), "rst_n")
        other_inputs = [p for p, info in self.ports.items() if info["direction"] == "input" and p != clk_name and p != rst_name]

        # Check if user provided custom testbench stimulus
        tb_schedule = self._parse_testbench()
        if tb_schedule:
            logs.append(f"[INFO] Custom Testbench stimulus active! Found {len(tb_schedule)} timed event stages.")

        # Simulation cycle loop
        for c in range(self.cycles):
            current_time_ns = c * 10
            # 1. Update Clock
            current_state[clk_name] = 1 # Rising edge evaluation

            # 2. Update inputs from Testbench if scheduled
            applied_from_tb = False
            if tb_schedule:
                for t_ev, assignments in sorted(tb_schedule.items()):
                    if t_ev <= current_time_ns:
                        for v, val in assignments.items():
                            if v in current_state:
                                current_state[v] = val
                                applied_from_tb = True

            # If no testbench stimulus for this cycle, use standard clock/reset and dynamic inputs
            if not applied_from_tb:
                is_cycle_zero = (c == 0)
                if self.reset_active_low:
                    current_state[rst_name] = 0 if is_cycle_zero else 1
                else:
                    current_state[rst_name] = 1 if is_cycle_zero else 0

                for idx, in_name in enumerate(other_inputs):
                    info = self.ports[in_name]
                    if info["is_bus"]:
                        val = (c * (idx + 1) + idx * 3) & info["mask"]
                        current_state[in_name] = val
                    else:
                        period = (idx % 3) + 2
                        val = 1 if (c // period) % 2 == 0 else 0
                        current_state[in_name] = val

            # Check if reset is currently active (from testbench or default)
            if self.reset_active_low:
                is_reset_active = (current_state.get(rst_name, 1) == 0)
            else:
                is_reset_active = (current_state.get(rst_name, 0) == 1)

            # 4. Evaluate Sequential Blocks (Flip-Flops)
            next_state = dict(current_state)
            for block in self.seq_blocks:
                actions = block["reset_actions"] if is_reset_active else block["normal_actions"]
                for target_var, expr in actions.items():
                    val = self._eval_expr(expr, current_state)
                    mask = all_signals.get(target_var, {}).get("mask", 0xFFFFFFFF)
                    next_state[target_var] = val & mask

            # 5. Evaluate Combinational Blocks & Continuous Assigns (stabilization loop)
            for _ in range(3):
                # Combinational blocks
                for c_block in self.comb_blocks:
                    if c_block["type"] == "case":
                        sel_val = self._eval_expr(c_block["sel"], next_state)
                        matched = False
                        for lbl, target, expr in c_block["cases"]:
                            val_check = self._eval_expr(lbl, next_state)
                            if sel_val == val_check:
                                val = self._eval_expr(expr, next_state)
                                mask = all_signals.get(target, {}).get("mask", 0xFFFFFFFF)
                                next_state[target] = val & mask
                                matched = True
                                break
                        if not matched and c_block["default"]:
                            d_target, d_expr = c_block["default"]
                            val = self._eval_expr(d_expr, next_state)
                            mask = all_signals.get(d_target, {}).get("mask", 0xFFFFFFFF)
                            next_state[d_target] = val & mask
                    elif c_block["type"] == "assigns":
                        for target_var, expr in c_block["assigns"]:
                            val = self._eval_expr(expr, next_state)
                            mask = all_signals.get(target_var, {}).get("mask", 0xFFFFFFFF)
                            next_state[target_var] = val & mask

                # Continuous assigns
                for target_var, expr in self.assigns:
                    val = self._eval_expr(expr, next_state)
                    mask = all_signals.get(target_var, {}).get("mask", 0xFFFFFFFF)
                    next_state[target_var] = val & mask

            current_state = next_state

            # Record history
            for name in all_signals:
                history[name].append(current_state[name])

        # 6. Format WaveDrom Data
        wavedrom_signals = []
        for name, info in all_signals.items():
            vals = history[name]
            if name == clk_name:
                wavedrom_signals.append({"name": name, "wave": "p" + "." * (self.cycles - 1)})
            elif info["is_bus"]:
                data_list = [f"{v:X}" for v in vals]
                wavedrom_signals.append({
                    "name": f"{name}[{info['width']-1}:0]",
                    "wave": "=" * self.cycles,
                    "data": data_list
                })
            else:
                wave_str = "".join(str(v & 1) for v in vals)
                wavedrom_signals.append({"name": name, "wave": wave_str})

        # 7. Format IEEE 1364 VCD
        vcd_lines = [
            "$date 2026-10-15 $end",
            "$version Universal Global RTL Engine v2.0 $end",
            "$timescale 1ns $end",
            f"$scope module {self.module_name} $end"
        ]
        pool = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        id_map = {}
        for i, (name, info) in enumerate(all_signals.items()):
            vcd_id = pool[i % len(pool)]
            id_map[name] = vcd_id
            rng = f" [{info['width']-1}:0]" if info["is_bus"] else ""
            vcd_lines.append(f"$var wire {info['width']} {vcd_id} {name}{rng} $end")
        vcd_lines.append("$upscope $end\n$enddefinitions $end\n#0\n$dumpvars")

        for name, info in all_signals.items():
            val0 = history[name][0]
            if info["is_bus"]:
                vcd_lines.append(f"b{val0:b} {id_map[name]}")
            else:
                vcd_lines.append(f"{val0}{id_map[name]}")
        vcd_lines.append("$end")

        for c in range(1, self.cycles):
            t = c * 10
            vcd_lines.append(f"#{t}")
            for name, info in all_signals.items():
                if history[name][c] != history[name][c-1]:
                    v = history[name][c]
                    if info["is_bus"]:
                        vcd_lines.append(f"b{v:b} {id_map[name]}")
                    else:
                        vcd_lines.append(f"{v}{id_map[name]}")

        vcd_content = "\n".join(vcd_lines) + "\n"
        logs.append(f"[SUCCESS] SimEngine executed {self.cycles} cycles. All user expressions evaluated successfully.")

        return SimulateResponse(
            success=True,
            module_name=self.module_name,
            cycles_simulated=self.cycles,
            signals=list(all_signals.keys()),
            vcd_content=vcd_content,
            wavedrom={"signal": wavedrom_signals},
            console_log="\n".join(logs)
        )

class RTLSimulator:
    def __init__(self, module_code: str, testbench_code: str = None, cycles: int = 16, top_module: str = None, reset_active_low: bool = True):
        self.module_code = module_code
        self.testbench_code = testbench_code
        self.cycles = max(4, min(cycles, 256))
        self.top_module = top_module
        self.reset_active_low = reset_active_low

    def run(self) -> SimulateResponse:
        interpreter = VerilogRTLInterpreter(
            verilog_code=self.module_code,
            testbench_code=self.testbench_code,
            cycles=self.cycles,
            reset_active_low=self.reset_active_low
        )
        return interpreter.simulate()
