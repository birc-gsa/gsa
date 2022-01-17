"""Writing hits to "simple"-SAM format."""

import typing


def ssam_record(out: typing.TextIO,
                sname: str, rname: str,
                pos: int, cigar: str,
                read: str) -> None:
    """Write location of a match as simple-sam format.

    The "simple" SAM format is like the SAM format, except that we only
    write the fields we use in the GSA class, so we write tab-separated
    columns of sequence name, read name, position, cigar and read.
    """
    print(sname, rname, pos+1, cigar, read, sep='\t', file=out)
