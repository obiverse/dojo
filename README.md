# Dojo - Small Language Model Playground

**"Ninjas who can clone themselves"**

A playground for composing small language models into powerful systems.

## Philosophy

- **Composition over Scale**: Many small, sharp tools > one monolithic model
- **Unix Philosophy for AI**: Each ninja does ONE thing well
- **Dialectic Thinking**: Thesis → Antithesis → Synthesis
- **Scrolls**: Universal data primitive with lineage tracking

## Structure

```
dojo/
├── scroll.py      # Universal Scroll primitive (any type, with lineage)
├── ninja.py       # Ninja agents (small model wrappers)
├── hokage.py      # Orchestrator that commands ninjas
└── README.md
```

## Usage

```bash
# Run on Linux box with Ollama
python3 scroll.py      # Demo universal scrolls
python3 hokage.py      # Run the orchestrator
```

## Concepts

### Scroll
Inspired by micrograd's Value, but universal:
- Numbers add, multiply, backpropagate
- Strings concatenate
- Dicts merge
- Lists join
- Functions compose
- ALL track lineage

### Ninja
A small model wrapper that:
- Specializes in one task
- Can clone itself for parallel work
- Composes with other ninjas

### Hokage
The orchestrator that:
- Commands multiple ninjas
- Routes tasks to specialists
- Synthesizes results

## Hardware

Designed to run on modest hardware:
- RTX 4060 8GB or similar
- 32GB RAM
- Ollama with qwen2.5:1.5b (~400ms inference)
