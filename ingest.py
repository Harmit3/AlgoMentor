import chromadb
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Seed corpus — add more entries as you go
CORPUS = [
    {
        "id": "dijkstra_invariant",
        "topic": "dijkstra",
        "text": "Dijkstra's invariant: once a node is finalized (popped from the priority queue), its shortest distance is permanently known. This only holds when all edge weights are non-negative. With negative edges, a later path could undercut a finalized distance — breaking the invariant."
    },
    {
        "id": "dijkstra_negative_edges",
        "topic": "dijkstra",
        "text": "MISTAKE: Using the standard greedy shortest-path method on graphs with negative edge weights. SYMPTOM: Wrong shortest paths on graphs with negative edges. ROOT CAUSE: Finalizing a node too early is only safe when all edge weights are non-negative. HINT_1: What guarantee do you rely on when a node is finalized? HINT_2: Draw A->B (4), A->C (1), C->B (-3). Can a later path improve an earlier decision? HINT_3: What kind of shortest-path method keeps relaxing edges instead of trusting one greedy finalization?"
    },
    {
        "id": "dijkstra_priority_queue",
        "topic": "dijkstra",
        "text": "The priority queue in Dijkstra always pops the node with the smallest known distance. This greedy choice is valid because with non-negative weights, no future path can improve an already-finalized node. A regular queue (BFS) would process nodes by hop count, not by distance — wrong for weighted graphs."
    },
    {
        "id": "dp_overlapping_subproblems",
        "topic": "dynamic_programming",
        "text": "Dynamic programming applies when a problem has overlapping subproblems — the same subproblem is solved multiple times in naive recursion. Memoization stores results to avoid recomputation. The key insight: if you draw the recursion tree and see duplicate nodes, DP will help."
    },
    {
        "id": "dp_optimal_substructure",
        "topic": "dynamic_programming",
        "text": "MISTAKE: Applying DP to problems without optimal substructure. Optimal substructure means the optimal solution to the whole problem contains optimal solutions to subproblems. Longest path in a general graph does NOT have this — but shortest path does."
    },
    {
        "id": "bfs_vs_dijkstra",
        "topic": "graph",
        "text": "MISTAKE: Using BFS for weighted shortest path. SYMPTOM: Correct on unweighted graphs, wrong when weights differ. ROOT CAUSE: BFS minimizes hop count, not total weight. HINT: If all weights were 1, would BFS be correct? What changes when weights vary?"
    },
    {
    "id": "two_sum_hashmap",
    "topic": "array",
    "text": "PROBLEM: Two Sum. TUTOR GOAL: Guide the student toward a one-pass lookup-based solution without naming the data structure immediately. COMMON PITFALL: Sorting changes positions and makes original indices harder to recover. HINT_1: What if you could check whether a needed number was seen before in near-constant time? HINT_2: For each number x, what partner value would complete the target? HINT_3: If you remember previously seen numbers, what extra information would help you return positions instead of values?"
    },
]

def ingest():
    collection = chroma_client.get_or_create_collection("algo_corpus")

    texts = [item["text"] for item in CORPUS]
    embeddings = embedder.encode(texts).tolist()

    collection.upsert(
        ids=[item["id"] for item in CORPUS],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{"topic": item["topic"]} for item in CORPUS],
    )
    print(f"Ingested {len(CORPUS)} chunks into ChromaDB.")

if __name__ == "__main__":
    ingest()
