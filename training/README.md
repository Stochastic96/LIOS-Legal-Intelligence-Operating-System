# Training Infrastructure

This directory contains everything needed to train, fine-tune, and evaluate LIOS models.

## Directory Structure

```
training/
├── datasets/            # Raw Q&A pairs and processed instruction-tuning files
│   ├── raw_qa.jsonl     # (you populate this) raw question-answer pairs
│   └── benchmark.jsonl  # Gold-standard evaluation set
├── fine_tuning/
│   ├── prepare_dataset.py  # Convert raw Q&A → instruction-tuning JSONL
│   └── train.py            # LoRA fine-tuning with Hugging Face + PEFT
└── evaluation/
    ├── benchmark.py         # Run full eval against gold-standard set
    └── metrics.py           # ROUGE, citation precision, etc.
```

## Quick Start

### 1. Prepare your dataset

Create `training/datasets/raw_qa.jsonl` with entries like:
```json
{"question": "Does CSRD apply to a company with 300 employees?", "answer": "Yes. CSRD Art. 3 covers undertakings exceeding 250 employees ...", "regulation": "CSRD", "article_ref": "Art. 3"}
```

Then run:
```bash
python training/fine_tuning/prepare_dataset.py \
    training/datasets/raw_qa.jsonl \
    --output training/datasets/instruction_tuning.jsonl
```

### 2. Fine-tune

```bash
# Requires GPU + ~14GB VRAM for Mistral-7B with LoRA
python training/fine_tuning/train.py \
    training/datasets/instruction_tuning.jsonl \
    --model mistralai/Mistral-7B-Instruct-v0.2 \
    --epochs 3
```

Checkpoints land in `training/fine_tuning/checkpoints/`.

### 3. Evaluate

Create `training/datasets/benchmark.jsonl`:
```json
{"query": "What is the CSRD employee threshold?", "expected_answer": "250 employees (Art. 3 CSRD)."}
```

Then:
```bash
python training/evaluation/benchmark.py training/datasets/benchmark.jsonl
```

Results saved to `training/evaluation/results.json`.

## Data Sources

- EUR-Lex (free, open): https://eur-lex.europa.eu
- Use `scripts/ingest_regulations.py` to auto-fetch and build your dataset
- Supplement with manually verified Q&A pairs from legal professionals

## Future Scope (see docs/future_scope.md)

- Retrieval-Augmented Generation (RAG) fine-tuning
- Reinforcement Learning from Human Feedback (RLHF) with legal expert feedback
- Automated dataset expansion via LLM self-play
