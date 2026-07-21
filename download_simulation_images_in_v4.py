"""Download front (_03) images for India v4 simulation respondents from GCS"""
import os
import io
import pandas as pd
from PIL import Image
from google.cloud import storage

BUCKET_NAME = "mcb-hair-bucket"
CITY_FOLDERS = {
    1: "mcb_hair_bucket_mumbai_fixed",
    2: "mcb_hair_bucket_delhi",
    3: "mcb_hair_bucket_chennai",
    4: "mcb_hair_bucket_kolkata",
}

MODEL_IDS = [1094, 4053, 4082, 4117]


def build_image_path(resp_id: int, video: int) -> str:
    city_code = int(str(resp_id)[0])
    city_folder = CITY_FOLDERS[city_code]
    return f"{city_folder}/processed/results/images/{resp_id}/{video}/{resp_id}03_{video}.png"


def main():
    df = pd.read_csv("100_minwomen_50_s1r_0.0_de00_IN_v4.csv", sep=";")
    df = df[df["RESP_FINAL"].isin(MODEL_IDS)].copy()
    df = df[df["color_regions"].notna()]

    df = df.sort_values("S1R", ascending=False)
    df = df.drop_duplicates(subset=["RESP_FINAL", "color_regions"], keep="first")

    print(f"Total images to download: {len(df)}")

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    downloaded = 0
    failed = 0

    for _, row in df.iterrows():
        resp_id = int(row["RESP_FINAL"])
        video = int(row["VIDEO"])
        region = int(row["color_regions"])

        blob_path = build_image_path(resp_id, video)
        out_dir = f"data/Results_CT_local_for_app_IN_v4/{region}"
        out_path = f"{out_dir}/{region}_{resp_id}.jpg"

        os.makedirs(out_dir, exist_ok=True)

        blob = bucket.blob(blob_path)
        if not blob.exists():
            print(f"  MISSING: {blob_path}")
            failed += 1
            continue

        image_bytes = blob.download_as_bytes()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image.save(out_path, "JPEG")
        downloaded += 1
        print(f"  OK: {out_path}")

    print(f"\nDone: {downloaded} downloaded, {failed} missing")


if __name__ == "__main__":
    main()