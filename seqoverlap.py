__version__ = "v1.0.2"

__doc__ = """用于求两个序列文件的重叠区域

参数:
    --i1: 第一份输入文件路径
    --i2: 第二份输入文件路径
    --o1: 第一份输出文件路径, 和 i1 对应, 可选, 默认在 i1 文件名后缀前增加 "overlap"
    --o2: 第二份输出文件路径, 和 i2 对应, 可选, 默认在 i2 文件名后缀前增加 "overlap"
    --overlap: 两份文件的真正重叠区域输出文件路径, 可选, 默认 "overlap.txt"

    --sep: 列分隔符, 默认为制表符 "\\t"
    --merge-sep: 合并列的列内分隔符, 默认为分号 ";"

备注:
    输入文件的前三列是 (chr, start, end)
        chr 只要是染色体唯一标识符就可以, 任何格式, 例如 3, chr3, Chrom3, 但是输入的两份文件要是同一种格式, 输出的文件也会是相同的格式;
        start 和 end 都是整数;
        后面可以跟若干的内容, 每一列用分隔符分隔

    输出文件的 o1 和 o2 格式与 i1 和 i2 完全一致, 保留了产生重叠的行, 并且追加了另一分文件产生交集的行

    overlap 文件的格式是 (chr, start, end, length), 使用指定分隔符分隔

    所有文件均没有表头, 输入文件可以无序, 同一个染色体内的行允许有区间重叠, 输出的文件都按升序排序

示例:
    python fileoverlap.py --i1 file1.txt --i2 file2.txt --o1 file1.overlap.txt --o2 file2.overlap.txt --overlap file1-file2.overlap.txt
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Set, Tuple

ChromData = List[Tuple[int, int, List[str]]]


class SequenceOverlapFinder:
    def __init__(self, sep: str = "\t", merge_sep: str = ",", comment_prefix: Tuple[str] = ("#", )):
        self.sep = sep
        self.comment_prefix = comment_prefix
        self.merge_sep = merge_sep

    def read_filedata(self, path) -> Dict[str, ChromData]:
        """读取文件数据, 并按区间排序, 同一份文件的区间允许存在重叠, 并且不需要排序.

        前三列必定是 (chr, start, end), 后跟任意列数据, 列使用 `sep` 作为分隔符.

        Returns:
            chrom -> [(start, end, list_of_other_columns), ...]
        """

        data: Dict[str, ChromData] = {}

        with Path(path).open("r", encoding="utf8") as f:
            for line in f:
                line = line.lstrip()
                if line.startswith(self.comment_prefix):
                    continue

                row = line.strip().split(self.sep)
                if len(row) < 3:
                    raise ValueError(f"{path}: 数据少于 3 列.")

                chrom = row[0]
                start = int(row[1])
                end = int(row[2])

                row = (start, end, row[3:])  # 保留内容

                if chrom not in data:
                    data[chrom] = []
                data[chrom].append(row)

        for value in data.values():
            value.sort()

        return data

    def write_filedata(self, data: Dict[str, ChromData], path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf8") as f:
            for chrom in sorted(data.keys()):
                for start, end, row in data[chrom]:
                    print(chrom, start, end, *row, sep=self.sep, file=f)

    def chrom_overlap(self, chrom1: ChromData, chrom2: ChromData):
        """对同染色体数据求解交集

        Args:
            chrom_: 必须按 start 排好序.

        Returns:
            chrom1_hit: chrom1 每个区间与 chrom2 存在交集的 chrom2 区间索引
            chrom2_hit: chrom2 每个区间与 chrom1 存在交集的 chrom1 区间索引
            overlap_both: 共同区间
        """

        # 记录与交集的对方索引
        chrom1_hit = [[] for _ in range(len(chrom1))]
        chrom2_hit = [[] for _ in range(len(chrom2))]

        # 两份的共同交集
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

                chrom1_hit[i1].append(i2)
                chrom2_hit[i2].append(i1)
                _overlap_both.add((s3, e3))

        overlap_both = sorted(_overlap_both)

        return chrom1_hit, chrom2_hit, overlap_both

    def data_overlap(self, data1: Dict[str, ChromData], data2: Dict[str, ChromData]):
        """查找每个染色体的交集"""

        overlap1: Dict[str, ChromData] = {}
        overlap2: Dict[str, ChromData] = {}
        overlap_both: Dict[str, List[Tuple[int, int]]] = {}

        def get_chrom_data(chr_hit_1, chr_data_1, chr_data_2) -> ChromData:
            chr_data = []
            for i1, hits in enumerate(chr_hit_1):
                if len(hits) <= 0:
                    continue
                start, end, rest_columns_1 = chr_data_1[i1]
                start_2 = self.merge_sep.join(map(str, (chr_data_2[i2][0] for i2 in hits)))
                end_2 = self.merge_sep.join(map(str, (chr_data_2[i2][1] for i2 in hits)))
                rest_columns_2 = [self.merge_sep.join(v) for v in zip(*(chr_data_2[i2][2] for i2 in hits))]
                chr_data.append([start, end, [*rest_columns_1, start_2, end_2, *rest_columns_2]])
            return chr_data

        for k1, v1 in data1.items():
            for k2, v2 in data2.items():
                if k1 != k2:
                    continue

                print(f"正在查找染色体 {k1} 交集")
                chr_hit1, chr_hit2, chr_overlap_both = self.chrom_overlap(v1, v2)

                overlap1[k1] = get_chrom_data(chr_hit1, v1, v2)
                overlap2[k1] = get_chrom_data(chr_hit2, v2, v1)
                overlap_both[k1] = chr_overlap_both

        return overlap1, overlap2, overlap_both

    def write_overlapdata(self, data: Dict[str, List[Tuple[int, int]]], path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf8") as f:
            for chrom in sorted(data.keys()):
                for s, e in data[chrom]:
                    print(chrom, s, e, e - s + 1, sep=self.sep, file=f)

    def make_overlap_file(self, path1, path2, path_overlap1, path_overlap2, path_overlap_both):
        def _count(_data): return sum(len(x) for x in _data.values())

        print(f"读取数据文件 1: {path1}")
        data1 = self.read_filedata(path1)
        print(f"数据 1 总行数: {_count(data1)}")

        print(f"读取数据文件 2: {path2}")
        data2 = self.read_filedata(path2)
        print(f"数据 2 总行数: {_count(data2)}")

        overlap1, overlap2, overlap_both = self.data_overlap(data1, data2)

        print(f"数据 1 交集总行数: {_count(overlap1)}")
        self.write_filedata(overlap1, path_overlap1)
        print(f"数据 1 已写入: {path_overlap1}")

        print(f"数据 2 交集总行数: {_count(overlap2)}")
        self.write_filedata(overlap2, path_overlap2)
        print(f"数据 2 已写入: {path_overlap2}")

        print(f"交集总行数: {_count(overlap_both)}")
        self.write_overlapdata(overlap_both, path_overlap_both)
        print(f"数据交集已写入: {path_overlap_both}")


if __name__ == "__main__":
    parser = ArgumentParser(usage=__doc__)

    parser.add_argument("--i1", type=str, required=True, help="第一份输入文件路径")
    parser.add_argument("--i2", type=str, required=True, help="第二份输入文件路径")

    parser.add_argument("--o1", type=str, default="", help="第一份文件输出路径")
    parser.add_argument("--o2", type=str, default="", help="第二份文件输出路径")
    parser.add_argument("--overlap", type=str, default="overlap.txt", help="重叠文件输出路径")

    parser.add_argument("--sep", type=str, default="\t", help="列分隔符")
    parser.add_argument("--merge-sep", type=str, default=";", help="合并列列内分隔符")
    parser.add_argument("--comment-prefix", type=str, default=("#",), help="行首注释符", nargs="+")

    args = parser.parse_args()

    path1 = Path(args.i1)
    path2 = Path(args.i2)

    if args.o1:
        path_overlap1 = Path(args.o1)
    else:
        path_overlap1 = path1.with_name(f"{path1.stem}.overlap{path1.suffix}")

    if args.o2:
        path_overlap2 = Path(args.o2)
    else:
        path_overlap2 = path2.with_name(f"{path2.stem}.overlap{path2.suffix}")

    path_overlap_both = Path(args.overlap)

    finder = SequenceOverlapFinder(args.sep, args.merge_sep, args.comment_prefix)
    finder.make_overlap_file(path1, path2, path_overlap1, path_overlap2, path_overlap_both)
