# NewsLens — Presentation Study Guide

A concept-by-concept primer on every technology, NLP technique, and ML idea used in this project. Organized so you can explain *what it is*, *why we used it here*, and *how it fits the pipeline* — the three things a teacher/audience will probe.

---

## How to use this guide

For each concept below there are three parts:
1. **What it is** — the general idea, in plain language.
2. **Where we use it** — the specific feature in NewsLens it powers.
3. **Likely question + good answer** — anticipate what gets asked.

Read top to bottom once, then use Section 10 (Quick Q&A Bank) the night before as a refresher.

---

## 1. Natural Language Processing (NLP) — the umbrella field

**What it is:** NLP is the branch of AI concerned with getting computers to understand, process, and generate human language — text or speech. It sits at the intersection of linguistics and machine learning.

**Where we use it:** Every analytical feature in NewsLens (entity extraction, sentiment, framing, omission, clustering, bias detection) is an NLP task applied to news articles.

**Likely question:** *"Why is this an NLP project and not just data analysis?"*
**Good answer:** Because the core objects being processed — sentences, entity names, phrasing — are unstructured natural language, not numbers in a spreadsheet. Every technique we used (entity recognition, embeddings, sentiment classifiers, transformers) exists specifically to turn unstructured text into something comparable and measurable.

---

## 2. Named Entity Recognition (NER)

**What it is:** A model that scans text and labels spans of words as belonging to predefined categories — most commonly people (PERSON), organizations (ORG), and locations/geopolitical entities (GPE). It's typically done with a trained sequence-labeling model that has learned patterns of capitalization, context words, and grammar that signal "this is a name."

**Where we use it:** To extract every person, organization, and place mentioned in each article, as the foundation for entity-level comparisons across outlets (who gets mentioned, how often, with what sentiment).

**Likely question:** *"How does the model know 'Modi' is a person and not just a random word?"*
**Good answer:** The NER model was pretrained on large amounts of labeled text and learned statistical patterns — capitalization, surrounding words like "President" or "said," sentence position — that correlate with entity types. It doesn't "know" facts about the world; it recognizes linguistic patterns.

---

## 3. Entity Resolution / Canonicalization (Fuzzy Matching)

**What it is:** The problem of deciding whether two different text strings refer to the same real-world thing. "Trump," "Donald Trump," and "President Trump" are three different strings but one entity. **Fuzzy string matching** measures how similar two strings are (e.g., by comparing token overlap and character-level similarity) and merges strings above a similarity threshold.

**Where we use it:** After NER extracts raw entity mentions from every source, we merge same-entity mentions across all outlets in an event *before* counting/scoring, so comparisons are accurate. We also add a special rule for people's names: if one name's words are a subset of another's (e.g., "Modi" ⊆ "Narendra Modi"), they're merged even if the general fuzzy score alone wouldn't catch it.

**Likely question:** *"Why not just match exact strings?"*
**Good answer:** Exact string matching would treat "Trump" and "Donald Trump" as two unrelated entities, splitting one person's mentions across two rows — this would silently corrupt every downstream count, sentiment score, and omission calculation. Fuzzy matching accounts for how real writers actually vary names across sentences and outlets.

---

## 4. Sentiment Analysis

**What it is:** Classifying a piece of text as expressing positive, negative, or neutral sentiment, usually with a confidence score attached. Modern sentiment models are trained on large labeled datasets (e.g., social media posts or reviews) using deep learning.

**Where we use it:** To score how positively or negatively each outlet's language treats a specific entity — not the article's overall tone, but the tone specifically around mentions of, say, a particular politician or organization.

**Likely question:** *"Isn't sentiment just about single words like 'good' or 'bad'?"*
**Good answer:** No — modern sentiment models consider context, not just keyword lookup. The same word can carry different sentiment depending on surrounding grammar and negation ("not bad" vs. "bad"). Our model was trained on real-world text specifically to capture this kind of context-sensitivity, not a simple positive/negative word list.

---

## 5. Word/Sentence Embeddings & Semantic Similarity

