import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """初始化全局日志配置，应用启动时调用一次。"""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
