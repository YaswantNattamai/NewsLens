import argparse
import json
import urllib.request
import zipfile
import os
import shutil
from pathlib import Path

def setup_args():
    parser = argparse.ArgumentParser(description="Download and/or prepare the BASIL dataset.")
    parser.add_argument(
        "--zip-path", 
        type=str, 
        default=None, 
        help="Path to a local BASIL dataset repository zip file if already downloaded. If not provided, it downloads from GitHub."
    )
    return parser.parse_args()

def download_and_prepare():
    args = setup_args()
    
    zip_path = Path("data/basil_master.zip")
    temp_extract_path = Path("data/basil_temp")
    dest_dir = Path("data/basil")
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Acquire the zip file
    if args.zip_path:
        local_zip = Path(args.zip_path)
        if not local_zip.exists():
            raise FileNotFoundError(f"Provided local zip file not found: {local_zip}")
        print(f"Using local zip file: {local_zip}")
        shutil.copy(local_zip, zip_path)
    else:
        url = "https://github.com/launchnlp/BASIL/archive/refs/heads/master.zip"
        print(f"Downloading from {url}...")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, zip_path)
        print("Download completed.")
    
    # 2. Extract the zip file
    print("Extracting...")
    if temp_extract_path.exists():
        shutil.rmtree(temp_extract_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_extract_path)
    print("Extraction completed.")
    
    # 3. Find the BASIL-main or BASIL-master directory
    root_dirs = [d for d in temp_extract_path.iterdir() if d.is_dir()]
    if not root_dirs:
        raise FileNotFoundError("No root directory found in the extracted zip.")
    
    basil_repo_root = root_dirs[0]
    src_articles_dir = basil_repo_root / "articles"
    src_annotations_dir = basil_repo_root / "annotations"
    
    if not src_articles_dir.exists() or not src_annotations_dir.exists():
        raise FileNotFoundError(f"Required 'articles' or 'annotations' directories not found in {basil_repo_root}")
        
    # 4. Merge articles and annotations
    article_paths = list(src_articles_dir.glob("**/*.json"))
    print(f"Found {len(article_paths)} raw articles. Merging and structuring...")
    
    merged_count = 0
    for art_path in article_paths:
        filename = art_path.name
        year_dir = art_path.parent.name
        
        # Annotation file mapping
        ann_filename = filename.replace(".json", "_ann.json")
        ann_path = src_annotations_dir / year_dir / ann_filename
        
        with open(art_path, "r", encoding="utf-8") as f:
            article_data = json.load(f)
            
        triplet_uuid = article_data.get("triplet-uuid")
        source = article_data.get("source")
        
        if not triplet_uuid or not source:
            continue
            
        word_level_annotations = []
        if ann_path.exists():
            with open(ann_path, "r", encoding="utf-8") as f:
                ann_data = json.load(f)
            phrase_annotations = ann_data.get("phrase-level-annotations", [])
            for ann in phrase_annotations:
                mapped_ann = ann.copy()
                if "txt" in mapped_ann and "text" not in mapped_ann:
                    mapped_ann["text"] = mapped_ann["txt"]
                word_level_annotations.append(mapped_ann)
        
        article_data["word-level-annotations"] = word_level_annotations
        
        event_dest_dir = dest_dir / triplet_uuid
        event_dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_file_path = event_dest_dir / f"{source.lower()}.json"
        with open(dest_file_path, "w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=4, ensure_ascii=False)
            
        merged_count += 1
        
    # 5. Clean up temporary directories
    shutil.rmtree(temp_extract_path)
    if zip_path.exists():
        os.remove(zip_path)
        
    print(f"Success! Merged and structured {merged_count} articles under '{dest_dir}'.")

if __name__ == "__main__":
    download_and_prepare()