**What it is:** An embedding is a way of converting text (a word, sentence, or document) into a list of numbers (a vector) such that texts with *similar meaning* end up with *similar vectors*. Once text is turned into vectors, you can mathematically compare meaning using **cosine similarity** — a measure of the angle between two vectors, ranging from -1 (opposite) to 1 (identical meaning), regardless of vector length.

**Where we use it:** This is the backbone of two features:
- **Framing divergence** — comparing whether two sentences from different outlets are "about the same thing" even if worded completely differently.
- **Narrative clustering** — grouping sentences from across all outlets by shared topic/theme.
- **Duplicate detection in live search** — recognizing when two articles are actually the same wire-service story republished by different outlets.

**Likely question:** *"How can the computer tell two differently-worded sentences mean the same thing?"*
**Good answer:** The embedding model was trained on massive amounts of text to learn that sentences with similar meaning should map to nearby points in a high-dimensional numeric space — even if they don't share many words. So "the bill passed narrowly" and "the measure squeaked through by a slim margin" end up close together in that space, even though they share almost no vocabulary. Cosine similarity then measures exactly how close.

---

## 6. Framing Divergence (our custom metric)

**What it is:** Our own designed metric, built on top of embeddings, that tries to answer: *for the same underlying fact, how differently do two outlets phrase it?* For every sentence in one outlet, we find its closest-meaning match in the other outlet (via cosine similarity). If that best match is still similar enough to count as "the same fact," we score how much the wording diverges (1 minus the similarity score). Low similarity pairs are discarded as unrelated content, not divergence.

**Where we use it:** The central comparative feature of the whole project — shown as a percentage per pair of outlets, with the actual most-divergent sentence pairs surfaced as evidence.

**Likely question:** *"Is this the same as detecting bias?"*
**Good answer:** No, and we're explicit about that in the interface. It measures *phrasing difference for the same fact*, not whether either outlet is biased. Two outlets could phrase something very differently for entirely neutral stylistic reasons. We validated it against human bias annotations and found a real but weak correlation — so we present it as "phrasing differs," never as a bias verdict.

**Likely question:** *"Why call it a 'lower bound'?"*
**Good answer:** Because we only compare each sentence to its single closest match in the other article (nearest-neighbor matching), not an optimal overall pairing between the two full articles. A more advanced version could use an algorithm that finds the best *global* pairing between all sentences (like the Hungarian algorithm used in optimal assignment problems), which would give a more complete picture — that's one of our planned improvements.

---

## 7. Keyword/Keyphrase Extraction (KeyBERT)

**What it is:** Automatically identifying the most representative words or phrases in a document, without a human tagging them. Modern approaches (like KeyBERT) use the same embedding technique from Section 5: they generate candidate phrases, embed them, and rank them by how close their meaning is to the meaning of the whole document.

**Where we use it:** Part of our **topic-overlap omission** score — extracting the main themes each outlet's article covers, so we can tell if one outlet skipped an entire angle of the story that others covered (even if it's not tied to a specific named entity).

**Likely question:** *"How is this different from just picking the most frequent words?"*
**Good answer:** Frequency-based keyword extraction (like TF-IDF) misses phrases that are meaningful but not repeated often. Embedding-based extraction ranks candidate phrases by how well they represent the *meaning* of the whole document, which tends to surface more genuinely representative themes rather than just the most-repeated words.

---

## 8. Clustering (Unsupervised Learning) — K-Means

**What it is:** An unsupervised machine learning technique that groups data points into a fixed number of clusters based on similarity, without being told in advance what the groups should represent. K-Means specifically works by picking cluster "centers," assigning each point to its nearest center, then repeatedly recalculating the centers until the groupings stabilize.

**Where we use it:** **Narrative clustering** — grouping all sentences from all outlets covering an event into a handful of shared sub-narratives (e.g., "economic impact," "political reaction," "eyewitness accounts") without predefining what those narratives are. Each cluster is embedded (Section 5) first, then K-Means groups the embeddings.

