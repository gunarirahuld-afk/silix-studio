"""
Pedagogical guidance and educational explanations for RTL designers, students, and freshers.
Translates cryptic hardware/EDA issues into intuitive, real-world silicon concepts.
"""

from typing import Dict, Any

TEACHING_GUIDELINES: Dict[str, Dict[str, str]] = {
    "INFERRED_LATCH": {
        "concept": "Unintentional Inferred Latch",
        "why_it_happens": (
            "In combinational logic (e.g. `always @(*)` or `always_comb`), if a signal is not assigned "
            "a value under every single possible condition (missing `else` or missing `default` in a `case` statement), "
            "the synthesizer must preserve the signal's old value. To do this, it infers a level-sensitive LATCH."
        ),
        "why_it_is_bad": (
            "Latches are asynchronous and prone to timing hazards, glitches, and race conditions. "
            "In modern synchronous FPGA/ASIC flows, static timing analysis (STA) and scan testing (DFT) "
            "are significantly complicated by latches. 99% of the time, this is an unintentional student bug."
        ),
        "how_to_fix": (
            "1. Give every variable a default value at the very top of the `always @(*)` block before any `if` statements.\n"
            "2. Ensure every `if` has an `else` branch.\n"
            "3. Ensure every `case` statement has a `default:` branch."
        ),
        "example_bad": (
            "always @(*) begin\n"
            "    if (sel == 1'b1)\n"
            "        out = data_in; // BUG: What happens when sel == 0? Latches!\n"
            "end"
        ),
        "example_good": (
            "always @(*) begin\n"
            "    out = 1'b0; // Default assignment prevents latch inference\n"
            "    if (sel == 1'b1)\n"
            "        out = data_in;\n"
            "end"
        )
    },
    "BLOCKING_IN_SEQUENTIAL": {
        "concept": "Blocking Assignment (=) in Sequential Block",
        "why_it_happens": (
            "Using `=` instead of `<=` inside an edge-triggered sequential block (`always @(posedge clk)`)."
        ),
        "why_it_is_bad": (
            "Blocking assignments execute immediately in simulator event queues, creating simulation vs. synthesis "
            "mismatches. If two flip-flops communicate, blocking assignments can cause one flip-flop to update "
            "prematurely, leading to hold-time violations or incorrect race conditions in simulation that don't match silicon."
        ),
        "how_to_fix": (
            "Always follow the golden rule of RTL design:\n"
            "- Use non-blocking (`<=`) for sequential logic (`always @(posedge clk)`).\n"
            "- Use blocking (`=`) for combinational logic (`always @(*)`)."
        )
    },
    "NON_BLOCKING_IN_COMBINATIONAL": {
        "concept": "Non-Blocking Assignment (<=) in Combinational Block",
        "why_it_happens": (
            "Using `<=` instead of `=` inside a combinational block (`always @(*)`)."
        ),
        "why_it_is_bad": (
            "Non-blocking assignments schedule updates for the end of the simulation delta-cycle. "
            "In combinational logic, this wastes simulator performance and can cause multi-cycle glitches during evaluation."
        ),
        "how_to_fix": "Change `<=` to `=` inside `always @(*)` blocks."
    },
    "MULTI_DRIVEN_NET": {
        "concept": "Multi-Driven Net (Multiple Drivers on One Signal)",
        "why_it_happens": (
            "The same `reg` or `wire` is being assigned values in two different `always` blocks or continuous `assign` statements."
        ),
        "why_it_is_bad": (
            "In physical hardware, this connects the outputs of two physical drivers directly to each other! "
            "If one driver outputs 1 (Vdd) and the other outputs 0 (GND), a dead short circuit occurs, resulting in "
            "an indeterminate logic state ('X') and potential hardware damage in real silicon."
        ),
        "how_to_fix": (
            "Ensure each signal is driven by exactly ONE `always` block or ONE `assign` statement. "
            "If you need arbitration between sources, use a multiplexer."
        )
    },
    "RESET_BEST_PRACTICE": {
        "concept": "Asynchronous vs Synchronous Reset Best Practices",
        "why_it_happens": (
            "Digital systems require predictable startup states across millions of flip-flops."
        ),
        "why_it_is_bad": (
            "Uninitialized registers power up in unpredictable states ('X'), corrupting state machines and data pipelines."
        ),
        "how_to_fix": (
            "For ASIC designs, active-low asynchronous reset with synchronous de-assertion is standard (`if (!rst_n)`).\n"
            "For Xilinx FPGAs, active-high synchronous reset is preferred by the DSP and slice architecture."
        )
    }
}

def get_advice_for_rule(rule: str) -> Dict[str, str]:
    return TEACHING_GUIDELINES.get(rule, {
        "concept": rule,
        "why_it_happens": "General hardware design guideline.",
        "why_it_is_bad": "May result in hardware inefficiency, synthesis warnings, or simulation mismatches.",
        "how_to_fix": "Review IEEE 1364 / IEEE 1800 standards for clean synthesizable RTL."
    })
