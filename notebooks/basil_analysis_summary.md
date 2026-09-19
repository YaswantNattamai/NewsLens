# BASIL Dataset — EDA Summary

- **100 events**, **300 articles**, balanced triplets of Fox News / HuffPost / New York Times.
- **1726 human bias annotations** (mean 5.8 per article).
- Bias is mostly **informational** (72%) rather than lexical (28%) — about *what* is reported, not only word choice.
- Biased language skews strongly **negative** (82% vs 18% positive) — a class imbalance for any bias classifier.
- Bias is overwhelmingly **direct** (88%), aimed at a named target.
- **42%** of biased spans sit inside quotations; the rest are the reporter's own voice.
- Annotation **density** per 1,000 words: Fox News 11.4, HuffPost 9.7, New York Times 10.4.
- Coverage spans **2010–2019**; a handful of events use uppercase source names (normalised on load).

**Why it matters for NewsLens:** BASIL's human spans are the ground truth the project validates its framing metric against; the dominance of informational + direct bias justifies the entity-, omission-, and framing-centred design, and the negative-class imbalance is why the bias classifier is selected by F1 rather than accuracy.