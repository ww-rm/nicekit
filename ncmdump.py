# -*- coding: UTF-8 -*-

import imghdr
import json
import mimetypes
from argparse import ArgumentParser
from base64 import b64decode
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import List, Union
from urllib import request

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from mutagen import flac, id3, mp3
from PIL import Image
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn


class NCMRC4:
    """RC4 for ncm file."""

    def __init__(self, key: bytes) -> None:
        """
        Args:
            key (bytes): RC4 key bytes
        """

        self._key = key
        self._s_box = bytearray(range(256))
        self._key_box = bytearray(256)
        self._key_pos = 0

        # standard RC4 init
        j = 0
        for i in range(256):
            j = (j + self._s_box[i] + self._key[i % len(self._key)]) & 0xFF
            self._s_box[i], self._s_box[j] = self._s_box[j], self._s_box[i]

        # non-standard keybox generate
        for i in range(256):
            j = (i + 1) & 0xFF
            s_j = self._s_box[j]
            s_jj = self._s_box[(s_j + j) & 0xFF]
            self._key_box[i] = self._s_box[(s_jj + s_j) & 0xFF]

    def decrypt(self, ciphertext: bytes) -> bytes:
        """decrypt

        Args:
            ciphertext (bytes): btyes to be decrypted
        """

        plaintext = bytearray()
        for b in ciphertext:
            plaintext.append(b ^ self._key_box[self._key_pos])
            if self._key_pos >= 255:
                self._key_pos = 0
            else:
                self._key_pos += 1
        return bytes(plaintext)


