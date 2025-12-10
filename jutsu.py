#!/usr/bin/env python3
"""
Jutsu - Ninja Techniques & Summoning

In Naruto, ninjas perform jutsu that can:
- Transform data (Transformation Jutsu)
- Clone themselves (Shadow Clone Jutsu)
- Summon other beings (Summoning Jutsu)
- Combine elements (Combination Jutsu)

This maps to our system:
- Jutsu = Prompt templates that produce specific effects
- Summoning = Factories that create specialized ninjas
- Shadow Clone = Parallel execution
- Scroll Contracts = 9S integration

"A ninja's true power is not in their strength,
 but in their ability to adapt and combine."
"""

import requests
import json
import time
import re
from typing import Any, Dict, List, Optional, Callable, Type
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from abc import ABC, abstractmethod

from scroll import Scroll, Meta


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JUTSU (Techniques)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Jutsu:
    """
    A ninja technique - a reusable prompt pattern.

    Like in Naruto, jutsu have:
    - Name (identity)
    - Hand signs (the prompt template)
    - Chakra cost (model complexity)
    - Effect (what it produces)
    """
    name: str
    template: str  # Prompt with {placeholders}
    description: str = ""
    chakra_type: str = "neutral"  # fire, water, earth, wind, lightning, neutral

    def weave(self, **kwargs) -> str:
        """Weave the jutsu - fill in the template."""
        return self.template.format(**kwargs)


