import re
from typing import List, Tuple, Optional
from app.models import LintIssue, LintResponse
from app.services.teacher import get_advice_for_rule

class VerilogLinter:
    def __init__(self, code: str, top_module: Optional[str] = None, strict_mode: bool = False):
        self.raw_code = code
        self.lines = code.splitlines()
        self.top_module = top_module
        self.strict_mode = strict_mode
        self.issues: List[LintIssue] = []

    def analyze(self) -> LintResponse:
        self.issues = []
        
        # 1. Structural checks
        module_name = self._check_module_structure()
        self._check_begin_end_balance()
        
        # 2. Assignment & timing checks
        self._check_always_blocks()
        
        # 3. Latch inference checks
        self._check_latch_risks()

        # 4. Multi-driven net checks
        self._check_multi_driven_nets()

        # Count issues
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        tips = [i for i in self.issues if i.severity == "tip"]

        is_valid = len(errors) == 0
        if self.strict_mode and len(warnings) > 0:
            is_valid = False

        summary = self._generate_summary(len(errors), len(warnings), len(tips))

        return LintResponse(
            valid=is_valid,
            module_name=module_name or self.top_module,
            total_errors=len(errors),
            total_warnings=len(warnings),
            total_tips=len(tips),
            issues=self.issues,
            pedagogical_summary=summary
        )

    def _add_issue(self, line: Optional[int], severity: str, rule: str, message: str, fix_suggestion: str):
        advice = get_advice_for_rule(rule)
        explanation = f"{advice.get('why_it_happens', '')} {advice.get('why_it_is_bad', '')}".strip()
        self.issues.append(
            LintIssue(
                line=line,
                severity=severity,
                rule=rule,
                message=message,
                explanation=explanation,
                fix_suggestion=fix_suggestion
            )
        )

    def _check_module_structure(self) -> Optional[str]:
        has_module = False
        has_endmodule = False
        detected_name = None

        for idx, line in enumerate(self.lines, start=1):
            stripped = self._strip_comment(line)
            mod_match = re.search(r'\bmodule\s+([a-zA-Z_][a-zA-Z0-9_$]*)', stripped)
            if mod_match:
                has_module = True
                detected_name = mod_match.group(1)
            if re.search(r'\bendmodule\b', stripped):
                has_endmodule = True

        if not has_module:
            self._add_issue(
                line=1,
                severity="error",
                rule="MISSING_MODULE",
                message="No 'module' declaration found in source code.",
                fix_suggestion="Wrap your circuit definition in 'module module_name(...); ... endmodule'."
            )
        elif not has_endmodule:
            self._add_issue(
                line=len(self.lines),
                severity="error",
                rule="MISSING_ENDMODULE",
                message="Missing 'endmodule' keyword at the end of the file.",
                fix_suggestion="Add 'endmodule' after the last statement."
            )
        return detected_name

    def _check_begin_end_balance(self):
        begin_count = 0
        end_count = 0
        for idx, line in enumerate(self.lines, start=1):
            clean = self._strip_comment(line)
            # Match word boundaries for begin / end
            begins = len(re.findall(r'\bbegin\b', clean))
            ends = len(re.findall(r'\bend\b', clean))
            begin_count += begins
            end_count += ends

        if begin_count > end_count:
            self._add_issue(
                line=len(self.lines),
                severity="error",
                rule="UNBALANCED_BEGIN_END",
                message=f"Syntax Error: {begin_count - end_count} unclosed 'begin' block(s).",
                fix_suggestion="Ensure each 'begin' has a matching 'end'."
            )
        elif end_count > begin_count:
            self._add_issue(
                line=len(self.lines),
                severity="error",
                rule="UNBALANCED_BEGIN_END",
                message=f"Syntax Error: Extra 'end' keyword(s) with no matching 'begin'.",
                fix_suggestion="Check your nested blocks and remove extraneous 'end' statements."
            )

    def _check_always_blocks(self):
        current_block_type = None # 'seq', 'comb', or None
        block_start_line = 0

        for idx, line in enumerate(self.lines, start=1):
            clean = self._strip_comment(line)
            
            # Detect always @(posedge ... or negedge ...)
            if re.search(r'\balways\s*@\s*\(\s*(posedge|negedge)', clean) or 'always_ff' in clean:
                current_block_type = 'seq'
                block_start_line = idx
            # Detect always @(*) or always_comb
            elif re.search(r'\balways\s*@\s*\(\s*\*\s*\)', clean) or 'always_comb' in clean or re.search(r'\balways\s*@\s*\(', clean):
                if current_block_type != 'seq':
                    current_block_type = 'comb'
                    block_start_line = idx

            # If inside sequential block, check for blocking '='
            if current_block_type == 'seq':
                # Avoid matching '<=' or '==' or '!=' or '<=' in if conditions
                # Look for identifier followed by = (not <=, ==, !=, >=, <=)
                match = re.search(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*(?<![<>=!])=(?![=])\s*([^;]+);', clean)
                if match and 'for' not in clean: # allow for-loop index init
                    var_name = match.group(1)
                    self._add_issue(
                        line=idx,
                        severity="warning",
                        rule="BLOCKING_IN_SEQUENTIAL",
                        message=f"Blocking assignment '=' used for signal '{var_name}' in sequential always block.",
                        fix_suggestion=f"Change '{var_name} = ...;' to '{var_name} <= ...;' to avoid race conditions."
                    )

            # If inside combinational block, check for non-blocking '<='
            elif current_block_type == 'comb':
                match = re.search(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*<=\s*([^;]+);', clean)
                if match:
                    var_name = match.group(1)
                    self._add_issue(
                        line=idx,
                        severity="warning",
                        rule="NON_BLOCKING_IN_COMBINATIONAL",
                        message=f"Non-blocking assignment '<=' used for signal '{var_name}' in combinational block.",
                        fix_suggestion=f"Use blocking assignment '=' inside always @(*) blocks: '{var_name} = ...;'."
                    )

            if re.search(r'\bendmodule\b', clean):
                current_block_type = None

    def _check_latch_risks(self):
        in_comb = False
        has_if = False
        has_else = False
        in_case = False
        has_default = False
        case_start = 0

        for idx, line in enumerate(self.lines, start=1):
            clean = self._strip_comment(line)
            if re.search(r'\balways\s*@\s*\(\s*\*\s*\)', clean) or 'always_comb' in clean:
                in_comb = True

            if in_comb:
                if re.search(r'\bcase\s*\(', clean):
                    in_case = True
                    has_default = False
                    case_start = idx
                if in_case and re.search(r'\bdefault\s*:', clean):
                    has_default = True
                if in_case and re.search(r'\bendcase\b', clean):
                    if not has_default:
                        self._add_issue(
                            line=case_start,
                            severity="warning",
                            rule="INFERRED_LATCH",
                            message="Case statement inside combinational block has no 'default:' branch.",
                            fix_suggestion="Add 'default: out_signal = 0;' to prevent unintentional latch inference."
                        )
                    in_case = False

            if re.search(r'\bendmodule\b', clean):
                in_comb = False

    def _check_multi_driven_nets(self):
        drivers: dict[str, List[int]] = {}
        in_always = False
        always_idx = 0

        for idx, line in enumerate(self.lines, start=1):
            clean = self._strip_comment(line)
            if re.search(r'\balways\b', clean):
                in_always = True
                always_idx += 1

            # Detect continuous assign
            assign_match = re.search(r'\bassign\s+([a-zA-Z_][a-zA-Z0-9_$]*)\s*=', clean)
            if assign_match:
                net = assign_match.group(1)
                drivers.setdefault(net, []).append(idx)

            # Detect assignment inside always block
            if in_always:
                match = re.search(r'([a-zA-Z_][a-zA-Z0-9_$]*)\s*(?:<=|=)', clean)
                if match and 'if' not in clean and 'case' not in clean and 'for' not in clean:
                    net = match.group(1)
                    if net not in drivers:
                        drivers[net] = [idx]
                    elif idx not in drivers[net] and len(drivers[net]) > 0 and (idx - drivers[net][-1] > 20):
                        drivers[net].append(idx)

        for net, lines in drivers.items():
            if len(lines) > 1 and len(set(lines)) > 1:
                # Multiple places driving the same net
                self._add_issue(
                    line=lines[1],
                    severity="error",
                    rule="MULTI_DRIVEN_NET",
                    message=f"Signal '{net}' appears to be driven by multiple always blocks or continuous assignments.",
                    fix_suggestion=f"Ensure '{net}' is driven from only ONE procedural block or assign statement."
                )

    def _strip_comment(self, line: str) -> str:
        # Strip // comments
        idx = line.find('//')
        if idx != -1:
            return line[:idx]
        return line

    def _generate_summary(self, errors: int, warnings: int, tips: int) -> str:
        if errors == 0 and warnings == 0:
            return "Excellent design! Your RTL satisfies clean synthesizability rules with zero errors and no inferred latches."
        elif errors > 0:
            return f"Found {errors} critical error(s) that will prevent synthesis or simulation. Review the suggested fixes above."
        else:
            return f"Code compiles, but found {warnings} hardware warning(s). Pay close attention to blocking/non-blocking rules and latch inferences."
