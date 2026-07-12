import numpy as np
from sklearn.cluster import KMeans
from sentence_transformers import util

from analysis.framing import get_model
from storage.db import get_conn
from preprocessing.clean import to_sentences

def cluster_event_sentences(event_id: int, n_clusters: int = 4) -> list[dict]:
    """
    Groups all sentences across all articles for the given event_id into n_clusters.
    Returns a list of clusters, each containing:
        - cluster_id (int)
        - representative_sentence (str)
        - source_distribution (dict: source -> count)
        - source_percentages (dict: source -> percentage)
        - total_sentences (int)
    """
    # 1. Fetch articles for this event
    with get_conn() as conn:
        articles = conn.execute(
            "SELECT id, source, clean_text FROM articles WHERE event_id = %s",
            (event_id,),
        ).fetchall()

    if not articles:
        return []

    # 2. Extract and keep track of sentences, their source, and their article ID
    all_sentences = []
    sentence_sources = []
    
    for art in articles:
        source = art["source"]
        sentences = to_sentences(art["clean_text"])
        for sent in sentences:
            all_sentences.append(sent)
            sentence_sources.append(source)

    if len(all_sentences) < n_clusters:
        n_clusters = max(1, len(all_sentences))

    # 3. Generate embeddings
    model = get_model()
    embeddings = model.encode(all_sentences)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    # 4. Perform KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    kmeans.fit(embeddings)
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_

    # 5. Extract results for each cluster
    clusters = []
    for c_id in range(n_clusters):
        # Indices of sentences in this cluster
        indices = np.where(labels == c_id)[0]
        if len(indices) == 0:
            continue

        cluster_embeddings = embeddings[indices]
        centroid = centroids[c_id]

        # Find the sentence closest to the centroid (representative sentence)
        # Cosine similarity between centroid and all embeddings in the cluster
        sims = util.cos_sim(cluster_embeddings, centroid).flatten().numpy()
        closest_idx_in_cluster = int(np.argmax(sims))
        representative_sentence = all_sentences[indices[closest_idx_in_cluster]]

        # Compute source distribution
        source_counts = {}
        for idx in indices:
            src = sentence_sources[idx]
            source_counts[src] = source_counts.get(src, 0) + 1

        total_in_cluster = len(indices)
        source_pct = {src: (count / total_in_cluster) for src, count in source_counts.items()}

        clusters.append({
            "cluster_id": c_id,
            "representative_sentence": representative_sentence,
            "source_distribution": source_counts,
            "source_percentages": source_pct,
            "total_sentences": total_in_cluster
        })

    return clusters
