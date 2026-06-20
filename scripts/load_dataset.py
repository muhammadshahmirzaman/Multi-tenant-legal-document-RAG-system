import os
import shutil
from datasets import load_dataset
from app.workers.ingest_task import ingest_text

# Set a shorter cache directory for Hugging Face to avoid Windows path length limits
HF_CACHE_DIR = "C:\\hf_cache"
os.makedirs(HF_CACHE_DIR, exist_ok=True)
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["HF_DATASETS_CACHE"] = HF_CACHE_DIR

TENANT_ID  = "00000000-0000-0000-0000-000000000001"
OUTPUT_DIR = "data/processed"
MAX_DOCS   = 50

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Downloading CUAD dataset from HuggingFace...")
# Attempt to load the dataset. We use streaming=True to bypass Windows path length limits.
# We also try to use a custom cache directory that is shorter than the default.
HF_CACHE_DIR = "C:\\hf_cache"
os.makedirs(HF_CACHE_DIR, exist_ok=True)

try:
    # Try to load the version with text directly
    dataset = load_dataset("json", data_files="https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/CUAD_v1/CUAD_v1.json", split="train")
except:
    # Fallback to default but with custom short cache dir
    dataset = load_dataset("theatticusproject/cuad", split="train", cache_dir=HF_CACHE_DIR)

print(f"Total CUAD samples: {len(dataset)}")

seen_titles = set()
docs_loaded = 0

def process_sample(title, context, docs_loaded):
    if title in seen_titles:
        return docs_loaded, False
    seen_titles.add(title)

    safe_name = title.replace("/", "_").replace(" ", "_").replace(":", "_").replace("\"", "_")
    out_path  = f"{OUTPUT_DIR}/{safe_name}.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(context)

    print(f"[{docs_loaded+1}/{MAX_DOCS}] Ingesting: {title}")
    # Use the synchronous ingest_text helper for scripted ingestion
    try:
        ingest_text(
            file_path=out_path,
            tenant_id=TENANT_ID,
            filename=title,
        )
    except Exception as e:
        print(f"Error ingesting {title}: {e}")
        return docs_loaded, False

    return docs_loaded + 1, True

for sample in dataset:
    # Handle the single-sample structure from raw JSON (all docs in 'data')
    if "data" in sample:
        for doc in sample["data"]:
            if docs_loaded >= MAX_DOCS:
                break
            
            title = doc.get("title", "Unknown")
            # Context is usually in paragraphs
            context = ""
            for para in doc.get("paragraphs", []):
                context = para.get("context", "")
                if context:
                    break
            
            if not context:
                continue
                
            docs_loaded, success = process_sample(title, context, docs_loaded)
        if docs_loaded >= MAX_DOCS:
            break
        continue
    
    # Handle the standard flattened structure
    if "title" in sample and "paragraphs" in sample:
        title   = sample["title"]
        context = sample["paragraphs"][0]["context"]
        docs_loaded, success = process_sample(title, context, docs_loaded)
    
    if docs_loaded >= MAX_DOCS:
        break

print(f"\nDone. {docs_loaded} contracts ingested.")
