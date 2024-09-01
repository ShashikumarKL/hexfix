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

