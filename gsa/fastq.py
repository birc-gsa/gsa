import typing


def write_fastq(f: typing.TextIO, reads: typing.Iterator[str]) -> None:
    for i, read in enumerate(reads):
        print(f"@read{i}", file=f)
        print(read, file=f)
        print("+", file=f)
        print("~" * len(read), file=f)
