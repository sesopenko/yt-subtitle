"""Discover the project's NVIDIA runtime libraries before CUDA inference."""

import ctypes
import os
import sys
from importlib.metadata import PackageNotFoundError, distribution


_dll_directories = []


def prepare_cuda() -> None:
    if sys.platform == "win32":
        if not _dll_directories:
            directories = set()
            for name in ("nvidia-cublas-cu12", "nvidia-cudnn-cu12", "nvidia-cuda-runtime-cu12"):
                try:
                    package = distribution(name)
                except PackageNotFoundError as exc:
                    raise RuntimeError("NVIDIA runtime packages are missing; run uv sync.") from exc
                for file in package.files or []:
                    if str(file).lower().endswith(".dll"):
                        directories.add(str(package.locate_file(file).parent.resolve()))
            for directory in sorted(directories):
                _dll_directories.append(os.add_dll_directory(directory))
            # CTranslate2 also loads some libraries through the Windows PATH.
            os.environ["PATH"] = os.pathsep.join(sorted(directories) + [os.environ.get("PATH", "")])
        for library in ("cublas64_12.dll", "cudnn64_9.dll"):
            ctypes.WinDLL(library)

    import ctranslate2

    if ctranslate2.get_cuda_device_count() < 1:
        raise RuntimeError("No CUDA GPU detected. Check the NVIDIA driver and nvidia-smi.")
    if "float16" not in ctranslate2.get_supported_compute_types("cuda"):
        raise RuntimeError("The CUDA GPU does not support float16 inference.")
