import random
import typing
import sys


def simulate_dna_string(n: int) -> str:
    return ''.join(random.choice("acbt") for _ in range(n))


def simulate_genome(k: int, n: int) -> dict[str, str]:
    genome: dict[str, str] = {}
    for i in range(k):
        genome[f"chrom{i}"] = simulate_dna_string(n)
    return genome


def mutate(x: str, e: int) -> str:
    seq: list[str] = list(x)
    for _ in range(e):
        mutation = random.randrange(3)
        position = random.randrange(len(seq))
        if mutation == 0:
            seq[position] = random.choice("acgt")
        elif mutation == 1:
            del seq[position]
        else:
            seq = seq[:position] + [random.choice("acgt")] + seq[position:]
    return ''.join(seq)


def sample_reads(genome: dict[str, str],
                 k: int, n: int, e: int,
                 ) -> typing.Iterator[str]:
    chromosomes = tuple[str](genome.keys())
    for _ in range(k):
        chrom: str = genome[random.choice(chromosomes)]
        if len(chrom) < n:
            print("Chromosomes are shorter than desired read lengths.")
            sys.exit(1)
        i = random.randrange(0, len(chrom)-n)
        yield mutate(chrom[i:i+n], e)
