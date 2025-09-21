import argparse
import os
import zlib

def compress_file(input_file, output_file, noreplace):
    if noreplace and os.path.exists(output_file):
        print(f"[!] {output_file} exists, skipping (use without --noreplace to overwrite).")
        return

    with open(input_file, "rb") as f:
        data = f.read()
    compressed = zlib.compress(data, level=9)

    if os.path.exists(output_file) and not noreplace:
        os.remove(output_file)

    with open(output_file, "wb") as f:
        f.write(compressed)

    os.remove(input_file)  # delete original
    print(f"[+] Compressed {input_file} -> {output_file} (source deleted)")

def decompress_file(input_file, output_file, noreplace):
    if noreplace and os.path.exists(output_file):
        print(f"[!] {output_file} exists, skipping (use without --noreplace to overwrite).")
        return

    with open(input_file, "rb") as f:
        data = f.read()
    decompressed = zlib.decompress(data)

    if os.path.exists(output_file) and not noreplace:
        os.remove(output_file)

    with open(output_file, "wb") as f:
        f.write(decompressed)

    os.remove(input_file)  # delete original
    print(f"[+] Decompressed {input_file} -> {output_file} (source deleted)")

def transform_file(input_file, noreplace):
    base, ext = os.path.splitext(input_file)
    if ext == ".txt":
        output_file = base + ".rx"
    elif ext == ".rx":
        output_file = base + ".txt"
    else:
        print(f"[!] {input_file} is not .txt or .rx")
        return

    if noreplace and os.path.exists(output_file):
        print(f"[!] {output_file} exists, skipping (use without --noreplace to overwrite).")
        return

    if os.path.exists(output_file) and not noreplace:
        os.remove(output_file)

    os.rename(input_file, output_file)  # this deletes the old automatically
    print(f"[+] Transformed {input_file} -> {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Gears file format tool (.rx, .rxc)")
    subparsers = parser.add_subparsers(dest="command")

    # Compress
    compress_parser = subparsers.add_parser("compress", help="Compress .txt or .rx into .rxc")
    compress_parser.add_argument("files", nargs="+", help="Files to compress")
    compress_parser.add_argument("--batch", action="store_true", help="Batch mode")
    compress_parser.add_argument("--noreplace", action="store_true", help="Skip if output exists")

    # Decompress
    decompress_parser = subparsers.add_parser("decompress", help="Decompress .rxc into .rx or .txt")
    decompress_parser.add_argument("files", nargs="+", help="Files to decompress")
    decompress_parser.add_argument("--txt", action="store_true", help="Decompress to .txt instead of .rx")
    decompress_parser.add_argument("--batch", action="store_true", help="Batch mode")
    decompress_parser.add_argument("--noreplace", action="store_true", help="Skip if output exists")

    # Transform
    transform_parser = subparsers.add_parser("transform", help="Transform .txt <-> .rx")
    transform_parser.add_argument("files", nargs="+", help="Files to transform")
    transform_parser.add_argument("--batch", action="store_true", help="Batch mode")
    transform_parser.add_argument("--noreplace", action="store_true", help="Skip if output exists")

    args = parser.parse_args()

    if args.command == "compress":
        for file in args.files:
            if not os.path.exists(file):
                print(f"[!] {file} not found")
                continue
            base, ext = os.path.splitext(file)
            if ext not in [".txt", ".rx"]:
                print(f"[!] {file} must be .txt or .rx")
                continue
            output_file = base + ".rxc"
            compress_file(file, output_file, args.noreplace)

    elif args.command == "decompress":
        for file in args.files:
            if not os.path.exists(file):
                print(f"[!] {file} not found")
                continue
            base, _ = os.path.splitext(file)
            output_file = base + (".txt" if args.txt else ".rx")
            decompress_file(file, output_file, args.noreplace)

    elif args.command == "transform":
        for file in args.files:
            if not os.path.exists(file):
                print(f"[!] {file} not found")
                continue
            transform_file(file, args.noreplace)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