class NeteaseCloudMusicFile:
    """ncm file"""

    MAGIC_HEADER = b"CTENFDAM"

    AES_KEY_RC4_KEY = bytes.fromhex("687A4852416D736F356B496E62617857")
    RC4_KEY_XORBYTE = 0x64

    AES_KEY_METADATA = bytes.fromhex("2331346C6A6B5F215C5D2630553C2728")
    METADATA_XORBYTE = 0x63

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def file_type(self) -> str:
        """`flac` or `mp3`"""
        return self._metadata.get("format", "")

    @property
    def id(self) -> int:
        return self._metadata.get("musicId", -1)

    @property
    def name(self) -> str:
        return self._metadata.get("musicName", "")

    @property
    def artists(self) -> List[str]:
        return [a[0] for a in self._metadata.get("artist", [])]

    @property
    def album(self) -> str:
        return self._metadata.get("album", "")

    @property
    def cover_data(self) -> bytes:
        return self._cover_data

    @property
    def cover_suffix(self) -> str:
        return f".{imghdr.what(None, self._cover_data[:32])}"

    @property
    def cover_mime(self) -> str:
        return mimetypes.types_map.get(self.cover_suffix, "")

    def __init__(self, path: Union[str, PathLike]) -> None:
        """
        Args:
            path (str or PathLike): ncm file path
        """

        self._path = Path(path)
        self._parse()

    def _parse(self) -> None:
        """parse file."""

        with self._path.open("rb") as ncmfile:
            self._hdr = ncmfile.read(8)

            if self._hdr != self.MAGIC_HEADER:
                raise TypeError(f"{self._path} is not a valid ncm file.")

            # XXX: 2 bytes unknown
            self._gap1 = ncmfile.read(2)

            self._rc4_key_enc_size = int.from_bytes(ncmfile.read(4), "little")
            self._rc4_key_enc = ncmfile.read(self._rc4_key_enc_size)
            self._rc4_key = b""

            self._metadata_enc_size = int.from_bytes(ncmfile.read(4), "little")
            self._metadata_enc = ncmfile.read(self._metadata_enc_size)
            self._metadata = {}

            # XXX: 9 bytes unknown
            self._crc32 = int.from_bytes(ncmfile.read(4), "little")
            self._gap2 = ncmfile.read(5)

            self._cover_data_size = int.from_bytes(ncmfile.read(4), "little")
            self._cover_data = ncmfile.read(self._cover_data_size)

            self._music_data_enc = ncmfile.read()
            self._music_data = b""

    def _decrypt_rc4_key(self) -> None:
        """
        Attributes:
            self._rc4_key: bytes
        """

        cryptor = AES.new(self.AES_KEY_RC4_KEY, AES.MODE_ECB)

        rc4_key = bytes(map(lambda b: b ^ self.RC4_KEY_XORBYTE, self._rc4_key_enc))
        rc4_key = unpad(cryptor.decrypt(rc4_key), len(self.AES_KEY_RC4_KEY), "pkcs7")

        self._rc4_key = rc4_key.lstrip(b"neteasecloudmusic")

    def _decrypt_metadata(self) -> None:
        """
        Attributes:
            self._metadata: dict

        ```json
        {
            "format": "flac", 
            "musicId": 431259256, 
            "musicName": "カタオモイ", 
            "artist": [["Aimer", 16152]], 
            "album": "daydream", 
            "albumId": 34826361, 
            "albumPicDocId": 109951165052089697, 
            "albumPic": "http://p1.music.126.net/2QRYxUqXfW0zQpm2_DVYRA==/109951165052089697.jpg", 
            "mvId": 0, 
            "flag": 4, 
            "bitrate": 876923, 
            "duration": 207866, 
            "alias": [], 
            "transNames": ["单相思"]
        }
        ```
        """

        # if no metadata
        if self._metadata_enc_size <= 0:
            self._metadata = {}

        else:
            cryptor = AES.new(self.AES_KEY_METADATA, AES.MODE_ECB)

            metadata = bytes(map(lambda b: b ^ self.METADATA_XORBYTE, self._metadata_enc))

            metadata = b64decode(metadata.lstrip(b"163 key(Don't modify):"))
            metadata = unpad(cryptor.decrypt(metadata), len(self.AES_KEY_METADATA), "pkcs7")

            self._metadata: dict = json.loads(metadata.lstrip(b"music:"))

            # if no cover data, try get cover data by url in metadata
            if self._cover_data_size <= 0:
                try:
                    with request.urlopen(self._metadata.get("albumPic", "")) as res:
                        if res.status < 400:
                            self._cover_data = res.read()
                            self._cover_data_size = len(self._cover_data)
                except:
                    pass

    def _decrypt_music_data(self) -> None:
        """
        Attributes:
            self._music_data: bytes
        """

        cryptor = NCMRC4(self._rc4_key)
        self._music_data = cryptor.decrypt(self._music_data_enc)

    def decrypt(self) -> "NeteaseCloudMusicFile":
        """Decrypt all data.

        Returns:
            self
        """

        self._decrypt_rc4_key()
        self._decrypt_metadata()
        self._decrypt_music_data()

        return self

    def dump_metadata(self, path: Union[str, PathLike], suffix: str = ".json") -> Path:
        """Dump metadata.

        Args:
            path (str or PathLike): path to dump.
            suffix (str): suffix for path, default to `.json`

        Returns:
            Path: path dumped.
        """

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        path = path.with_suffix(suffix)
        path.write_text(json.dumps(self._metadata, ensure_ascii=False, indent=4), "utf8")
        return path

    def dump_cover(self, path: Union[str, PathLike]) -> Path:
        """Dump cover image.

        Args:
            path (str or PathLike): path to dump.

        Returns:
            Path: path dumped.

        Note:
            If no cover data found, an empty file will be dumped, with same file stem and `None` suffix.
        """

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        path = path.with_suffix(self.cover_suffix)
        path.write_bytes(self._cover_data)
        return path

    def _dump_music(self, path: Union[str, PathLike]) -> Path:
        """Dump music without any other info."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        path = path.with_suffix(f".{self.file_type}")
        path.write_bytes(self._music_data)
        return path

    def _addinfomp3(self, path: Union[str, PathLike]) -> None:
        """Add info for mp3 format."""

        audio = mp3.MP3(path)

        audio["TIT2"] = id3.TIT2(text=self.name, encoding=id3.Encoding.UTF8)  # title
        audio["TALB"] = id3.TALB(text=self.album, encoding=id3.Encoding.UTF8)  # album
        audio["TPE1"] = id3.TPE1(text="/".join(self.artists), encoding=id3.Encoding.UTF8)  # artists
        audio["TPE2"] = id3.TPE2(text="/".join(self.artists), encoding=id3.Encoding.UTF8)  # album artists

        if self._cover_data_size > 0:
            audio["APIC"] = id3.APIC(type=id3.PictureType.COVER_FRONT, mime=self.cover_mime, data=self._cover_data)  # cover

        audio.save()

    def _addinfoflac(self, path: Union[str, PathLike]) -> None:
        """Add info for flac format."""

        audio = flac.FLAC(path)

        # add music info
        audio["title"] = self.name
        audio["artist"] = self.artists
        audio["album"] = self.album
        audio["albumartist"] = "/".join(self.artists)

        # add cover
        if self._cover_data_size > 0:
            cover = flac.Picture()
            cover.type = id3.PictureType.COVER_FRONT
            cover.data = self._cover_data

            with BytesIO(self._cover_data) as data:
                with Image.open(data) as f:
                    cover.mime = self.cover_mime
                    cover.width = f.width
                    cover.height = f.height
                    cover.depth = len(f.getbands()) * 8

            audio.add_picture(cover)

        audio.save()

    def dump_music(self, path: Union[str, PathLike]) -> Path:
        """Dump music with metadata and cover.

        Args:
            path (str or PathLike): path to dump.

        Returns:
            Path: path dumped.

        Raises:
            NotImplementedError: If there are some unknown file types, it will only dump music data without music info.
        """

        path = self._dump_music(path)

        if self.file_type == "flac":
            self._addinfoflac(path)
        elif self.file_type == "mp3":
            self._addinfomp3(path)
        else:
            raise NotImplementedError(f"Unknown file type '{self.file_type}', failded to add music info.")

        return path


if __name__ == "__main__":
    parser = ArgumentParser("ncmdump", description="Dump ncm files with progress bar and logging info, only process files with suffix '.ncm'")
    parser.add_argument("files", nargs="*", help="Files to dump, can follow multiple files.")
    parser.add_argument("--in-folder", help="Input folder of files to dump.")
    parser.add_argument("--out-folder", help="Output folder of files dumped.", default=".")

    parser.add_argument("--dump-metadata", help="Whether dump metadata.", action="store_true")
    parser.add_argument("--dump-cover", help="Whether dump album cover.", action="store_true")

    args = parser.parse_args()

    out_folder = Path(args.out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)

    dump_metadata = args.dump_metadata
    dump_cover = args.dump_cover

    files = args.files
    if args.in_folder:
        files.extend(Path(args.in_folder).iterdir())
    files = list(filter(lambda p: p.suffix == ".ncm", map(Path, files)))

    if not files:
        parser.print_help()
    else:
        with Progress(SpinnerColumn(), *Progress.get_default_columns(), TimeElapsedColumn()) as progress:
            task = progress.add_task("[#d75f00]Dumping files", total=len(files))

            for ncm_path in files:
                output_path = out_folder.joinpath(ncm_path.stem)

                try:
                    ncmfile = NeteaseCloudMusicFile(ncm_path).decrypt()
                    music_path = ncmfile.dump_music(output_path)

                    if dump_metadata:
                        ncmfile.dump_metadata(output_path)
                    if dump_cover:
                        ncmfile.dump_cover(output_path)

                except Exception as e:
                    progress.log(f"[red]ERROR[/red]: {ncm_path} -> {e}")

                else:
                    if not ncmfile.metadata:
                        progress.log(f"[yellow]WARNING[/yellow]: {ncm_path} -> {music_path}, no metadata found")
                    if not ncmfile.cover_data:
                        progress.log(f"[yellow]WARNING[/yellow]: {ncm_path} -> {music_path}, no cover data found")

                finally:
                    progress.advance(task)
