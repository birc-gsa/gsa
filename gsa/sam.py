import typing


def sam_record(out: typing.TextIO,
               qname: str, rname: str,
               pos: int, cigar: str,
               read: str, qual: str) -> None:
    print(f"{qname}\t0\t{rname}\t{pos+1}\t0\t{cigar}\t*\t0\t0\t{read}\t{qual}",
          file=out)
