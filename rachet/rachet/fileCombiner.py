import os

FILES_TO_COMBINE = [
    "commands/cmd_os.py",
    "commands/cmd_print.py"
    "commands/cmd_input.py"
    "commands/cmd_pause.py",
    "main.rx",
    "compiler.py",
    "lexer.py",
    "linker.ld",
    "linker.py",
    "parser.py",
    "runtimes/bootloader.asm",
    "runtimes/kernel.asm",
]

OUTPUT_FILE = "combined.txt"


def generate_file_tree(root_dir: str) -> str:
    """
    Generate a file tree string starting from root_dir.
    Uses ├── and └── for nice tree visualization.
    """
    tree_lines = []

    for current_root, dirs, files in os.walk(root_dir):
        # Determine depth and indent
        level = current_root.replace(root_dir, "").count(os.sep)
        indent = "│   " * level

        if current_root != root_dir:
            tree_lines.append(f"{indent}└── {os.path.basename(current_root)}")

        sub_indent = indent + "│   " if current_root != root_dir else ""
        for idx, f in enumerate(sorted(files)):
            prefix = "└── " if idx == len(files) - 1 else "├── "
            tree_lines.append(f"{sub_indent}{prefix}{f}")

    return "\n".join(tree_lines)


def combine_files(base_dir: str, files: list[str], output_path: str):
    """
    Combine the listed files into one text file.
    Each file's contents are preceded by '#<filename>' and separated by blank lines.
    """
    with open(output_path, "w", encoding="utf-8") as out:
        # Write file tree first
        out.write("# File Tree\n")
        out.write(generate_file_tree(base_dir))
        out.write("\n\n")

        for rel_path in files:
            file_path = os.path.join(base_dir, rel_path)
            if not os.path.exists(file_path):
                out.write(f"# {rel_path} (MISSING)\n\n")
                continue

            out.write(f"# {rel_path}\n")
            with open(file_path, "r", encoding="utf-8") as f:
                out.write(f.read())
            out.write("\n\n")


if __name__ == "__main__":
    base_directory = os.path.dirname(os.path.abspath(__file__))
    output_file_path = os.path.join(base_directory, OUTPUT_FILE)
    combine_files(base_directory, FILES_TO_COMBINE, output_file_path)
    print(f"Combined file written to {output_file_path}")