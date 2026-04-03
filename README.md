# Prompt Engineering Playground

An interactive terminal app for experimenting with LLM prompt techniques. Change system prompts, temperature, and few-shot examples from a config file, no code edits needed. Built with Groq's inference API and LLaMA 3.3 70B.

---

## What it does

Four experiment modes that isolate the core levers of LLM behavior:

> 1. Mode 1 — Free chat: Test different system prompt personas side by side
> 2. Mode 2 — A/B comparison: Run two different system prompts against the same message and compare outputs in split panels
> 3. Mode 3 — Few-shot prompting: Give the model input→output examples and watch it pattern match
> 4. Mode 4 — Temperature sweep: Run the same prompt at 0.0, 0.5, and 1.0 simultaneously to feel the difference

Everything is configured from `config.json` — swap prompts, examples, and parameters without touching Python.

---

## How it works

Every mode sends a structured `messages` array to the Groq API. The difference between modes is purely in how that array is constructed:

```
Free chat:
  [system: persona] + [conversation history]

A/B test:
  [system: prompt_a] + [user message]   ← call 1
  [system: prompt_b] + [user message]   ← call 2 (same message, different system)

Few-shot:
  [system: persona]
  [user: example 1] [assistant: label 1]
  [user: example 2] [assistant: label 2]
  [user: example 3] [assistant: label 3]
  [user: actual question]               ← model pattern matches from above

Temperature sweep:
  Same messages array × 3 API calls
  Each call identical except temperature: 0.0 / 0.5 / 1.0
```

The model is stateless — it has no memory between calls. All context, persona, and examples are rebuilt and resent on every single request.

---

## Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM Provider | [Groq](https://groq.com) (free tier) |
| Model | LLaMA 3.3 70B Versatile |
| Terminal UI | Rich |
| Config | JSON + python-dotenv |

---

## Setup

1. Clone the repo
2. Create and activate a virtual environment
3. Install dependencies: pip install groq python-dotenv rich
4. Get a Groq API key
5. Create your `.env` file
6. Configure `config.json`

---

## Experiments and what they reveal

Mode 1 — Persona control

Set `system_prompt_a` to a specific persona and ask an opinionated question:

```json
"system_prompt_a": "You are a brutally honest senior engineer with 20 years
of experience. You do not sugarcoat feedback. Tell people exactly what is
wrong with their code or ideas."
```

Test input:
```
I want to build my own blockchain to store user passwords securely
```

The default helpful assistant gently suggests alternatives. The brutal engineer dismantles the idea immediately. Same model, same knowledge, completely different communication style. The system prompt is the only difference.

---

Mode 2 — A/B prompt comparison

Best config for showing format vs tone differences:

```json
"system_prompt_a": "You are a helpful assistant. Be thorough and detailed.",
"system_prompt_b": "You are a cynical tech veteran. Answer with skepticism and point out what could go wrong."
```

Test input:
```
Should I use Python or JavaScript for my first project
```

Prompt A gives an encouraging balanced answer. Prompt B leads with risk and caveats. The content overlaps but the framing is completely different — this is how product teams test prompt variants before deploying to users.

---

Mode 3 — Few-shot pattern matching

With the sentiment classification config, these inputs reveal the boundaries of the pattern:

| Input | Expected | What actually happens |
|---|---|---|
| `'Worst purchase I have ever made'` | Negative | Clean single word — pattern matches perfectly |
| `'Expensive but worth every penny'` | Positive | Clean — strong signal overrides the "expensive" |
| `'My dog loves it even if I dont'` | Mixed | Invents a new category not in your examples |
| `'Great design but terrible battery'` | Mixed | Same — model reasons beyond the pattern |
| `What is the capital of France` | — | Ignores pattern entirely, answers normally |

The key insight: few-shot examples guide behavior but don't lock it. The model falls back to general knowledge when inputs don't fit the pattern. In production you'd add explicit system prompt rules on top: `"Only ever respond with Positive, Negative, or Neutral. Nothing else."` — combining both is far more reliable than either alone.

---

Mode 4 — Temperature sweep

| Temperature | Behavior | Best used for |
|---|---|---|
| 0.0 | Deterministic — same answer every run | Facts, code, data extraction |
| 0.5 | Balanced — slight variation, stays coherent | General conversation, summaries |
| 1.0 | High variance — creative, sometimes unexpected | Brainstorming, creative writing |

Critical finding: running `What is the capital of France` at temperature 1.0 occasionally produces wrong answers with full confidence.

---

## Key concepts demonstrated

1. System prompts: define the model's persona, rules, and constraints. Small wording changes produce dramatically different outputs. Vague instructions like "be concise" are interpreted loosely, specific constraints like "reply in exactly one sentence" are far more reliable.
2. Few-shot prompting: shows the model input→output examples before the actual question. Instead of explaining what you want, you demonstrate it. Three clean examples are often more effective than a paragraph of instructions for structured tasks like classification or extraction.
3. Temperature: controls output randomness. It is not a quality dial, high temperature is better for creative tasks, low temperature is better for factual ones. Using the wrong temperature for the task is one of the most common mistakes in production LLM applications.
4. A/B testing: is how prompt engineers actually work, run two prompt variants against the same inputs and compare outputs systematically before deciding which to ship. This playground makes that workflow interactive.
5. Stateless API: every API call is independent. The model has zero memory between requests. All context, history, persona, and examples are rebuilt and resent on every call. "Memory" is just a Python list you maintain and pass in yourself.

---

## Limitations

- Few-shot examples work well for clear cut cases but break on edge cases and off-topic inputs
- System prompt instructions can be overridden by sufficiently strong user messages. This is called prompt injection and is a real security concern in production
- Temperature affects creativity but not factual accuracy. A model at temperature 0 can still hallucinate, just consistently
