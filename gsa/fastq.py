import typing


def write_fastq(f: typing.TextIO, reads: typing.Iterator[str]) -> None:
    for i, read in enumerate(reads):
        print(f"@read{i}", file=f)
        print(read, file=f)
        print("+", file=f)
        print("~" * len(read), file=f)


def scan_reads(f: typing.TextIO) -> typing.Iterator[tuple[str, str, str]]:
    # This is a fucking hack, but Python won't let you check for EOF
    # and when parsing four lines at a time, that makes things harder
    # than they have any good reason for being.
    itr = iter(f)
    try:
        while True:
            name = next(itr).strip()[1:]
            seq = next(itr).strip()
            next(itr)
            qual = next(itr).strip()
            yield name, seq, qual
    except StopIteration:
        return
