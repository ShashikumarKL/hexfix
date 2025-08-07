import zlib

def parse_srec_line(line):
    """
    Parses an SREC line to extract tge record type, address, and data bytes.
    """
    if len(line)< 10 or not line.startswith('S'):
        return None, None, None

    try:
        record_type = line[0:2]
        byte_count = int(line[2:4], 16)
        address_length = {'S1': 4, 'S2': 6, 'S3': 8}.get(record_type, 0)
        address = int(line[4:4+address_length], 16)
        data = bytes.fromhex(line[4+address_length:-2])
        return record_type, address, data
    except ValueError:
        return None, None, None


def validate_srec_file(filename, fix: bool = False):
    """Validate checksums in an SREC file.

    Each line is parsed and the checksum is recomputed from the byte count,
    address bytes and data bytes. A list of line numbers with invalid
    checksums is returned. When ``fix`` is ``True`` the checksums in these
    lines are replaced with the recomputed values in the file on disk.

    Parameters
    ----------
    filename: str
        Path to the SREC file to validate.
    fix: bool, optional
        If ``True`` any checksum mismatches will be corrected in-place. The
        list of offending line numbers is still returned.
    """

    invalid_lines = []
    output_lines = []

    with open(filename, "r") as infile:
        lines = infile.readlines()

    for lineno, line in enumerate(lines, start=1):
        stripped = line.rstrip("\n")
        if not stripped.startswith("S") or len(stripped) < 4:
            output_lines.append(line)
            continue

        record_type = stripped[0:2]
        try:
            byte_count = int(stripped[2:4], 16)
        except ValueError:
            invalid_lines.append(lineno)
            output_lines.append(line)
            continue

        # Address length in bytes for common record types
        addr_len_map = {"S0": 2, "S1": 2, "S2": 3, "S3": 4, "S5": 2, "S7": 4, "S8": 3, "S9": 2}
        addr_len = addr_len_map.get(record_type, 0)
        addr_hex_len = addr_len * 2

        try:
            addr_bytes = bytes.fromhex(stripped[4:4 + addr_hex_len])
            data_bytes = bytes.fromhex(stripped[4 + addr_hex_len:-2])
            stored_checksum = int(stripped[-2:], 16)
        except ValueError:
            invalid_lines.append(lineno)
            output_lines.append(line)
            continue

        calc_checksum = (~(byte_count + sum(addr_bytes) + sum(data_bytes)) & 0xFF)

        if calc_checksum != stored_checksum:
            invalid_lines.append(lineno)
            if fix:
                fixed_line = stripped[:-2] + f"{calc_checksum:02X}\n"
                output_lines.append(fixed_line)
            else:
                output_lines.append(line)
        else:
            output_lines.append(line)

    if fix and invalid_lines:
        with open(filename, "w") as outfile:
            outfile.writelines(output_lines)

    return invalid_lines

def crc32_for_address_range(srec_filename, start_address, end_address):
    """
    Calculates the CRC32 checksum from data records within a specified range in an SREC file.

    :param srec_filename: Path to the SREC file
    :param start_address: Starting byte address (inclusive)
    :param end_address: Ending byte address (exclusive)
    :return: CRC32 checksum
    """
    checksum = 0
    
    with open(srec_filename, 'r') as file:
        for line in file:
            record_type, address, data = parse_srec_line(line.strip())
            
            if record_type in ['S1', 'S2', 'S3']:
                record_end_address = address + len(data) - 1
                
                # Check if the record is completely outside the range of interest
                if record_end_address < start_address or address > end_address:
                    continue
                
                # Trim data to the specified range
                if address < start_address:
                    # Trim the beginning of the data
                    offset = start_address - address
                    data = data[offset:]
                    address = start_address
                
                if record_end_address > end_address:
                    # Trim the end of the data
                    offset = record_end_address - end_address
                    data = data[:-offset]
                
                # Update checksum with the relevant part of the data
                checksum = zlib.crc32(data, checksum)
    
    return checksum & 0xFFFFFFFF

