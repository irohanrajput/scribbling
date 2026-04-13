# RAG, Embeddings, Vectors, Semantics

This document explains how a RAG system works, using a "Perplexity Lite" project as a running example. The project searches the web, stores scraped content in a vector database, and generates answers grounded in that context.

---

## Architecture Overview

```
User Query
    |
    v
+----------+     +------------+     +-------------+     +----------+
|  Search   |---->|   Scrape   |---->|  Vector DB  |---->|   LLM    |
| (DuckDuck |     | (Beautiful |     |  (ChromaDB)  |     |  (Groq)  |
|   Go)     |     |   Soup)    |     |              |     |          |
+----------+     +------------+     +-------------+     +----------+
```

### Pipeline

1. **Search** - Query DuckDuckGo for top 5 URLs
2. **Scrape** - Fetch each URL, extract text with BeautifulSoup
3. **Chunk & Store** - Split text into 500-char chunks, store in ChromaDB with HuggingFace embeddings (`all-MiniLM-L6-v2`)
4. **Retrieve** - Similarity search for top 3 relevant chunks
5. **Generate** - Send query + context to Groq LLM, return answer with citations

---

## What is an Embedding?

Computers don't understand words. They understand numbers. An **embedding** is a way to convert text into a list of numbers (a "vector") that captures the **meaning** of that text.

The model `all-MiniLM-L6-v2` takes any text and outputs a list of **384 numbers**:

```
"king"   -> [0.21, -0.05, 0.87, ..., 0.33]   (384 numbers)
"queen"  -> [0.19, -0.03, 0.85, ..., 0.31]   (384 numbers)
"banana" -> [-0.72, 0.44, 0.01, ..., -0.56]  (384 numbers)
```

Key insight: **"king" and "queen" will have similar numbers because they're semantically similar.** "Banana" will have very different numbers because it means something completely different.

Important: if you pass the same sentence 10 times, you get the exact same 384 numbers every time. The model is deterministic. Same input = same output.

---

## How Text is Converted into Embeddings

The model `all-MiniLM-L6-v2` is a **transformer neural network** (same family as GPT/BERT). Here's the process:

```
"backend engineer jobs in bangalore"
        |
        v
+---------------+
|   Tokenizer   |  Splits text into tokens:
|               |  ["backend", "engineer", "jobs", "in", "bang", "##alore"]
+-------+-------+
        |
        v
+---------------+
|  Transformer  |  6 layers of attention - each token "looks at"
|    Layers     |  every other token to understand context
+-------+-------+
        |
        v
+---------------+
|    Pooling    |  Combine all token outputs into ONE vector
+-------+-------+
        |
        v
[0.21, -0.05, 0.87, ..., 0.33]   <- 384 numbers
```

This is called a **"local" embedding** because the model runs on your machine (downloaded from HuggingFace). No API call, no internet needed. Compare this with OpenAI embeddings, which send your text to their servers — that would be a "remote" embedding.

---

## Vectors vs Dimensions — Clearing Up the Confusion

A common confusion: the 384 numbers are NOT 384 separate vectors. The entire list is **ONE vector**. The 384 numbers inside it are called **dimensions**.

Think of it like coordinates:

```
2D point (on a map):     [x, y]           -> 1 vector with 2 dimensions
3D point (in a room):    [x, y, z]        -> 1 vector with 3 dimensions
Embedding (meaning):     [n1, n2, ..n384] -> 1 vector with 384 dimensions
```

