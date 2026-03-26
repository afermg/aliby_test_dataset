#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy",
#     "tifffile",
#     "zarr",
# ]
# ///
import os
import argparse
import glob
import numpy as np
import tifffile
import zarr
from zarr.codecs import BytesCodec, ZstdCodec


def get_common_name(filenames):
    basenames = [os.path.basename(f) for f in filenames]
    names_no_ext = [os.path.splitext(b)[0] for b in basenames]
    if len(names_no_ext) == 1:
        return names_no_ext[0]

    prefix = os.path.commonprefix(names_no_ext)
    reversed_names = [name[::-1] for name in names_no_ext]
    suffix = os.path.commonprefix(reversed_names)[::-1]

    if len(prefix) + len(suffix) >= len(names_no_ext[0]):
        return prefix
    return prefix + suffix


def main():
    parser = argparse.ArgumentParser(
        description="Convert a folder of TIFFs to a Zarr directory."
    )
    parser.add_argument("input_dir", help="Input directory containing TIFF files.")
    parser.add_argument("output_zarr", help="Output Zarr directory path.")
    parser.add_argument(
        "-n",
        "--n-files",
        type=int,
        required=True,
        help="Number of files per array group.",
    )
    args = parser.parse_args()

    search_pattern1 = os.path.join(args.input_dir, "*.tif")
    search_pattern2 = os.path.join(args.input_dir, "*.tiff")
    files = sorted(glob.glob(search_pattern1) + glob.glob(search_pattern2))

    if not files:
        print(f"No TIFF files found in {args.input_dir}")
        return

    print(f"Found {len(files)} files in {args.input_dir}.")

    sample = tifffile.imread(files[0])
    h, w = sample.shape
    dtype = sample.dtype

    num_groups = len(files) // args.n_files
    remainder = len(files) % args.n_files
    total_groups = num_groups + (1 if remainder else 0)

    print(f"Grouping into {total_groups} arrays (N={args.n_files}).")

    root = zarr.group(store=args.output_zarr, overwrite=True, zarr_format=3)

    for i in range(total_groups):
        group_files = files[i * args.n_files : (i + 1) * args.n_files]
        current_n = len(group_files)
        group_name = get_common_name(group_files)

        arr = np.zeros((current_n, h, w), dtype=dtype)
        for j, f in enumerate(group_files):
            arr[j] = tifffile.imread(f)

        root.create_array(
            group_name,
            data=arr,
            chunks=(current_n, h, w),
            compressors=[ZstdCodec(level=3)],
        )
        print(
            f"Saved array '{group_name}' of shape {arr.shape} inside {args.output_zarr}"
        )


if __name__ == "__main__":
    main()
