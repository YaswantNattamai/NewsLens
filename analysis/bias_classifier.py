"""
Bias classifier — section 6.7. The one model in this project that's actually
trained, not used off the shelf, because it's the one place labeled data
(BASIL's bias spans) and a real research question (RQ2) both exist.

This module is the reusable core logic (labeling, article-level split,
train/evaluate for one checkpoint). It's deliberately backend-agnostic about
*where* it runs — see `newslens_bias_classifier_kaggle.ipynb` for a
self-contained notebook version of the same logic wired up for Kaggle's
GPU + dataset-mount environment, and `run_bias_classifier_comparison()`
at the bottom for running it locally/on Colab.

LABELING METHOD — read this before trusting results:
BASIL's bias-span annotations carry character offsets (`start`/`end`) in
`ingestion/basil_loader.BiasSpan`, but those offsets are relative to
BASIL's own raw-text representation, which may not survive paragraph-joining
exactly (see the offset caveat already flagged in basil_loader.py). Rather
than trust offset arithmetic that depends on an unverified file format,
this module labels a sentence as biased (1) if the *text* of any annotated
bias span is a substring of that sentence, case-insensitive. This is more
robust to formatting drift, at the cost of occasionally matching a short
span's text in the wrong sentence if the same phrase repeats verbatim
elsewhere in the article — rare enough in practice not to matter, but note
it if you're auditing labels closely.
"""
import time
from dataclasses import dataclass

import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, f1_score

from ingestion.basil_loader import BasilArticle
from preprocessing.clean import to_sentences

CHECKPOINTS = ["bert-base-uncased", "roberta-base", "distilbert-base-uncased"]


@dataclass
class LabeledSentence:
    event_id: str
    source: str
    article_key: str   # unique per article, used as the split-group key
    sentence: str
    label: int          # 1 = overlaps an annotated bias span, 0 = not


def label_article(article: BasilArticle) -> list[LabeledSentence]:
    sentences = to_sentences(article.raw_text)
    span_texts = [s.text.strip().lower() for s in article.bias_spans if s.text.strip()]
    article_key = f"{article.event_id}:{article.source}"

    rows = []
    for sent in sentences:
        sent_lower = sent.lower()
        label = int(any(span_text in sent_lower for span_text in span_texts))
        rows.append(LabeledSentence(
            event_id=article.event_id,
            source=article.source,
            article_key=article_key,
            sentence=sent,
            label=label,
        ))
    return rows


def build_labeled_dataset(events: dict[str, list[BasilArticle]]) -> list[LabeledSentence]:
    """events: {event_id: [BasilArticle, ...]} — typically the output of basil_loader.load_all_events()."""
    rows = []
    for articles in events.values():
        for article in articles:
            rows.extend(label_article(article))
    return rows


def split_by_article(
    rows: list[LabeledSentence], test_size: float = 0.2, seed: int = 42
) -> tuple[list[LabeledSentence], list[LabeledSentence]]:
    """
    Split by ARTICLE, not by sentence. Sentences from the same article are
    too similar to each other (shared topic, shared author voice) —
    splitting by sentence leaks information between train and test and
    inflates reported accuracy.
    """
    groups = [r.article_key for r in rows]
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(rows, groups=groups))
    train_rows = [rows[i] for i in train_idx]
    test_rows = [rows[i] for i in test_idx]
    return train_rows, test_rows


def class_balance(rows: list[LabeledSentence]) -> dict:
    labels = [r.label for r in rows]
    n = len(labels)
    return {"n": n, "positive": sum(labels), "positive_frac": sum(labels) / n if n else 0.0}


# --------------------------------------------------------------------------
# Training + evaluation for one checkpoint. Requires transformers/torch —
# imported lazily so importing this module for labeling alone (e.g. to
# inspect class balance) doesn't require a GPU environment.
# --------------------------------------------------------------------------

