# -*- coding: UTF-8 -*-

import logging
import math
import os
from argparse import ArgumentParser
from functools import wraps
from pathlib import Path
from time import sleep
from typing import Tuple, Union
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm


def empty_retry(times: int = 3, interval: float = 1):
    """Retry when a func returns empty

    Args:
        times (int): Times to retry.
        interval (float): Interval between each retry, in seconds.
    """
    def decorator(func):
        @wraps(func)
        def decorated_func(*args, **kwargs):
            for i in range(times + 1):
                # retry log
                if i > 0:
                    logging.getLogger(__name__).warning("Retry func {} {} time.".format(func.__name__, i))

                # call func
                ret = func(*args, **kwargs)
                if ret:
                    return ret

                # sleep for interval
                sleep(interval)

            # all retry failed
            logging.getLogger(__name__).error("All retries failed in func {}.".format(func.__name__))
            return ret
        return decorated_func
    return decorator


class XSession(requests.Session):
    """A wrapper class for `requests.Session`, can log info.

    If anything wrong happened in a request, return an empty `Response` object, keeping url info and logging error info using `logging` module.
    """

    def __init__(self) -> None:
        """
        Properties:
            interval (float): Seconds between each request. Minimum to 0.01. Default to 0.01
            max_retries (int): max retry times. Default to 3.
            timeout: same as timeout param to `requests.request`, default to 30.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.interval = 1
        self.timeout = 30
        self.max_retries = 3

    @property
    def interval(self):
        return self.__interval

    @interval.setter
    def interval(self, value: float):
        self.__interval = max(0.01, value)

    @property
    def timeout(self):
        return self.__timeout

    @timeout.setter
    def timeout(self, value: Union[Tuple[float, float], float]):
        self.__timeout = value

    @property
    def max_retries(self):
        return self.__max_retries

    @max_retries.setter
    def max_retries(self, value: int):
        self.__max_retries = value
        # set default adapter max retry
        self.mount("https://", HTTPAdapter(max_retries=value))
        self.mount("http://", HTTPAdapter(max_retries=value))

    def request(self, method, url, *args, **kwargs) -> requests.Response:
        sleep(self.interval)
        kwargs.setdefault("timeout", self.timeout)  # timeout to avoid suspended
        try:
            res = super().request(method, url, *args, **kwargs)
        except Exception as e:
            self.logger.error("{}:{}".format(url, e))
            res = requests.Response()
            res.url = url  # keep url info
            return res
        else:
            if not res.ok:
                self.logger.warning("{}:{}".format(url, res.status_code))
            return res


class AsmrSite(XSession):
    """"""

    def __init__(self) -> None:
        super().__init__()
        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
            "Referer": "https://www.asmr.one/"
        })

    def login(self, name="guest", password="guest"):
        """"""

        res = self.post(
            "https://api.asmr.one/api/auth/me",
            json={"name": name, "password": password}
        )

        try:
            auth_token = res.json()["token"]
        except ValueError:
            self.logger.error(f"User {name} login failed!")
            return False

        self.headers.update({
            "Authorization": f"Bearer {auth_token}"
        })

        self.logger.warning(f"User {name} login success.")
        return True

    def logout(self):
        """"""

        self.get("https://api.asmr.one/api/auth/reg")

        return True

    def get_track_info(self, track_id) -> list:
        """"""

        res = self.get(
            f"https://api.asmr.one/api/tracks/{track_id}"
        )

        try:
            track_info = res.json()
        except ValueError:
            self.logger.error(f"Failed to get track {track_id} info.")
            return []

        return track_info

    def download_file(self, url, save_path):
        """"""

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if save_path.is_file() and save_path.stat().st_size > 0:
            self.logger.warning(f"Skip download exist file {save_path}")
            return True

        res = self.head(url)
        content_length = int(res.headers.get("Content-Length", 0))
        chunk_size = 1*1024*1024
        chunk_num = math.ceil(content_length / chunk_size)

        res = self.get(url, stream=True)

        self.logger.warning(f"Begin downloading file {save_path}...")
        try:
            with save_path.open("wb") as f:
                for chunk in tqdm(res.iter_content(chunk_size), save_path.name, chunk_num, True, unit="MB"):
                    f.write(chunk)
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Failed to download file {save_path}")
            if save_path.is_file():
                os.remove(save_path)
            return False

        return True

    def download_track(self, track_id, save_dir, no_voice=False):
        """"""

        save_dir = Path(save_dir)

        track_info = self.get_track_info(track_id)

        if not track_info:
            self.logger.error(f"Falied to download track {track_id}")
            return False

        # 回溯法遍历
        nodes = [{"children": track_info, "title": f"RJ{track_id}", "next": 0}]
        while nodes:
            top = nodes[-1]

            # 目录节点
            if top.get("children"):
                # 目录遍历完成, 弹出节点
                if top["next"] >= len(top["children"]):
                    nodes.pop()
                # 进栈下一个子目录节点
                else:
                    child = top["children"][top["next"]]
                    child["next"] = 0
                    nodes.append(child)
                    top["next"] += 1
            # 文件节点
            else:
                save_path = save_dir.joinpath(*(e["title"] for e in nodes))
                if no_voice and save_path.suffix in [".mp3", ".wav"]:
                    pass
                else:
                    # print(save_path)
                    self.download_file(top["mediaDownloadUrl"], save_path)
                nodes.pop()


if __name__ == "__main__":
    print("声明: 所有资源均来自 https://www.asmr.one")
    print("="*50)

    parser = ArgumentParser()
    parser.add_argument("--no-voice", action="store_true")
    args = parser.parse_args()

    # RJ id
    rj_id = input("RJ号: ").strip()
    while not rj_id:
        print("必须输入有效的RJ号!")
        rj_id = input("RJ号: ").strip()

    rj_id = rj_id.lower().strip("rj")

    # name, password, save_dir
    def_name = "guest"
    def_pwd = "guest"
    def_save_dir = Path(".")

    name = input(f"用户名(可选)[{def_name}]: ").strip() or def_name
    password = input(f"登录密码(可选)[{def_name}]: ").strip() or def_name
    save_dir = input(f"保存位置(可选)[{def_save_dir.absolute()}]").strip() or def_save_dir

    # proxy settings
    proxy = input(f"代理(可选, 例如 '127.0.0.1:10809'): ").strip()

    asmr_sess = AsmrSite()
    if proxy:
        asmr_sess.proxies = {
            "http": proxy,
            "https": proxy
        }
    if asmr_sess.login(name, password):
        asmr_sess.download_track(rj_id, save_dir, args.no_voice)

        print(f"RJ{rj_id} downloading done!")
        asmr_sess.logout()

    input("按任意键退出...")