# Standard Jutsu Library
JUTSU_LIBRARY = {
    # Parsing Jutsu (Earth style - solid structure)
    "parse_invoice": Jutsu(
        name="Invoice Parsing Jutsu",
        template='''Parse this invoice into JSON.
Schema: {{"client": "name", "lineItems": [{{"description": "what", "quantity": number, "rate": number}}]}}
Input: "{text}"
Output ONLY valid JSON:''',
        description="Extract structured invoice data",
        chakra_type="earth",
    ),

    "parse_contact": Jutsu(
        name="Contact Extraction Jutsu",
        template='''Extract contact info as JSON.
Schema: {{"name": "string", "email": "string|null", "phone": "string|null", "company": "string|null"}}
Input: "{text}"
Output ONLY valid JSON:''',
        description="Extract contact information",
        chakra_type="earth",
    ),

    # Writing Jutsu (Wind style - flowing text)
    "summarize": Jutsu(
        name="Condensation Jutsu",
        template='''Summarize in 1-2 sentences:
{text}

Summary:''',
        description="Condense text to essence",
        chakra_type="wind",
    ),

    "email_draft": Jutsu(
        name="Messenger Bird Jutsu",
        template='''Write a brief professional email.
To: {recipient}
Subject: {subject}
Key points: {points}

Email:''',
        description="Draft professional emails",
        chakra_type="wind",
    ),

    # Analysis Jutsu (Fire style - illuminating)
    "dialectic": Jutsu(
        name="Thesis-Antithesis-Synthesis Jutsu",
        template='''Analyze dialectically:
Problem: {problem}

THESIS (current state):
ANTITHESIS (what opposes it):
SYNTHESIS (higher unity):''',
        description="Dialectical analysis",
        chakra_type="fire",
    ),

    "critique": Jutsu(
        name="Critical Eye Jutsu",
        template='''Critique this briefly (strengths & weaknesses):
{content}

Critique:''',
        description="Balanced critique",
        chakra_type="fire",
    ),

    # Transformation Jutsu (Water style - adaptive)
    "translate": Jutsu(
        name="Universal Tongue Jutsu",
        template='''Translate to {language}:
{text}

Translation:''',
        description="Language translation",
        chakra_type="water",
    ),

    "rephrase": Jutsu(
        name="Mirror Reflection Jutsu",
        template='''Rephrase this in {style} style:
{text}

Rephrased:''',
        description="Rephrase in different styles",
        chakra_type="water",
    ),

    # Calculation Jutsu (Lightning style - precise)
    "calculate": Jutsu(
        name="Lightning Calculator Jutsu",
        template='''Calculate: {expression}
Return ONLY the number:''',
        description="Mathematical calculation",
        chakra_type="lightning",
    ),

    "estimate": Jutsu(
        name="Foresight Jutsu",
        template='''Estimate {what} based on: {context}
Give a single number with brief reasoning:''',
        description="Estimation with reasoning",
        chakra_type="lightning",
    ),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NINJA (Enhanced with Jutsu)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Ninja:
    """
    A ninja who can perform jutsu.

    Enhanced with:
    - Jutsu library (techniques they know)
    - Chakra affinity (what they're best at)
    - Shadow clone (parallel execution)
    - Summoning (create other ninjas)
    """

    def __init__(
        self,
        name: str,
        model: str = "qwen2.5:1.5b",
        system: str = "",
        jutsu: List[str] = None,  # Names of jutsu they know
        chakra_affinity: str = "neutral",
        ollama_url: str = "http://localhost:11434/api/generate",
    ):
        self.name = name
        self.model = model
        self.system = system
        self.jutsu_names = jutsu or []
        self.chakra_affinity = chakra_affinity
        self.ollama_url = ollama_url
        self.clone_count = 0
        self.jutsu_count = 0

    @property
    def jutsu(self) -> Dict[str, Jutsu]:
        """Get the jutsu this ninja knows."""
        return {name: JUTSU_LIBRARY[name] for name in self.jutsu_names if name in JUTSU_LIBRARY}

    def learn_jutsu(self, jutsu_name: str):
        """Learn a new jutsu."""
        if jutsu_name in JUTSU_LIBRARY and jutsu_name not in self.jutsu_names:
            self.jutsu_names.append(jutsu_name)

    def perform_jutsu(self, jutsu_name: str, **kwargs) -> Scroll:
        """Perform a jutsu - execute the technique."""
        if jutsu_name not in self.jutsu:
            return Scroll(
                f"/ninja/{self.name}/error",
                {"error": f"Unknown jutsu: {jutsu_name}"},
                Meta(schema="dojo/error"),
            )

        jutsu = self.jutsu[jutsu_name]
        prompt = jutsu.weave(**kwargs)
        return self._execute(prompt, jutsu.name)

    def _execute(self, prompt: str, jutsu_name: str = "raw") -> Scroll:
        """Execute a prompt against Ollama."""
        self.jutsu_count += 1
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

            return Scroll(
                f"/ninja/{self.name}/{jutsu_name.lower().replace(' ', '_')}_{self.jutsu_count}",
                {
                    "response": response,
                    "jutsu": jutsu_name,
                    "model": self.model,
                    "elapsed": elapsed,
                },
                Meta(schema="dojo/jutsu_result"),
            )
        except Exception as e:
            return Scroll(
                f"/ninja/{self.name}/error_{self.jutsu_count}",
                {"error": str(e), "jutsu": jutsu_name},
                Meta(schema="dojo/error"),
            )

    def shadow_clone(self, count: int = 1) -> List['Ninja']:
        """
        Shadow Clone Jutsu - create copies for parallel work.

        Each clone is independent but shares the same jutsu.
        """
        clones = []
        for i in range(count):
            self.clone_count += 1
            clone = Ninja(
                name=f"{self.name}_clone_{self.clone_count}",
                model=self.model,
                system=self.system,
                jutsu=self.jutsu_names.copy(),
                chakra_affinity=self.chakra_affinity,
                ollama_url=self.ollama_url,
            )
            clones.append(clone)
        return clones

    def __repr__(self) -> str:
        return f"Ninja({self.name}, jutsu={list(self.jutsu.keys())})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUMMONING CONTRACTS (Ninja Factories)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SummoningContract(ABC):
    """
    A summoning contract - a factory for creating specialized ninjas.

    Like in Naruto, you sign a contract with a scroll to summon beings.
    Each contract produces a specific type of ninja.
    """

    @abstractmethod
    def summon(self, ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
        """Summon a ninja of this type."""
        pass


class ParserContract(SummoningContract):
    """Summons parsing specialists."""

    def summon(self, ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
        return Ninja(
            name="Parser",
            model="qwen2.5:1.5b",
            system="You are a precise parser. Output ONLY valid JSON. No explanations.",
            jutsu=["parse_invoice", "parse_contact"],
            chakra_affinity="earth",
            ollama_url=ollama_url,
        )


class WriterContract(SummoningContract):
    """Summons writing specialists."""

    def summon(self, ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
        return Ninja(
            name="Writer",
            model="qwen2.5:1.5b",
            system="You are a concise writer. Be brief. No fluff.",
            jutsu=["summarize", "email_draft", "rephrase"],
            chakra_affinity="wind",
            ollama_url=ollama_url,
        )


class AnalystContract(SummoningContract):
    """Summons analytical thinkers."""

    def summon(self, ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
        return Ninja(
            name="Analyst",
            model="qwen2.5:1.5b",
            system="You are a dialectical thinker. Analyze deeply but concisely.",
            jutsu=["dialectic", "critique"],
            chakra_affinity="fire",
            ollama_url=ollama_url,
        )


class TranslatorContract(SummoningContract):
    """Summons language specialists."""

    def summon(self, ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
        return Ninja(
            name="Translator",
            model="qwen2.5:1.5b",
            system="You are a polyglot translator. Preserve meaning and tone.",
            jutsu=["translate", "rephrase"],
            chakra_affinity="water",
            ollama_url=ollama_url,
        )


class CalculatorContract(SummoningContract):
    """Summons calculation specialists."""

    def summon(self, ollama_url: str = "http://localhost:11434/api/generate") -> Ninja:
        return Ninja(
            name="Calculator",
            model="qwen2.5:1.5b",
            system="You are a precise calculator. Return only numbers.",
            jutsu=["calculate", "estimate"],
            chakra_affinity="lightning",
            ollama_url=ollama_url,
        )


# Registry of all contracts
SUMMONING_CONTRACTS = {
    "parser": ParserContract(),
    "writer": WriterContract(),
    "analyst": AnalystContract(),
    "translator": TranslatorContract(),
    "calculator": CalculatorContract(),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HOKAGE (Enhanced Orchestrator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Hokage:
    """
    The village leader who commands ninjas.

    Can:
    - Summon ninjas via contracts
    - Dispatch jutsu to appropriate ninjas
    - Coordinate shadow clone armies
    - Combine jutsu for complex tasks
    """

    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate"):
        self.ollama_url = ollama_url
        self.ninjas: Dict[str, Ninja] = {}
        self.mission_count = 0

        # Summon initial team
        for contract_name, contract in SUMMONING_CONTRACTS.items():
            ninja = contract.summon(ollama_url)
            self.ninjas[ninja.name.lower()] = ninja

    def summon(self, contract_name: str) -> Optional[Ninja]:
        """Summon a ninja using a contract."""
        contract = SUMMONING_CONTRACTS.get(contract_name)
        if contract:
            ninja = contract.summon(self.ollama_url)
            self.ninjas[ninja.name.lower()] = ninja
            return ninja
        return None

    def dispatch(self, ninja_name: str, jutsu_name: str, **kwargs) -> Scroll:
        """Dispatch a ninja to perform a jutsu."""
        ninja = self.ninjas.get(ninja_name.lower())
        if not ninja:
            return Scroll("/hokage/error", {"error": f"Unknown ninja: {ninja_name}"}, Meta(schema="dojo/error"))
        return ninja.perform_jutsu(jutsu_name, **kwargs)

    def shadow_clone_army(self, ninja_name: str, tasks: List[Dict], jutsu_name: str) -> List[Scroll]:
        """
        Shadow Clone Jutsu at scale - parallel execution.

        Creates clones and dispatches them to process tasks in parallel.
        """
        ninja = self.ninjas.get(ninja_name.lower())
        if not ninja:
            return [Scroll("/hokage/error", {"error": f"Unknown ninja: {ninja_name}"}, Meta(schema="dojo/error"))]

        # Create clones
        clones = ninja.shadow_clone(len(tasks))

        results = []
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {}
            for clone, task in zip(clones, tasks):
                future = executor.submit(clone.perform_jutsu, jutsu_name, **task)
                futures[future] = task

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(Scroll(
                        "/hokage/clone_error",
                        {"error": str(e), "task": futures[future]},
                        Meta(schema="dojo/error"),
                    ))

        return results

    def combination_jutsu(self, steps: List[Dict]) -> Scroll:
        """
        Combination Jutsu - chain multiple jutsu together.

        Each step feeds into the next.
        """
        self.mission_count += 1
        results = []
        context = {}

        for step in steps:
            ninja_name = step.get("ninja")
            jutsu_name = step.get("jutsu")
            kwargs = {**context, **step.get("kwargs", {})}

            result = self.dispatch(ninja_name, jutsu_name, **kwargs)
            results.append(result)

            # Extract data for next step
            if result.data.get("response"):
                context["previous"] = result.data["response"]

        return Scroll(
            f"/hokage/combination_{self.mission_count}",
            {
                "steps": len(steps),
                "results": [r.to_dict() for r in results],
                "final": results[-1].data if results else None,
            },
            Meta(schema="dojo/combination_result"),
        )

    def __repr__(self) -> str:
        return f"Hokage(ninjas={list(self.ninjas.keys())})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEMO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def demo():
    print("=" * 60)
    print("JUTSU & SUMMONING - Naruto-Inspired AI Composition")
    print("=" * 60)

    # Create Hokage
    hokage = Hokage()
    print(f"\nHokage: {hokage}")
    print(f"Available ninjas: {list(hokage.ninjas.keys())}")

    # Show jutsu library
    print("\n[JUTSU LIBRARY]")
    for name, jutsu in JUTSU_LIBRARY.items():
        print(f"  {jutsu.chakra_type.upper():10} | {name}: {jutsu.description}")

    # Test single jutsu
    print("\n[1] SINGLE JUTSU - Invoice Parsing")
    result = hokage.dispatch("parser", "parse_invoice", text="3 hours consulting for Acme at $150/hr")
    print(f"  Result: {result.data.get('response', 'Error')[:200]}")
    print(f"  Time: {result.data.get('elapsed', 0):.2f}s")

    # Test shadow clone army
    print("\n[2] SHADOW CLONE ARMY - Parallel Parsing")
    tasks = [
        {"text": "5 hours design for TechCo at $100/hr"},
        {"text": "Monthly retainer $2000 for Jane"},
        {"text": "10 pages website at $500/page for StartupX"},
    ]
    results = hokage.shadow_clone_army("parser", tasks, "parse_invoice")
    for r in results:
        print(f"  Clone result: {r.data.get('response', 'Error')[:100]}...")

    # Test dialectic
    print("\n[3] DIALECTIC JUTSU")
    result = hokage.dispatch("analyst", "dialectic", problem="Should AI replace human decision making?")
    print(f"  Analysis:\n{result.data.get('response', 'Error')[:400]}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
