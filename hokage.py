#!/usr/bin/env python3
"""
Hokage - The Ninja Orchestrator

The Hokage commands ninjas (small models) and coordinates complex tasks.
This is the "Hexa" layer that routes tasks to specialist ninjas.

Architecture:
    User → Hokage → [Parser Ninja, Calculator Ninja, Writer Ninja, ...]
                         ↓
                     Scrolls (9S)

Key Concepts:
- Ninjas are specialists (one model, one task)
- Hokage routes and synthesizes
- All results are Scrolls (9S compatible)
- The Linux box at 192.168.86.20 runs Ollama

"Many small, sharp tools > one monolithic model"
"""

import requests
import json
import time
import re
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from scroll import Scroll, Meta


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NINJA (Small Model Agent)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Ninja:
    """
    A specialized small model agent.

    Each ninja:
    - Has a specialty (system prompt)
    - Has skills (prompt templates)
    - Returns Scrolls
    """

    def __init__(
        self,
        name: str,
        model: str = "qwen2.5:1.5b",
        system: str = "",
        skills: Dict[str, str] = None,
        ollama_url: str = "http://localhost:11434/api/generate",
    ):
        self.name = name
        self.model = model
        self.system = system
        self.skills = skills or {}
        self.ollama_url = ollama_url
        self.call_count = 0

    def call(self, prompt: str, **kwargs) -> Scroll:
        """
        Execute a prompt and return a Scroll.
        """
        self.call_count += 1
        start = time.time()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if self.system:
            payload["system"] = self.system

        try:
            r = requests.post(self.ollama_url, json=payload, timeout=60)
            r.raise_for_status()
            response = r.json()["response"]
            elapsed = time.time() - start

            # Return as Scroll
            return Scroll(
                f"/ninja/{self.name}/call_{self.call_count}",
                {
                    "response": response,
                    "model": self.model,
                    "elapsed": elapsed,
                    "prompt": prompt[:100],
                },
                Meta(schema="dojo/ninja_result"),
            )

        except Exception as e:
            elapsed = time.time() - start
            return Scroll(
                f"/ninja/{self.name}/error_{self.call_count}",
                {
                    "error": str(e),
                    "model": self.model,
                    "elapsed": elapsed,
                },
                Meta(schema="dojo/error"),
            )

    def use_skill(self, skill_name: str, **kwargs) -> Scroll:
        """Use a predefined skill (prompt template)."""
        if skill_name not in self.skills:
            return Scroll(
                f"/ninja/{self.name}/error",
                {"error": f"Unknown skill: {skill_name}"},
                Meta(schema="dojo/error"),
            )

        template = self.skills[skill_name]
        prompt = template.format(**kwargs)
        return self.call(prompt)

    def clone(self, suffix: str = "_clone") -> 'Ninja':
        """Clone for parallel work."""
        return Ninja(
            name=self.name + suffix,
            model=self.model,
            system=self.system,
            skills=self.skills.copy(),
            ollama_url=self.ollama_url,
        )

    def __repr__(self) -> str:
        return f"Ninja({self.name}, {self.model})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPECIALIZED NINJAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_parser_ninja(ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
    """Ninja specialized in parsing text to JSON."""
    return Ninja(
        name="Parser",
        model="qwen2.5:1.5b",
        ollama_url=ollama_url,
        system="""You are a precise parser. Extract structured data from text.
Output ONLY valid JSON. No explanations, no markdown, just JSON.""",
        skills={
            "invoice": """Parse this invoice description into JSON.
Schema: {{"client": "name", "lineItems": [{{"description": "what", "quantity": number, "rate": number}}]}}

Input: "{text}"
Output:""",
            "contact": """Extract contact info from this text.
Schema: {{"name": "string", "email": "string or null", "phone": "string or null"}}

Input: "{text}"
Output:""",
        },
    )


