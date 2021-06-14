import typing


def break_lines(x: str, linewidth: int = 80) -> typing.Iterator[str]:
    for i in range(0, len(x), linewidth):
        yield x[i:i+linewidth]


def write_fasta(
    f: typing.TextIO,
    chromosomes: dict[str, str]
) -> None:
    for chrom, seq in chromosomes.items():
        print(f">{chrom}", file=f)
        for line in break_lines(seq):
            print(line, file=f)


def read_fasta(f: typing.TextIO) -> dict[str, str]:
    # This is a bit flaky of a fasta parser, but it is okay
    # for this class...
    genome: dict[str, str] = {}
    chromosomes = f.read().split('>')
    for i in range(1, len(chromosomes)):
        name, *seq = chromosomes[i].split()
        genome[name] = ''.join(seq)
    return genome