**Likely question:** *"How does the computer know what to call each cluster?"*
**Good answer:** It doesn't — K-Means only groups similar sentences together; it doesn't generate labels. To make the cluster interpretable, we surface the single sentence closest to each cluster's mathematical center as a "representative sentence," which a human can read to understand what the cluster is about.

**Likely question:** *"Why 4 clusters and not some other number?"*
**Good answer:** It's a reasonable default that keeps sub-narratives digestible in the interface; the number can be adjusted, and it's automatically reduced if an event doesn't have enough sentences to fill that many meaningfully distinct groups.

---

## 9. Transformer Language Models & Transfer Learning

**What it is:** Transformers are the neural network architecture behind essentially all modern large language models (BERT, RoBERTa, DistilBERT, GPT, etc.). Their key innovation is the **attention mechanism**, which lets the model weigh the relevance of every other word in a sentence when interpreting each word — capturing context far better than older architectures. **Transfer learning** (also called **fine-tuning**) means taking a model that was already pretrained on a huge general-purpose text corpus (so it already "understands" language broadly) and further training it on a smaller, task-specific dataset so it specializes in one job.

**Where we use it:**
- **Pretrained, used as-is:** the sentiment model, the sentence-embedding model, and the NER model are all transformer-family or transformer-adjacent models used off-the-shelf.
- **Fine-tuned by us:** the sentence-level bias detector is a transformer model we specifically trained further on human-labeled examples of biased language, so it specializes in that one task. We compared three different pretrained transformer architectures (a full-size model, a variant with a different pretraining objective, and a lighter "distilled" version) to see which fine-tuned best for this specific job.

**Likely question:** *"Why fine-tune instead of training a model from scratch?"*
**Good answer:** Training a language model from scratch would require enormous amounts of data and compute we don't have access to. Fine-tuning starts from a model that already understands grammar, vocabulary, and general language patterns, and only needs a comparatively small labeled dataset to adapt that general understanding to our specific task — detecting biased phrasing.

**Likely question:** *"What's the difference between the three models you compared?"*
**Good answer:** They're all transformer architectures but differ in size and training approach — one is a larger "standard" model, one uses an improved pretraining method that generally performs better on downstream tasks, and one is a "distilled" (compressed) version of the standard model, trained to mimic a larger model's behavior with fewer parameters, trading a small amount of accuracy for significantly faster inference speed.

---

## 10. Evaluation Metrics — Accuracy, F1 Score, ROC AUC, Correlation

**What they are:**
- **Accuracy** — the percentage of predictions the model got right overall. Misleading when classes are imbalanced (see below).
- **Precision** — of everything the model flagged as positive, what fraction actually was positive.
- **Recall** — of everything that actually was positive, what fraction the model successfully flagged.
- **F1 score** — the harmonic mean of precision and recall; a single number that balances both, and is much more informative than accuracy when one class (here, "biased") is rare.
- **ROC AUC** — a score between 0.5 (no better than random guessing) and 1.0 (perfect) measuring how well a model's continuous output score ranks positive examples above negative ones, across every possible decision threshold.
- **Point-biserial correlation** — a specific correlation coefficient used when one variable is continuous (our divergence score) and the other is binary (human-labeled biased or not); tells you how strongly the two move together.

**Where we use them:**
- **F1 score** decided which of our three bias-detection models "won," because BASIL's biased-sentence examples are a minority class (most sentences are not biased) — a model can get high accuracy by just predicting "not biased" every time, so F1 is the fairer comparison.
- **ROC AUC and point-biserial correlation** were used to test our framing-divergence metric against real human bias annotations — checking whether higher divergence scores actually tend to line up with sentences a human flagged as biased.

**Likely question:** *"Why not just use accuracy for everything?"*
**Good answer:** Accuracy can be misleading with imbalanced data. If only 15% of sentences are truly biased, a model that always predicts "not biased" would score 85% accuracy while being completely useless. F1 score penalizes that failure mode because it also accounts for how many *actual* biased sentences got missed (recall) and how many flagged sentences were wrong (precision).

