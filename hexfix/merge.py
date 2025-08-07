"""Utilities for merging SREC files."""


def merge_srec_files(file1_name: str, file2_name: str, output_name: str) -> None:
    """Merge ``file1_name`` and ``file2_name`` into ``output_name``.

    The routine preserves the header from the first file and the termination
    record from the second file.
    """
    with open(file1_name, "r") as file1, open(file2_name, "r") as file2:
        file1_lines = file1.readlines()
        file2_lines = file2.readlines()

    # Remove the termination record from the first file if present
    if file1_lines and (file1_lines[-1].startswith("S9") or file1_lines[-1].startswith("S8")):
        file1_lines.pop(-1)

    # Remove header lines from the second file
    file2_lines_filtered = [line for line in file2_lines if not line.startswith("S0")]

    combined_lines = file1_lines + file2_lines_filtered

    # Append termination record from the second file if available
    termination_line = next((line for line in file2_lines if line.startswith("S8") or line.startswith("S9")), None)
    if termination_line:
        combined_lines.append(termination_line)

    with open(output_name, "w") as output_file:
        output_file.writelines(combined_lines)
