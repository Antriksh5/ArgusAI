import argparse
from huggingface_hub import snapshot_download

def main():
    parser = argparse.ArgumentParser(description="Download footage from HuggingFace without symlinks to save disk space.")
    parser.add_argument("--repo_id", required=True, help="Hugging Face repository ID")
    parser.add_argument("--local_dir", default="data/videos/indian_footage", help="Local directory to download to")
    args = parser.parse_args()

    print(f"Downloading from {args.repo_id} to {args.local_dir}...")
    
    # We use local_dir_use_symlinks=False to avoid cache disk-space issues,
    # as implemented in the previous successful approach.
    snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=args.local_dir,
        local_dir_use_symlinks=False,
        allow_patterns=["*.mp4", "*.avi", "*.mov"]
    )
    print("Download complete!")

if __name__ == "__main__":
    main()