**Likely question:** *"What does an AUC of 0.56 actually mean?"*
**Good answer:** An AUC of 0.5 means the metric is no better than a coin flip at telling biased from non-biased sentences; 1.0 would mean perfect separation. 0.56 means our framing-divergence score does carry *some* real signal — it's statistically better than chance — but it's a weak one, nowhere near strong enough to use as a standalone bias detector. That's exactly why we present it to users as "phrasing differs," not "this is biased."

---

## 11. Data Splitting & Avoiding Data Leakage

**What it is:** When training and evaluating a machine learning model, you must split your data into a training set (used to teach the model) and a test set (used to check how well it generalizes to unseen data). **Data leakage** happens when information from the test set "leaks" into training, or when the split isn't independent enough — making the model look better than it really is. A common, easy-to-miss version of this: splitting individual sentences randomly, when multiple sentences from the *same article* are highly similar to each other — some of those sentences could land in training and near-duplicates in test, letting the model "cheat" by having effectively seen similar content already.

**Where we use it:** For the bias-detection model, we split by *article*, not by sentence — every sentence from a given article stays entirely in either training or test, never split across both. This prevents inflated performance numbers.

**Likely question:** *"Why does it matter which article a sentence came from?"*
**Good answer:** Sentences from the same article tend to share vocabulary, topic, and style. If we split randomly by sentence, some sentences from an article could end up in training while very similar sentences from that same article end up in the test set — the model might do well not because it generalizes, but because it's effectively seen highly similar content already. Splitting by article closes that loophole.

---

## 12. Class Imbalance

**What it is:** When one category in a labeled dataset vastly outnumbers another (e.g., far more "not biased" sentences than "biased" ones). Models trained naively on imbalanced data tend to become biased toward predicting the majority class.

**Where we use it:** Directly relevant to the bias-detection task — most sentences in real news articles are not flagged as biased, so this imbalance shaped both how we labeled/evaluated (F1 over accuracy) and is consistent with our dataset analysis (annotations skew 82% negative-in-tone vs. 18% positive, and biased spans are a minority of all sentences).

---

## 13. APIs and Web Architecture

**What it is:** An **API (Application Programming Interface)** is a defined set of operations one piece of software exposes so other software can request data or trigger actions, typically over HTTP in a web context. A **REST API** organizes those operations around resources (like "an event" or "an article") accessed via standard HTTP methods (GET to read, POST to create/trigger).

**Where we use it:** Our backend exposes a REST API — the frontend calls it to load events, trigger analysis, and fetch each type of result (entities, sentiment, framing, etc.), keeping the analysis logic and the visual interface as separate, independently replaceable layers.

**Likely question:** *"Why separate the backend and frontend instead of building one combined program?"*
**Good answer:** Separation of concerns — the backend focuses purely on data processing and analysis, while the frontend focuses purely on presentation. This makes each side easier to develop, test, and reason about independently, and means the same backend could serve other frontends (mobile app, another dashboard) without changes.

---

## 14. Databases — Relational Storage

**What it is:** A relational database organizes data into tables with defined columns and relationships between tables (e.g., an article "belongs to" an event via a foreign key). This structure enforces consistency and allows efficient querying/joining of related data.

**Where we use it:** We store events, articles, entity mentions, and comparison scores as related tables, so that, for example, "get me every entity mentioned in this event, broken down by source" is a straightforward, efficient query rather than something we'd have to reconstruct from scratch each time.

**Likely question:** *"Why store results at all instead of recalculating every time someone views an event?"*
**Good answer:** Running the full analysis pipeline involves multiple AI models and is relatively slow — storing results means viewing an already-analyzed event again is instant. We do intentionally *not* store narrative clusters, as a simplicity trade-off, which is why that one feature is recalculated live each time (and is correspondingly a bit slower to load).

---

## 15. Live Data Ingestion & Web Scraping Considerations

**What it is:** Pulling real-world, up-to-date data from external sources at request time, as opposed to relying only on a fixed, pre-packaged dataset. This introduces practical challenges: rate limits (services restricting how often you can ask them for data), messy HTML that needs to be cleaned into readable text, and duplicate/syndicated content across sources.

