# tianchi-ocr

https://tianchi.aliyun.com/competition/entrance/531902/introduction

```bash
# 1. Downlaod CSV files to $TIANCHI_OCR_DATA/raw

# 2. Download the referenced images and normalize labels.
export TIANCHI_OCR_DATA=$(pyproject-data-folder "$VKIT_ROOT" "$VKIT_DATA" vkit_case/tianchi_ocr)

fireball vkit_case/tianchi_ocr/prep.py:download_images \
    --csv_file="$TIANCHI_OCR_DATA/raw/Xeon1OCR_round1_train_20210524.csv" \
    --output_folder="$TIANCHI_OCR_DATA/prep/train0"

fireball vkit_case/tianchi_ocr/prep.py:download_images \
    --csv_file="$TIANCHI_OCR_DATA/raw/Xeon1OCR_round1_train1_20210526.csv" \
    --output_folder="$TIANCHI_OCR_DATA/prep/train1"

fireball vkit_case/tianchi_ocr/prep.py:download_images \
    --csv_file="$TIANCHI_OCR_DATA/raw/Xeon1OCR_round1_train2_20210526.csv" \
    --output_folder="$TIANCHI_OCR_DATA/prep/train2"

fireball vkit_case/tianchi_ocr/prep.py:download_images \
    --csv_file="$TIANCHI_OCR_DATA/raw/Xeon1OCR_round1_test1_20210528.csv" \
    --output_folder="$TIANCHI_OCR_DATA/prep/test1" \
    --is_test

fireball vkit_case/tianchi_ocr/prep.py:download_images \
    --csv_file="$TIANCHI_OCR_DATA/raw/Xeon1OCR_round1_test2_20210528.csv" \
    --output_folder="$TIANCHI_OCR_DATA/prep/test2" \
    --is_test

fireball vkit_case/tianchi_ocr/prep.py:download_images \
    --csv_file="$TIANCHI_OCR_DATA/raw/Xeon1OCR_round1_test3_20210528.csv" \
    --output_folder="$TIANCHI_OCR_DATA/prep/test3" \
    --is_test

# Convert to scale sample.
# DEBUG.
fireball vkit_case/tianchi_ocr/prep.py:generate_scale_samples_from_folder \
    --input_folder="$TIANCHI_OCR_DATA/debug/example-folder" \
    --output_folder="$TIANCHI_OCR_DATA/debug/scale-sample" \
    --dilate_ratio="0.7" \
    --long_side="720"

fireball vkit_case/tianchi_ocr/prep.py:vis_scale_samples \
    --input_folder="$TIANCHI_OCR_DATA/debug/scale-sample" \
    --output_folder="$TIANCHI_OCR_DATA/debug/vis-scale-sample" \
    --num_samples="10"

# PROD.
fireball vkit_case/tianchi_ocr/prep.py:generate_scale_samples_from_folder \
    --input_folder="$TIANCHI_OCR_DATA/prep/train0" \
    --output_folder="$TIANCHI_OCR_DATA/scale-sample/train0" \
    --dilate_ratio="0.7" \
    --long_side="720"

fireball vkit_case/tianchi_ocr/prep.py:vis_scale_samples \
    --input_folder="$TIANCHI_OCR_DATA/scale-sample/train0" \
    --output_folder="$TIANCHI_OCR_DATA/debug/scale-sample/train0" \
    --num_samples="10"
```
