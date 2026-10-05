"""Minimal ctypes wrapper around Epic's Oodle (oo2core) DLL.

Used to decompress Oodle-compressed blocks inside Black Myth: Wukong .pak files.
The DLL (oo2core_9_win64.dll, sha256
6f5d41a7892ea6b2db420f2458dad2f84a63901c9a93ce9497337b16c195f457) lives in tools/bin/.
"""
import ctypes
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DLL_CANDIDATES = [
    os.path.join(_HERE, "bin", "oo2core_9_win64.dll"),
    os.path.join(_HERE, "bin", "oo2core_9_win64.dll".replace("9", "8")),
]

_lib = None


def _load():
    global _lib
    if _lib is not None:
        return _lib
    path = None
    for cand in DLL_CANDIDATES:
        if os.path.exists(cand):
            path = cand
            break
    if path is None:
        raise FileNotFoundError(
            "oo2core_9_win64.dll not found next to tools/bin; cannot decompress Oodle blocks"
        )
    lib = ctypes.CDLL(path)
    # silence Oodle's internal logging
    try:
        lib.OodleCore_Plugins_SetPrintf.argtypes = [ctypes.c_void_p]
        lib.OodleCore_Plugins_SetPrintf.restype = None
        lib.OodleCore_Plugins_SetPrintf(None)
    except AttributeError:
        pass

    lib.OodleLZ_Decompress.argtypes = [
        ctypes.c_char_p, ctypes.c_size_t,          # compBuf, compBufSize
        ctypes.c_char_p, ctypes.c_size_t,          # rawBuf, rawLen
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,   # fuzzSafe, checkCRC, verbosity
        ctypes.c_uint64, ctypes.c_size_t,          # decBufBase, decBufSize
        ctypes.c_uint64, ctypes.c_uint64,          # fpCallback, callbackUserData
        ctypes.c_char_p, ctypes.c_size_t,          # decoderMemory, decoderMemorySize
        ctypes.c_uint32,                           # threadPhase
    ]
    lib.OodleLZ_Decompress.restype = ctypes.c_ssize_t

    lib.OodleLZ_GetCompressedBufferSizeNeeded.argtypes = [ctypes.c_int32, ctypes.c_size_t]
    lib.OodleLZ_GetCompressedBufferSizeNeeded.restype = ctypes.c_size_t

    lib.OodleLZ_Compress.argtypes = [
        ctypes.c_int32,                            # compressor
        ctypes.c_char_p, ctypes.c_size_t,          # rawBuf, rawLen
        ctypes.c_char_p,                           # compBuf
        ctypes.c_int32,                            # level
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_char_p, ctypes.c_size_t,          # scratchMem, scratchSize
    ]
    lib.OodleLZ_Compress.restype = ctypes.c_ssize_t

    _lib = lib
    return lib


def decompress(data, raw_len, check_crc=False):
    """Decompress one Oodle block; returns exactly raw_len bytes (raises on failure)."""
    lib = _load()
    out = ctypes.create_string_buffer(raw_len)
    n = lib.OodleLZ_Decompress(
        data, len(data), out, raw_len,
        1, 1 if check_crc else 0, 0,
        0, 0, 0, 0, None, 0, 3,
    )
    if n <= 0:
        raise ValueError("OodleLZ_Decompress failed (returned %d, in=%d, out=%d)"
                         % (n, len(data), raw_len))
    return out.raw[:n]


KRaken = 8
KLeviathan = 13
KMermaid = 9
KSelkie = 11
KHydra = 12


def compress(data, compressor=KRaken, level=6):
    """Compress one buffer with Oodle. level 6 == Optimal2 (UE's usual choice)."""
    lib = _load()
    need = lib.OodleLZ_GetCompressedBufferSizeNeeded(compressor, len(data))
    buf = ctypes.create_string_buffer(need)
    n = lib.OodleLZ_Compress(compressor, data, len(data), buf, level,
                             None, None, None, None, 0)
    if n <= 0:
        raise ValueError("OodleLZ_Compress failed (returned %d)" % n)
    return buf.raw[:n]


if __name__ == "__main__":
    lib = _load()
    print("Oodle DLL loaded:", DLL_CANDIDATES[0])
