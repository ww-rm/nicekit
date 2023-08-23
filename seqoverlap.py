__doc__ = """用于求两个序列文件的重叠区域

参数:
    --i1: 第一份输入文件路径
    --i2: 第二份输入文件路径
    --o1: 第一份输出文件路径, 和 i1 对应, 可选, 默认在 i1 文件名后缀前增加 "overlap"
    --o2: 第二份输出文件路径, 和 i2 对应, 可选, 默认在 i2 文件名后缀前增加 "overlap"
    --overlap: 两份文件的真正重叠区域输出文件路径, 可选, 默认 "overlap.txt"

备注:
    输入文件的前三列是 (chr, start, end)
        chr 只要是染色体唯一标识符就可以, 任何格式, 例如 3, chr3, Chrom3, 但是输入的两份文件要是同一种格式, 输出的文件也会是相同的格式;
        start 和 end 都是整数;
        后面可以跟若干的内容, 每一列用 \\t 作为分隔符

    输出文件的 o1 和 o2 格式与 i1 和 i2 完全一致, 只保留了产生重叠的行

    overlap 文件的格式是 (chr, start, end, length), 使用 \\t 作为分隔符

    所有文件均没有表头, 输入文件可以无序, 输出的文件都按升序排序

示例:
    python fileoverlap.py --i1 file1.txt --i2 file2.txt --o1 file1.overlap.txt --o2 file2.overlap.txt --overlap file1-file2.overlap.txt
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import *


def read_filedata(path, sep: str = "\t"):
    """
    Returns:
        chrom -> [(start, end, raw_content), ...]

    Note:
        First three col of file is (chr, start, end), followed by any content, using `sep` as separator.
    """

    data: Dict[str, List[Tuple[int, int, str]]] = {}

    with Path(path).open("r", encoding="utf8") as f:
        for line in f:
            row = line.strip().split(sep)
            if len(row) < 3:
                raise ValueError(f"{path}: Column count less than 3.")

            chrom = row[0]
            start = int(row[1])
            end = int(row[2])

            row = (start, end, line)

            if chrom not in data:
                data[chrom] = []
            data[chrom].append(row)

    for value in data.values():
        value.sort()

    return data


def write_filedata(data: Dict[str, List[Tuple[int, int, str]]], path):
    chroms = sorted(data.keys())
    with Path(path).open("w", encoding="utf8") as f:
        for k in chroms:
            f.writelines(line for _, _, line in data[k])


def chrom_overlap(chrom1: List[Tuple[int, int, str]], chrom2: List[Tuple[int, int, str]]):
    """
    Args:
        chrom_: Must be sorted by start.
    """
    chrom1_flag = [False] * len(chrom1)
    chrom2_flag = [False] * len(chrom2)
    _overlap_both: Set[Tuple[int, int]] = set()

    for i1, r1 in enumerate(chrom1):
        s1, e1, _ = r1
        for i2, r2 in enumerate(chrom2):
            s2, e2, _ = r2

            # [s2, e2, ..., s1, e1]
            if e2 < s1:
                continue

            # [s1, e1, ..., s2, e2]
            if e1 < s2:
                break

            s3 = max(s1, s2)
            e3 = min(e1, e2)

            chrom1_flag[i1] = True
            chrom2_flag[i2] = True
            _overlap_both.add((s3, e3))

    overlap1 = [row for flag, row in zip(chrom1_flag, chrom1) if flag]
    overlap2 = [row for flag, row in zip(chrom2_flag, chrom2) if flag]
    overlap_both = sorted(_overlap_both)

    return overlap1, overlap2, overlap_both


def data_overlap(data1: Dict[str, List[Tuple[int, int, str]]], data2: Dict[str, List[Tuple[int, int, str]]]):
    """Find overlap by chrom"""

    overlap1: Dict[str, List[Tuple[int, int, str]]] = {}
    overlap2: Dict[str, List[Tuple[int, int, str]]] = {}
    overlap_both: Dict[str, List[Tuple[int, int]]] = {}

    for k1, v1 in data1.items():
        for k2, v2 in data2.items():
            if k1 != k2:
                continue

            print(f"Find overlap for chrom {k1}")
            chr_overlap1, chr_overlap2, chr_overlap_both = chrom_overlap(v1, v2)

            overlap1[k1] = chr_overlap1
            overlap2[k1] = chr_overlap2
            overlap_both[k1] = chr_overlap_both

    return overlap1, overlap2, overlap_both


def write_overlapdata(data: Dict[str, List[Tuple[int, int]]], path, sep: str = "\t"):
    chroms = sorted(data.keys())
    with Path(path).open("w", encoding="utf8") as f:
        for k in chroms:
            for s, e in data[k]:
                line = f"{k}{sep}{s}{sep}{e}{sep}{e - s + 1}"
                print(line, sep=sep, file=f)


def make_overlap_file(path1, path2, path_overlap1, path_overlap2, path_overlap_both):
    def _count(_data): return sum(len(x) for x in _data.values())

    print(f"Read data1 from file: {path1}")
    data1 = read_filedata(path1)
    print(f"Data1 total count: {_count(data1)}")

    print(f"Read data2 from file: {path2}")
    data2 = read_filedata(path2)
    print(f"Data2 total count: {_count(data2)}")

    overlap1, overlap2, overlap_both = data_overlap(data1, data2)

    print(f"Data1 overlap total count: {_count(overlap1)}")
    print(f"Write data1 overlap to: {path_overlap1}")
    write_filedata(overlap1, path_overlap1)

    print(f"Data2 overlap total count: {_count(overlap2)}")
    print(f"Write data2 overlap to: {path_overlap2}")
    write_filedata(overlap2, path_overlap2)

    print(f"Overlap total count: {_count(overlap_both)}")
    print(f"Write overlap to: {path_overlap_both}")
    write_overlapdata(overlap_both, path_overlap_both)


if __name__ == "__main__":
    parser = ArgumentParser(usage=__doc__)

    parser.add_argument("--i1", type=str, required=True, help="第一份输入文件路径")
    parser.add_argument("--i2", type=str, required=True, help="第二份输入文件路径")

    parser.add_argument("--o1", type=str, default="", help="第一份文件输出路径")
    parser.add_argument("--o2", type=str, default="", help="第二份文件输出路径")
    parser.add_argument("--overlap", type=str, default="overlap.txt", help="重叠文件输出路径")

    args = parser.parse_args()

    path1 = Path(args.i1)
    path2 = Path(args.i2)

    if args.o1:
        path_overlap1 = Path(args.o1)
    else:
        path_overlap1 = path1.with_stem(f"{path1.stem}.overlap")

    if args.o2:
        path_overlap2 = Path(args.o2)
    else:
        path_overlap2 = path2.with_stem(f"{path2.stem}.overlap")

    path_overlap_both = Path(args.overlap)

    make_overlap_file(path1, path2, path_overlap1, path_overlap2, path_overlap_both)
