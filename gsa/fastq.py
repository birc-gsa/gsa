import typing


def write_fastq(f: typing.TextIO, reads: typing.Iterator[str]) -> None:
    """Write reads to file in SimpleFASTQ format."""
    for i, read in enumerate(reads):
        print(f"@read{i}", file=f)
        print(read, file=f)
        # removed the following two lines to make the format "simple fastq"
        # print("+", file=f)
        # print("~" * len(read), file=f)


def scan_reads(f: typing.TextIO) -> typing.Iterator[tuple[str, str]]:
    """Read sequences from a SimpleFASTQ format."""
    # This is a fucking hack, but Python won't let you check for EOF
    # and when parsing four lines at a time, that makes things harder
    # than they have any good reason for being.
    itr = iter(f)
    try:
        while True:
            name = next(itr).strip()[1:]
            seq = next(itr).strip()
            # removed the next two lines to get "Simple FASTQ"
            # next(itr)
            # qual = next(itr).strip()
            yield name, seq
    except StopIteration:
        return
