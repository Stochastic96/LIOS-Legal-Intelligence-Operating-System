"""
training/fine_tuning/train.py
-------------------------------
Fine-tune a causal LM on the LIOS instruction-tuning dataset using
Hugging Face `transformers` + LoRA (PEFT).

This is a scaffold – fill in the model name and adjust hyperparameters.

Usage:
    python training/fine_tuning/train.py \
        --dataset training/datasets/instruction_tuning.jsonl \
        --model mistralai/Mistral-7B-Instruct-v0.2 \
        --output-dir training/fine_tuning/checkpoints
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer

app = typer.Typer()


@app.command()
def main(
    dataset: Path = typer.Argument(..., help="Instruction-tuning JSONL file"),
    model: str = typer.Option("mistralai/Mistral-7B-Instruct-v0.2", "--model", "-m"),
    output_dir: Path = typer.Option(
        Path("training/fine_tuning/checkpoints"), "--output-dir", "-o"
    ),
    num_epochs: int = typer.Option(3, "--epochs"),
    batch_size: int = typer.Option(4, "--batch-size"),
    lr: float = typer.Option(2e-4, "--lr"),
    lora_r: int = typer.Option(16, "--lora-r"),
    lora_alpha: int = typer.Option(32, "--lora-alpha"),
    max_seq_len: int = typer.Option(2048, "--max-seq-len"),
) -> None:
    """Fine-tune an LLM on the LIOS instruction-tuning dataset (LoRA)."""
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            DataCollatorForSeq2Seq,
            Trainer,
            TrainingArguments,
        )
    except ImportError as e:
        typer.echo(
            f"Missing dependency: {e}\n"
            "Install with: pip install torch transformers peft datasets",
            err=True,
        )
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Loading dataset from {dataset}…")
    raw_ds = load_dataset("json", data_files={"train": str(dataset)})["train"]

    typer.echo(f"Loading model {model}…")
    tokenizer = AutoTokenizer.from_pretrained(model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model_peft = get_peft_model(base_model, lora_config)
    model_peft.print_trainable_parameters()

    def _tokenise(example: dict) -> dict:
        text = (
            f"### Instruction:\n{example['instruction']}\n\n"
            f"### Input:\n{example['input']}\n\n"
            f"### Response:\n{example['output']}"
        )
        return tokenizer(text, truncation=True, max_length=max_seq_len, padding="max_length")

    tokenised = raw_ds.map(_tokenise, batched=False, remove_columns=raw_ds.column_names)
    tokenised = tokenised.train_test_split(test_size=0.05, seed=42)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=lr,
        fp16=torch.cuda.is_available(),
        save_strategy="epoch",
        evaluation_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model_peft,
        args=training_args,
        train_dataset=tokenised["train"],
        eval_dataset=tokenised["test"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
    )

    typer.echo("Starting training…")
    trainer.train()
    model_peft.save_pretrained(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))
    typer.echo(f"✓ Training complete. Model saved to {output_dir / 'final'}")


if __name__ == "__main__":
    app()