**Where we use it:** Our live-topic search pulls from GDELT (an open, free global news index) rather than a paid news API, extracts clean article text from raw webpages (stripping ads, navigation, and boilerplate), filters out articles too short to be real content (likely paywalled stubs), and removes duplicate wire-service stories using the same embedding-similarity technique from Section 5.

**Likely question:** *"What happens if the live search fails or a website can't be read?"*
**Good answer:** The system is built to fail safely — if one article can't be cleanly extracted, it's simply skipped rather than crashing the whole search, so a single problematic source doesn't block the rest of the results.

---

## 16. Political Lean Tagging

**What it is:** Categorizing a news source along a left/center/right spectrum based on known, publicly documented editorial orientation — not based on anything the AI model itself infers from the text.

**Where we use it:** For live events, each source is tagged using a reference list of well-known outlets and their general editorial leanings, shown as a badge in the interface — explicitly labeled as general orientation, not an automated bias judgment of that specific article.

**Likely question:** *"Isn't labeling outlets by political lean itself biased?"*
**Good answer:** We used a fixed, pre-researched reference list rather than having any model infer lean from the text itself, and the interface is explicit that the badge reflects a source's general known orientation, not a judgment about the specific article's content — keeping that distinction clear was a deliberate design choice.

---

## 17. Glossary (fast lookup)

| Term | One-line definition |
|---|---|
| NER | Detecting names of people/organizations/places in text |
| Fuzzy matching | Deciding two differently-written strings refer to the same thing |
| Sentiment analysis | Classifying text as positive/negative/neutral |
| Embedding | Turning text into a list of numbers that captures its meaning |
| Cosine similarity | A number measuring how close two embeddings are in meaning |
| Transformer | The neural network architecture behind modern language models |
| Fine-tuning | Further training a pretrained model on a smaller, specific task |
| K-Means | An algorithm that groups similar data points into clusters |
| F1 score | A balanced accuracy measure that's fair on imbalanced data |
| ROC AUC | How well a score ranks true positives above true negatives |
| Data leakage | Test data accidentally influencing/inflating training results |
| Class imbalance | One label being much rarer than another in a dataset |
| REST API | A structured way for software to request/send data over the web |
| Relational database | Data organized into related tables with defined structure |

---

## 18. Suggested Presentation Flow

If asked to walk through the project live, a natural order is:

1. **Motivation** — why comparing news coverage across outlets matters, and why doing it by hand doesn't scale.
2. **The pipeline, end to end** — ingest → extract entities → score sentiment → measure framing → measure omission → cluster → (optional) detect bias.
3. **Pick one feature and go deep** — framing divergence is the strongest story, because you can show the full arc: what it is → how it's computed (embeddings + cosine similarity) → how you validated it against real human data (AUC) → how you were honest about its limits in the interface.
4. **Show the bias-detection model comparison** — a clean example of an actual ML experiment (three models, fair comparison via F1, leakage-safe evaluation).
5. **Live demo** — pick a curated event and a live-searched topic, walk through each panel.
6. **Limitations and what's next** — shows maturity; a project that knows its own weak points is more credible than one claiming perfection.

---

## 19. Anticipate the Hard Questions

- **"Is this system actually detecting bias?"** — No. It surfaces *differences* — in entities mentioned, sentiment, phrasing, and omissions — and only one optional component (the fine-tuned classifier) makes a bias *prediction* at all, and even that is presented as a probability, not a verdict.
- **"How do you know your metrics aren't just noise?"** — We specifically validated the framing metric against thousands of human-annotated examples and reported the real result (a weak but statistically genuine correlation) rather than assuming it works.
- **"Could this be used to unfairly label a news outlet?"** — The interface is intentionally designed to show *differences*, with heavy caveats about what each score does and doesn't mean, specifically to avoid that misuse.
- **"What would you do with more time?"** — Point to the Planned Enhancements section of the project report: deployment, more live sources, persisting cluster results, formally validating omission/clustering, and improving the framing alignment algorithm.