def train_and_evaluate(
    checkpoint: str,
    train_rows: list[LabeledSentence],
    test_rows: list[LabeledSentence],
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 16,
    lr: float = 2e-5,
) -> dict:
    import torch
    from datasets import Dataset
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        TrainingArguments, Trainer,
    )

    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint, num_labels=2)

    def to_hf_dataset(rows: list[LabeledSentence]) -> Dataset:
        return Dataset.from_dict({
            "text": [r.sentence for r in rows],
            "label": [r.label for r in rows],
        })

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=128)

    train_ds = to_hf_dataset(train_rows).map(tokenize, batched=True)
    test_ds = to_hf_dataset(test_rows).map(tokenize, batched=True)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "accuracy": accuracy_score(labels, preds),
            "f1": f1_score(labels, preds, zero_division=0),
        }

    args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        eval_strategy="epoch",
        save_strategy="no",          # keep disk usage down during the sweep; save the winner separately
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    eval_metrics = trainer.evaluate()

    # Inference time measured separately from Trainer.evaluate(), which
    # includes loss computation overhead not representative of deployed use.
    model.eval()
    device = next(model.parameters()).device
    sample = test_rows[: min(50, len(test_rows))]
    inputs = tokenizer(
        [r.sentence for r in sample], truncation=True, padding=True, max_length=128, return_tensors="pt"
    ).to(device)
    with torch.no_grad():
        start = time.perf_counter()
        model(**inputs)
        elapsed = time.perf_counter() - start
    inference_ms_per_sentence = (elapsed / len(sample)) * 1000

    return {
        "checkpoint": checkpoint,
        "accuracy": eval_metrics["eval_accuracy"],
        "f1": eval_metrics["eval_f1"],
        "inference_ms_per_sentence": inference_ms_per_sentence,
        "train_n": len(train_rows),
        "test_n": len(test_rows),
    }, model, tokenizer



# --------------------------------------------------------------------------
# Inference — loading and using a checkpoint you've already fine-tuned
# (e.g. downloaded from the Kaggle notebook's Output tab). Training
# (above) and inference (below) are deliberately separate: nothing in this
# file runs training automatically, and nothing in the pipeline requires a
# fine-tuned model to be present — see analysis/pipeline.py, which calls
# `predict_bias` only if a model directory is configured and exists.
# --------------------------------------------------------------------------

_loaded_models: dict = {}  # model_dir -> (tokenizer, model), so repeated calls don't reload from disk


def load_classifier(model_dir: str):
    """
    Loads a fine-tuned checkpoint saved via `model.save_pretrained(...)` —
    matches what both `train_and_evaluate` above and the Kaggle notebook
    write to their `final/` folders. Raises FileNotFoundError early with a
    clear message if the directory doesn't look like a saved checkpoint,
    rather than letting a cryptic HF error surface later.
    """
    import os
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    if model_dir in _loaded_models:
        return _loaded_models[model_dir]

    if not os.path.isdir(model_dir):
        raise FileNotFoundError(
            f"BIAS_MODEL_DIR '{model_dir}' does not exist. Download a checkpoint's "
            f"`final/` folder from the Kaggle notebook's Output tab and point "
            f"BIAS_MODEL_DIR at it (see README section 10)."
        )

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    _loaded_models[model_dir] = (tokenizer, model)
    return tokenizer, model


def predict_bias(sentences: list[str], model_dir: str, batch_size: int = 16) -> list[dict]:
    """
    Returns [{sentence, biased, probability}, ...] — `probability` is the
    model's confidence in whichever class it predicted (not necessarily
    P(biased)), matching how a UI would want to display "how sure was it."
    Runs fine on CPU at this scale (per-event sentence counts are small);
    no GPU required for inference, only for the Kaggle training step.
    """
    import torch

    if not sentences:
        return []

    tokenizer, model = load_classifier(model_dir)
    device = next(model.parameters()).device
    results = []

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        inputs = tokenizer(batch, truncation=True, padding=True, max_length=128, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)

        for sent, pred, prob_row in zip(batch, preds, probs):
            results.append({
                "sentence": sent,
                "biased": bool(pred.item() == 1),
                "probability": float(prob_row[pred].item()),
            })

    return results


def run_bias_classifier_comparison(
    events: dict[str, list[BasilArticle]],
    output_root: str = "./bias_classifier_runs",
    checkpoints: list[str] = CHECKPOINTS,
) -> list[dict]:
    """Runs the full RQ2 comparison locally/on Colab and returns the results table."""
    rows = build_labeled_dataset(events)
    train_rows, test_rows = split_by_article(rows)
    print("Train:", class_balance(train_rows))
    print("Test: ", class_balance(test_rows))

    results = []
    for checkpoint in checkpoints:
        print(f"\n=== Training {checkpoint} ===")
        metrics, model, tokenizer = train_and_evaluate(
            checkpoint, train_rows, test_rows, output_dir=f"{output_root}/{checkpoint}"
        )
        results.append(metrics)
        model.save_pretrained(f"{output_root}/{checkpoint}/final")
        tokenizer.save_pretrained(f"{output_root}/{checkpoint}/final")
        del model
        import torch
        torch.cuda.empty_cache()

    return results