A location on a map like `[12.97, 77.59]` (Bangalore's lat/long) is ONE point, not two points. Same idea — `[0.21, -0.05, 0.87, ..., 0.33]` is ONE point in a 384-dimensional space.

### Why Pooling is Needed

Before pooling, each **token** has its own vector:

```
"backend"  -> [0.11, 0.42, ..., 0.08]   <- 384 numbers
"engineer" -> [0.33, -0.21, ..., 0.55]  <- 384 numbers
"jobs"     -> [0.09, 0.17, ..., -0.44]  <- 384 numbers
```

That's 3 separate vectors — one per word. But ChromaDB needs **one vector per chunk**. So pooling combines them — the simplest method is averaging:

```
dimension 1:  (0.11 + 0.33 + 0.09) / 3 = 0.18
dimension 2:  (0.42 + -0.21 + 0.17) / 3 = 0.13
...
dimension 384: (0.08 + 0.55 + -0.44) / 3 = 0.06

Result: [0.18, 0.13, ..., 0.06]  <- ONE vector representing the whole sentence
```

| Term | What it means |
|---|---|
| **Vector** | The entire list of numbers — one per chunk/sentence |
| **Dimension** | Each individual number inside the vector |
| **384-dimensional** | Each vector has 384 numbers that together encode meaning |

---

## What is a Vector Database?

A regular database stores rows and columns. You search with exact matches (`WHERE name = 'John'`).

A **vector database** stores those lists of numbers (vectors) and lets you search by **similarity** instead of exact match.

ChromaDB stores vectors on disk:

```
+--------------------------------------------------+
|                   ChromaDB                        |
|                                                   |
|  chunk_1: "Backend roles at Infosys..."           |
|  vector:  [0.21, -0.05, 0.87, ..., 0.33]        |
|                                                   |
|  chunk_2: "Banana bread recipe..."                |
|  vector:  [-0.72, 0.44, 0.01, ..., -0.56]       |
|                                                   |
|  chunk_3: "Software engineer hiring in..."        |
|  vector:  [0.19, -0.03, 0.85, ..., 0.31]        |
|                                                   |
+--------------------------------------------------+
```

Each chunk of scraped text is stored **alongside** its embedding vector. The vector is used for searching. The original text is what gets returned and sent to the LLM.

---

## How Retrieval Works

When you search, here's what happens step by step:

### Step 1: Your query gets embedded using the SAME model

```
"backend engineer jobs in bangalore"
    -> [0.20, -0.04, 0.86, ..., 0.32]
```

### Step 2: Compare this vector against EVERY stored vector

```
query vector:   [0.20, -0.04, 0.86, ..., 0.32]
     vs
chunk_1 vector: [0.21, -0.05, 0.87, ..., 0.33]  -> similarity: 0.97  (very close!)
chunk_2 vector: [-0.72, 0.44, 0.01, ..., -0.56] -> similarity: 0.12  (not related)
chunk_3 vector: [0.19, -0.03, 0.85, ..., 0.31]  -> similarity: 0.95  (close!)
```

### Step 3: Return top k=3 most similar chunks

The "similarity" is calculated using **cosine similarity** — it measures the angle between two vectors:
- Same direction -> similarity close to 1.0 (very related)
- Opposite directions -> similarity close to -1.0 (unrelated)

**The same embedding model must be used for both storing and retrieving.** If you used different models, the numbers wouldn't be in the same "space" and comparison would be meaningless.

### The text doesn't need to match — the meaning does

```
Query:   "backend engineering jobs in Bengaluru"
Chunk:   "Backend Engineer - Flipkart Bengaluru. Build scalable APIs..."
```

These share almost no exact words. But embeddings capture that they mean the same thing. That's the power of embeddings over traditional keyword search.

---

## How Many Vectors are Stored?

**Multiple vectors** — one per chunk. If DuckDuckGo returns 5 URLs:

```
URL 1 (naukri.com)      -> 3000 chars -> 6 chunks  -> 6 vectors
URL 2 (linkedin.com)    -> 5000 chars -> 10 chunks -> 10 vectors
URL 3 (indeed.com)      -> 2000 chars -> 4 chunks  -> 4 vectors
URL 4 (glassdoor.com)   -> 4500 chars -> 9 chunks  -> 9 vectors
URL 5 (some blog)       -> 1500 chars -> 3 chunks  -> 3 vectors
                                         ---------
                                         32 vectors stored in ChromaDB
```

---

## The Text is Never Lost

A common question: "How are the mathematical numbers converted back to text?"

They're not. **Embeddings are one-way** — you can't reconstruct the original sentence from 384 numbers. But you don't need to, because ChromaDB stores BOTH:

```
+----------------------------------------------------------+
|  ChromaDB stores BOTH:                                    |
|                                                           |
|  text:   "Senior Backend Engineer at Wipro..."           |
|  vector: [0.231, -0.030, 0.421, 0.189, ...]             |
+----------------------------------------------------------+
```

The vector is like an **index in a book** — you use the index to find the right page, then you read the page itself, not the index.

---

## How the Query is Used (3 Times, Different Ways)

```python
# 1. As search text -> DuckDuckGo (no embedding, just a text search)
urls = search(query)

# 2. As a vector -> ChromaDB (EMBEDDED into 384-dim vector for similarity search)
docs = retrieve(query)

# 3. As plain text -> Groq LLM (pasted into the prompt for the LLM to read)
answer = generate_answer(query, docs)
```

| # | Where | Embedded? | Purpose |
|---|---|---|---|
| 1 | `search()` | No | Text sent to DuckDuckGo to find URLs |
| 2 | `retrieve()` | **Yes** | Converted to vector to find similar chunks |
| 3 | `generate_answer()` | No | Plain text in the prompt for the LLM |

---

## Full Detailed Walkthrough: "Senior Backend Engineer at Wipro"

### Step 1: Scrape

Raw HTML:

```html
<nav>Home Jobs Companies</nav>
<h1>Senior Backend Engineer</h1>
<p>Wipro, Bengaluru</p>
<p>Build scalable APIs using Java Spring Boot. 5+ years experience required.</p>
```

After `BeautifulSoup.get_text()`:

```
"Home Jobs Companies Senior Backend Engineer Wipro, Bengaluru Build scalable APIs using Java Spring Boot. 5+ years experience required."
```

### Step 2: Chunk

131 characters < 500 limit, so the entire text becomes **one chunk**.

### Step 3: Embed

**Tokenization:**

```
["[CLS]", "home", "jobs", "companies", "senior", "backend", "engineer",
 "wi", "##pro", ",", "bengal", "##uru", "build", "scala", "##ble",
 "api", "##s", "using", "java", "spring", "boot", ".", "5", "+",
 "years", "experience", "required", ".", "[SEP]"]
```

29 tokens. `[CLS]` and `[SEP]` are special tokens the model adds. Words like "Wipro" become `"wi" + "##pro"` because the model hasn't seen "Wipro" as a whole word. `##` means "continuation of previous token".

**Per-token vectors (showing 8 dims instead of 384 for readability):**

```
"[CLS]"      -> [ 0.01,  0.03, -0.02,  0.05,  0.01, -0.04,  0.02,  0.06]
"home"        -> [ 0.44,  0.12, -0.33,  0.08, -0.21,  0.55,  0.09, -0.17]
"jobs"        -> [ 0.31, -0.05,  0.67,  0.22,  0.14, -0.08,  0.43,  0.11]
"companies"   -> [ 0.28,  0.09,  0.51,  0.18,  0.07, -0.12,  0.38,  0.05]
"senior"      -> [ 0.15, -0.22,  0.71,  0.33,  0.41,  0.09,  0.55,  0.27]
"backend"     -> [ 0.52, -0.18,  0.83,  0.45,  0.38,  0.21,  0.61,  0.34]
"engineer"    -> [ 0.48, -0.15,  0.79,  0.41,  0.35,  0.18,  0.58,  0.31]
"wi"          -> [ 0.11,  0.04,  0.22,  0.09,  0.03,  0.07,  0.14,  0.02]
"##pro"       -> [ 0.08,  0.02,  0.19,  0.06,  0.01,  0.05,  0.11, -0.01]
","           -> [ 0.00,  0.01,  0.00,  0.01, -0.01,  0.00,  0.01,  0.00]
"bengal"      -> [ 0.39,  0.27,  0.55,  0.30,  0.22,  0.33,  0.41,  0.19]
"##uru"       -> [ 0.14,  0.10,  0.21,  0.11,  0.08,  0.12,  0.15,  0.07]
"build"       -> [ 0.35, -0.11,  0.62,  0.28,  0.19,  0.15,  0.47,  0.22]
"scala"       -> [ 0.29, -0.09,  0.54,  0.24,  0.16,  0.11,  0.40,  0.18]
"##ble"       -> [ 0.10,  0.03,  0.18,  0.07,  0.05,  0.04,  0.13,  0.06]
"api"         -> [ 0.41, -0.14,  0.73,  0.37,  0.30,  0.19,  0.53,  0.28]
"##s"         -> [ 0.03,  0.01,  0.05,  0.02,  0.01,  0.01,  0.04,  0.01]
"using"       -> [ 0.07,  0.02,  0.11,  0.04,  0.03,  0.02,  0.08,  0.03]
"java"        -> [ 0.46, -0.20,  0.77,  0.39,  0.32,  0.17,  0.56,  0.29]
"spring"      -> [ 0.42, -0.16,  0.70,  0.35,  0.28,  0.14,  0.51,  0.25]
"boot"        -> [ 0.38, -0.13,  0.65,  0.31,  0.25,  0.12,  0.48,  0.23]
"."           -> [ 0.00,  0.01,  0.00,  0.01, -0.01,  0.00,  0.01,  0.00]
"5"           -> [ 0.05,  0.01,  0.09,  0.03,  0.02,  0.01,  0.06,  0.02]
"+"           -> [ 0.01,  0.00,  0.02,  0.01,  0.00,  0.00,  0.01,  0.00]
"years"       -> [ 0.20, -0.07,  0.44,  0.19,  0.13,  0.08,  0.33,  0.14]
"experience"  -> [ 0.33, -0.10,  0.61,  0.27,  0.20,  0.13,  0.45,  0.21]
"required"    -> [ 0.18, -0.06,  0.39,  0.16,  0.11,  0.07,  0.29,  0.12]
"."           -> [ 0.00,  0.01,  0.00,  0.01, -0.01,  0.00,  0.01,  0.00]
"[SEP]"      -> [ 0.02,  0.01, -0.01,  0.03,  0.00, -0.02,  0.01,  0.04]
```

**Pooling — 29 vectors become 1:**

Mean pooling averages each dimension across all 29 tokens:

```
Dim 1: (0.01+0.44+0.31+0.28+0.15+0.52+0.48+0.11+0.08+0.00+0.39+0.14+0.35+0.29+0.10+0.41+0.03+0.07+0.46+0.42+0.38+0.00+0.05+0.01+0.20+0.33+0.18+0.00+0.02) / 29 = 0.231

Dim 2: (0.03+0.12+-0.05+0.09+-0.22+-0.18+-0.15+0.04+0.02+0.01+0.27+0.10+-0.11+-0.09+0.03+-0.14+0.01+0.02+-0.20+-0.16+-0.13+0.01+0.01+0.00+-0.07+-0.10+-0.06+0.01+0.01) / 29 = -0.030

...same for all 384 dimensions...
```

**Final chunk vector:** `[0.231, -0.030, 0.421, 0.189, 0.139, 0.088, 0.312, 0.134]`

### Step 4: Store

ChromaDB saves both the text and the vector together.

### Step 5: Retrieve

Query "senior backend engineer at Wipro" goes through the same tokenize -> per-token vectors -> pool process:

```
Query vector: [0.228, -0.028, 0.418, 0.185, ...]
Chunk vector: [0.231, -0.030, 0.421, 0.189, ...]
               ^ very close numbers = high similarity
```

ChromaDB returns the **original text** (not the vector) -> sent to LLM -> you get your answer.

---

## The Chunking Problem

A real weakness in naive character-level chunking: words can get split across chunks.

```
Chunk 1 (chars 0-499):   "...looking for a talented software engi"
Chunk 2 (chars 500-999): "neer with 5 years of backend experience..."
```

"Engineer" is split into "engi" and "neer". Neither chunk captures the full meaning.

### Fixes

1. **Split on sentences, not characters** — cut at periods, not at character 500
2. **Overlapping chunks** — chunks share some characters so split words appear complete in at least one chunk
3. **LangChain's RecursiveCharacterTextSplitter** — tries paragraph breaks first, then newlines, then sentences, then spaces, and only as a last resort at characters

---

## The Big Picture: Why RAG Matters

RAG lets you analyze internal/private documents without exposing them to external AI:

1. Pour documents into the embedding model (runs locally)
2. Embeddings are stored in a local vector database
3. When you ask a question, it's embedded with the same model
4. Most similar chunks are found by comparing vectors
5. Those chunks (original text) + your question are sent to an LLM
6. LLM generates an answer grounded in your documents

Your data stays private during embedding and retrieval. The only part that leaves your machine is the final step where selected chunks are sent to the LLM for answer generation — and even that can be made local by running an open-source LLM on your machine.
