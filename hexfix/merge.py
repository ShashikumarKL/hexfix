def merge_srec_files(file1_name, file2_name, output_name):
      """
    Merge two SREC files into  one file.
    """
    with open(file1_name, 'r') as file1, open(file2_name, 'r') as file2:
        file1_lines = file1.readlines()
        file2_lines = file2.readlines()

    # Remove the End of line from the first file(s9 ar s8 record)
    if file1_lines[-1].startswith('S9') or file1_lines[-1].startswith('S8'):
        file1_lines.pop(-1)

    # Remove the Header lines from the second file except teh first one
    file2_lines_filtered = [line for line in file2_lines if not line.startswith('S0')]

    combined_lines = file1_lines + file2_lines_filtered

    # Add the  End of Line from file2 to combined files
    termination_line =  next((line for line in file2_lines if line.startswith('S8') or line.startswith('S9')), None)
    if termination_line:
        combined_lines.append(termination_line)

    # Write the combined content to new file
    with open(output_name, 'w') as output_file:
        output_file.writelines(combined_lines)
        print(f"File {file1_name} has merged with {file2_name} and saved as {output_name}")
