#!/usr/bin/env python3
"""
Ninja - Small Model Agents

Each ninja is a specialized small model that:
- Does ONE thing well
- Can clone itself for parallel execution
- Composes with other ninjas
- Tracks its own lineage (what it learned)

"The sharp edge of a single ninja can cut
 what the blunt force of giants cannot."
"""

import requests
import json
import time
import re
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from scroll import Scroll

OLLAMA_URL = "http://localhost:11434/api/generate"


@dataclass
class NinjaResult:
    """Result of a ninja's work."""
    data: Any
    raw: str
    model: str
    elapsed: float
    success: bool = True
    error: Optional[str] = None


class Ninja:
    """
    A small model agent specialized for one task.

    The ninja wraps a small LLM and:
    - Has a system prompt (its training/specialty)
    - Has skills (prompt templates for specific tasks)
    - Can clone itself (for parallel work)
    - Tracks its lineage (history of calls)
    """

    def __init__(
        self,
        name: str,
        model: str = "qwen2.5:1.5b",
        system: str = "",
        skills: Dict[str, str] = None,
    ):
        self.name = name
        self.model = model
        self.system = system
        self.skills = skills or {}
        self.lineage: List[Dict] = []  # History of calls

    def call(self, prompt: str, **kwargs) -> NinjaResult:
        """
        Execute a raw prompt.

        The ninja calls Ollama and tracks the result.
        """
        start = time.time()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if self.system:
            payload["system"] = self.system

        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=60)
            r.raise_for_status()
            response = r.json()["response"]
            elapsed = time.time() - start

            # Track lineage
            self.lineage.append({
                "time": time.time(),
                "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                "response": response[:100] + "..." if len(response) > 100 else response,
                "elapsed": elapsed,
            })

            return NinjaResult(
                data=response,
                raw=response,
                model=self.model,
                elapsed=elapsed,
            )

        except Exception as e:
            elapsed = time.time() - start
            return NinjaResult(
                data=None,
                raw="",
                model=self.model,
                elapsed=elapsed,
                success=False,
                error=str(e),
            )

    def use_skill(self, skill_name: str, **kwargs) -> NinjaResult:
        """
        Use a predefined skill (prompt template).

        Skills are prompt templates with {placeholders}.
        """
        if skill_name not in self.skills:
            return NinjaResult(
                data=None,
                raw="",
                model=self.model,
                elapsed=0,
                success=False,
                error=f"Unknown skill: {skill_name}",
            )

        template = self.skills[skill_name]
        prompt = template.format(**kwargs)
        return self.call(prompt)

    def clone(self, name_suffix: str = "_clone") -> 'Ninja':
        """
        Clone this ninja for parallel work.

        The clone has the same skills but fresh lineage.
        """
        return Ninja(
            name=self.name + name_suffix,
            model=self.model,
            system=self.system,
            skills=self.skills.copy(),
        )

    def as_scroll(self) -> Scroll:
        """Convert ninja's lineage to a Scroll for composition."""
        return Scroll(self.lineage, _op=f"ninja:{self.name}")

    def __repr__(self) -> str:
        return f"Ninja({self.name}, model={self.model}, skills={list(self.skills.keys())})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPECIALIZED NINJAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_parser_ninja() -> Ninja:
    """Create a ninja specialized in parsing text to JSON."""
    return Ninja(
        name="Parser",
        model="qwen2.5:1.5b",
        system="""You are a precise parser. Extract structured data from text.
Output ONLY valid JSON. No explanations, no markdown, just JSON.""",
        skills={
            "invoice": """Parse this invoice description into JSON.
Schema: {{"client": "name", "lineItems": [{{"description": "what", "quantity": number, "rate": number}}], "total": number}}

Input: "{text}"
Output:""",
            "contact": """Extract contact info from this text.
Schema: {{"name": "string", "email": "string or null", "phone": "string or null", "company": "string or null"}}

Input: "{text}"
Output:""",
        },
    )


def create_calculator_ninja() -> Ninja:
    """Create a ninja specialized in calculations."""
    return Ninja(
        name="Calculator",
        model="qwen2.5:1.5b",
        system="""You are a precise calculator. Do math and return only numbers.
No explanations. Just the final number.""",
        skills={
            "total": """Calculate the total from these line items:
{items}

Return ONLY the total number:""",
            "tax": """Calculate {rate}% tax on {amount}.
Return ONLY the tax amount:""",
        },
    )


def create_writer_ninja() -> Ninja:
    """Create a ninja specialized in writing text."""
    return Ninja(
        name="Writer",
        model="qwen2.5:1.5b",
        system="""You are a concise writer. Write clear, professional text.
Be brief. No fluff.""",
        skills={
            "summary": """Summarize this in 1-2 sentences:
{text}

Summary:""",
            "email": """Write a brief professional email about:
{topic}

To: {recipient}

Email:""",
        },
    )


def create_dialectic_ninja() -> Ninja:
    """Create a ninja that thinks dialectically."""
    return Ninja(
        name="Dialectic",
        model="qwen2.5:1.5b",
        system="""You are a dialectical thinker.
For every problem, identify:
1. THESIS: The current state or obvious solution
2. ANTITHESIS: What opposes or contradicts it
3. SYNTHESIS: A higher unity that transcends both

Be concise. No fluff.""",
        skills={
            "analyze": """Apply dialectical analysis to this problem:
{problem}

THESIS:
ANTITHESIS:
SYNTHESIS:""",
        },
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def demo():
    print("=" * 60)
    print("NINJA AGENTS - Specialized Small Model Wrappers")
    print("=" * 60)

    # Create ninjas
    parser = create_parser_ninja()
    writer = create_writer_ninja()

    print(f"\nCreated: {parser}")
    print(f"Created: {writer}")

    # Test parser
    print("\n[1] PARSER NINJA - Invoice parsing")
    result = parser.use_skill("invoice", text="3 hours consulting for Acme at $150/hr")
    print(f"  Result: {result.data}")
    print(f"  Time: {result.elapsed:.2f}s")

    # Test writer
    print("\n[2] WRITER NINJA - Summarization")
    result = writer.use_skill("summary", text="The quick brown fox jumps over the lazy dog. This is a common pangram used to test fonts and keyboards because it contains all letters of the alphabet.")
    print(f"  Result: {result.data}")
    print(f"  Time: {result.elapsed:.2f}s")

    # Test cloning
    print("\n[3] CLONING - Create parallel workers")
    parser_clone = parser.clone("_2")
    print(f"  Original: {parser}")
    print(f"  Clone: {parser_clone}")

    # Test lineage
    print("\n[4] LINEAGE - Track history")
    print(f"  Parser lineage: {len(parser.lineage)} calls")
    for entry in parser.lineage:
        print(f"    - {entry['elapsed']:.2f}s: {entry['prompt'][:50]}...")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
