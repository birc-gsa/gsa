import typing

from . import fasta
from . import fastq
from . import simulate


def simulate_genome(k: int, n: int,
                    fastafile: typing.TextIO
                    ) -> None:
    genome = simulate.simulate_genome(k, n)
    fasta.write_fasta(fastafile, genome)


def simulate_reads(k: int, n: int, edits: int,
                   fastafile: typing.TextIO,
                   fastqfile: typing.TextIO
                   ) -> None:
    genome = fasta.read_fasta(fastafile)
    fastq.write_fastq(
        fastqfile,
        simulate.sample_reads(genome, k, n, edits)
    )
