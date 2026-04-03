#!/usr/bin/env bash
set -e

echo "Cleaning up..."
rm -rf data/crop_*
mkdir -p files_to_upload

echo "Cropping..."
cd data
# Cell painting
mkdir -p crop_cellpainting_256
for file in full_cellpainting_1080/*.tif; do
    filename=$(basename "$file")
    magick "$file" -gravity center -crop 256x256+0+0 +repage -compress Zstd "crop_cellpainting_256/$filename"
done

# Time series
for ds in full_timeseries_*_1172; do
    if [ -d "$ds" ]; then
        out_dir="crop_${ds#full_}"
        out_dir="${out_dir/_1172/_293}"
        mkdir -p "$out_dir"
        for dir in "$ds"/*; do
            if [ -d "$dir" ]; then
                dirname=$(basename "$dir")
                mkdir -p "$out_dir/$dirname"
                for file in "$dir"/*.tif; do
                    filename=$(basename "$file")
                    magick "$file" -gravity center -crop 293x293+0+0 +repage -compress Zstd "$out_dir/$dirname/$filename"
                done
            fi
        done
    fi
done
cd ..

echo "Converting to Zarr..."
# Cell painting
uv run tiff_to_zarr.py data/crop_cellpainting_256 data/crop_cellpainting_256.zarr -n 5

# Time series
for ds in data/crop_timeseries_*_293; do
    if [ -d "$ds" ]; then
        dsname=$(basename "$ds" | sed 's/^data\/crop_//; s/^crop_//; s/_293$//')
        out_zarr_dir="data/crop_${dsname}_293_zarrs"
        mkdir -p "$out_zarr_dir"
        for dir in "$ds"/*; do
            if [ -d "$dir" ]; then
                dirname=$(basename "$dir")
                uv run timeseries_to_zarr.py "$dir" "$out_zarr_dir/${dirname}.zarr"
            fi
        done
    fi
done

echo "Compressing..."
cd data
tar -czvf ../files_to_upload/aliby_test_dataset.tar.gz crop* > /dev/null
tar -czvf ../files_to_upload/aliby_full_dataset.tar.gz full_* > /dev/null
cd ..

echo "Done."
