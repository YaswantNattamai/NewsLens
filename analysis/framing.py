"""
Framing score — section 6.5.

Naively pairing "first sentence mentioning X in article A" with "first
sentence mentioning X in article B" measures topic mismatch, not framing.
Instead: embed every sentence, align each to its most similar counterpart
in the other article, and only keep alignments above a similarity floor.

IMPORTANT interpretation note (carried over from the spec, don't drop this
when you write the report): because this matches each sentence to its
single most-similar counterpart, the score is a LOWER BOUND on framing
divergence, not an unbiased average. Read it as "how different are these
two sources even in their most similar description of this," not as a
complete measure of overall framing difference. Calibrate `threshold` and
validate against BASIL's human bias-span labels (section 7) before treating
the number as meaningful on its own.
"""
import numpy as np
from sentence_transformers import SentenceTransformer, util

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def align_and_score(
    sentences_a: list[str], sentences_b: list[str], threshold: float = 0.5
) -> dict | None:
    """
    Returns None if there's nothing comparable (empty article, or no aligned
    pair clears the similarity floor) — never silently returns 0, since 0
    would misleadingly read as "identical framing."

    Otherwise returns:
        {
          "score": float,              # mean (1 - similarity) over kept alignments — HIGHER = more divergent framing
          "aligned_pairs": [
              {"sentence_a": ..., "sentence_b": ..., "similarity": float},
              ...
          ],
        }
    """
    if not sentences_a or not sentences_b:
        return None

    model = get_model()
    emb_a = model.encode(sentences_a)
    emb_b = model.encode(sentences_b)
    sim_matrix = util.cos_sim(emb_a, emb_b).numpy()

    scores = []
    pairs = []
    for i in range(len(sentences_a)):
        j = int(np.argmax(sim_matrix[i]))
        best_sim = float(sim_matrix[i, j])
        if best_sim >= threshold:
            scores.append(1 - best_sim)
            pairs.append({
                "sentence_a": sentences_a[i],
                "sentence_b": sentences_b[j],
                "similarity": best_sim,
            })

    if not scores:
        return None

    return {
        "score": sum(scores) / len(scores),
        "aligned_pairs": sorted(pairs, key=lambda p: p["similarity"]),  # most-divergent first, for the UI
    }