def create_calculator_ninja(ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
    """Ninja specialized in calculations."""
    return Ninja(
        name="Calculator",
        model="qwen2.5:1.5b",
        ollama_url=ollama_url,
        system="""You are a precise calculator. Do math and return only numbers.
No explanations. Just the final number.""",
        skills={
            "total": """Calculate the total: {items}
Return ONLY the number:""",
            "tax": """Calculate {rate}% of {amount}.
Return ONLY the number:""",
        },
    )


def create_writer_ninja(ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
    """Ninja specialized in writing text."""
    return Ninja(
        name="Writer",
        model="qwen2.5:1.5b",
        ollama_url=ollama_url,
        system="""You are a concise writer. Write clear, professional text.
Be brief. No fluff.""",
        skills={
            "summary": """Summarize this in 1-2 sentences:
{text}

Summary:""",
            "email": """Write a brief professional email about: {topic}
To: {recipient}

Email:""",
        },
    )


def create_dialectic_ninja(ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
    """Ninja that thinks dialectically."""
    return Ninja(
        name="Dialectic",
        model="qwen2.5:1.5b",
        ollama_url=ollama_url,
        system="""You are a dialectical thinker.
For every problem, identify:
1. THESIS: The current state or obvious solution
2. ANTITHESIS: What opposes or contradicts it
3. SYNTHESIS: A higher unity that transcends both

Be concise.""",
        skills={
            "analyze": """Apply dialectical analysis to this problem:
{problem}

THESIS:
ANTITHESIS:
SYNTHESIS:""",
        },
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HOKAGE (Orchestrator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Hokage:
    """
    The Ninja Orchestrator.

    Routes tasks to specialist ninjas, synthesizes results.
    This is "Hexa" - the coordinating intelligence.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate"):
        self.ollama_url = ollama_url
        self.ninjas: Dict[str, Ninja] = {}
        self.task_count = 0

        # Initialize standard ninjas
        self.ninjas["parser"] = create_parser_ninja(ollama_url)
        self.ninjas["calculator"] = create_calculator_ninja(ollama_url)
        self.ninjas["writer"] = create_writer_ninja(ollama_url)
        self.ninjas["dialectic"] = create_dialectic_ninja(ollama_url)

    def add_ninja(self, ninja: Ninja):
        """Add a custom ninja."""
        self.ninjas[ninja.name.lower()] = ninja

    def get_ninja(self, name: str) -> Optional[Ninja]:
        """Get a ninja by name."""
        return self.ninjas.get(name.lower())

    def parse_invoice(self, raw: str) -> Scroll:
        """Parse invoice text to structured data."""
        self.task_count += 1

        # Step 1: Parse with parser ninja
        parser = self.ninjas["parser"]
        parsed_scroll = parser.use_skill("invoice", text=raw)

        # Extract JSON from response
        response = parsed_scroll.data.get("response", "")
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = {"client": "Unknown", "lineItems": []}
        except json.JSONDecodeError:
            parsed = {"client": "Unknown", "lineItems": []}

        # Step 2: Calculate total (pure function - no LLM needed)
        total = sum(
            float(item.get("quantity", 0)) * float(item.get("rate", 0))
            for item in parsed.get("lineItems", [])
        )

        # Return final scroll
        return Scroll(
            f"/hokage/invoice_{self.task_count}",
            {
                "raw": raw,
                "client": parsed.get("client", "Unknown"),
                "lineItems": parsed.get("lineItems", []),
                "total": total,
                "parseTime": parsed_scroll.data.get("elapsed", 0),
            },
            Meta(schema="beebill/invoice"),
        )

    def parallel_parse(self, items: List[str]) -> List[Scroll]:
        """Parse multiple items in parallel using cloned ninjas."""
        results = []

        with ThreadPoolExecutor(max_workers=len(items)) as executor:
            # Clone parser for each item
            futures = {}
            for i, item in enumerate(items):
                clone = self.ninjas["parser"].clone(f"_{i}")
                future = executor.submit(clone.use_skill, "invoice", text=item)
                futures[future] = item

            # Collect results
            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(Scroll(
                        "/hokage/error",
                        {"error": str(e), "input": item},
                        Meta(schema="dojo/error"),
                    ))

        return results

    def analyze_dialectically(self, problem: str) -> Scroll:
        """Apply dialectic analysis to a problem."""
        self.task_count += 1
        dialectic = self.ninjas["dialectic"]
        return dialectic.use_skill("analyze", problem=problem)

    def summarize(self, text: str) -> Scroll:
        """Summarize text."""
        self.task_count += 1
        writer = self.ninjas["writer"]
        return writer.use_skill("summary", text=text)

    def status(self) -> Dict:
        """Get Hokage status."""
        return {
            "ninjas": list(self.ninjas.keys()),
            "ninja_count": len(self.ninjas),
            "tasks_completed": self.task_count,
            "ollama_url": self.ollama_url,
        }

    def __repr__(self) -> str:
        return f"Hokage(ninjas={list(self.ninjas.keys())}, tasks={self.task_count})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def demo():
    """Demo the Hokage orchestrating ninjas."""

    print("=" * 60)
    print("HOKAGE - Ninja Orchestrator Demo")
    print("=" * 60)

    # Initialize with local Ollama (will fail on Mac, works on Linux box)
    # For remote: use "http://192.168.86.20:11434/api/generate"
    hokage = Hokage()

    print(f"\nHokage Status: {hokage.status()}")

    # Test invoice parsing
    print("\n[1] INVOICE PARSING")
    test_invoices = [
        "3 hours consulting for Acme Corp at $150/hr",
        "Website redesign - 10 pages at $500/page for TechStartup",
        "Monthly retainer $2000 for Jane Doe",
    ]

    for raw in test_invoices:
        print(f"\nInput: {raw}")
        try:
            result = hokage.parse_invoice(raw)
            print(f"  Client: {result.data['client']}")
            print(f"  Total: ${result.data['total']:.2f}")
            print(f"  Time: {result.data['parseTime']:.2f}s")
        except Exception as e:
            print(f"  Error: {e}")

    # Test dialectic analysis
    print("\n[2] DIALECTIC ANALYSIS")
    problem = "Should a small business use a complex invoicing system or simple spreadsheets?"
    print(f"Problem: {problem}")
    try:
        result = hokage.analyze_dialectically(problem)
        print(f"  Analysis:\n{result.data.get('response', 'Error')[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
