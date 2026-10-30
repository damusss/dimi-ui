from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dimi-ui")
except PackageNotFoundError:
    __version__ = "unknown"
