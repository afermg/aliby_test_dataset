#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy",
#     "tifffile",
#     "zarr",
#     "imagecodecs",
# ]
# ///
import os
import argparse
import glob
import re
import numpy as np
import tifffile
import zarr
from zarr.codecs import ZstdCodec

def main():
    parser = argparse.ArgumentParser(description="Convert timeseries TIFFs to 5D Zarr.")
    parser.add_argument("input_dir", help="Input directory containing TIFF files.")
    parser.add_argument("output_zarr", help="Output Zarr directory path.")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, "*.tif")) + glob.glob(os.path.join(args.input_dir, "*.tiff")))
    if not files:
        print(f"No files found in {args.input_dir}")
        return

    pattern = re.compile(r'(.*)_(\d+)_(.*)_(\d+)\.tiff?$')
    
    parsed = []
    times = set()
    channels = set()
    zs = set()
    
    for f in files:
        basename = os.path.basename(f)
        match = pattern.match(basename)
        if match:
            prefix, t, c, z = match.groups()
            times.add(t)
            channels.add(c)
            zs.add(z)
            parsed.append((t, c, z, f))
        else:
            print(f"File {basename} does not match expected pattern.")
            
    if not parsed:
        print("No valid files parsed.")
        return

    times = sorted(list(times))
    channels = sorted(list(channels))
    zs = sorted(list(zs))
    
    T = len(times)
    C = len(channels)
    Z = len(zs)
    
    sample = tifffile.imread(parsed[0][3])
    Y, X = sample.shape
    dtype = sample.dtype
    
    print(f"Creating Zarr array with shape (T={T}, C={C}, Z={Z}, Y={Y}, X={X})")
    
    root = zarr.group(store=args.output_zarr, overwrite=True, zarr_format=3)
    arr = root.create_array(
        "dataset",
        shape=(T, C, Z, Y, X),
        chunks=(1, 1, Z, Y, X),
        dtype=dtype,
        compressors=[ZstdCodec(level=3)]
    )
    
    for t_idx, t_val in enumerate(times):
        for c_idx, c_val in enumerate(channels):
            z_stack = np.zeros((Z, Y, X), dtype=dtype)
            for z_idx, z_val in enumerate(zs):
                fpath = next((p[3] for p in parsed if p[0] == t_val and p[1] == c_val and p[2] == z_val), None)
                if fpath:
                    z_stack[z_idx] = tifffile.imread(fpath)
            arr[t_idx, c_idx] = z_stack
            
    print(f"Saved timeseries dataset to {args.output_zarr}")

if __name__ == "__main__":
    main()
