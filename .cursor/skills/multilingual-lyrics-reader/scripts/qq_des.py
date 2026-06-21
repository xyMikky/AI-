"""QQ Music custom DES implementation.

Ported from https://github.com/jixunmoe-go/qrc/internal/des
"""

from __future__ import annotations

import struct
from typing import Iterable

from qq_des_tables import (
    des_shift_table_cache,
    ip,
    ip_inv,
    key_compression,
    key_expansion,
    key_permutation_table,
    key_rnd_shifts,
    large_state_shifts,
    p_box,
    sboxes,
)


def _make_u64(hi32: int, lo32: int) -> int:
    return ((hi32 & 0xFFFFFFFF) << 32) | (lo32 & 0xFFFFFFFF)


def _swap_u64_side(value: int) -> int:
    value &= 0xFFFFFFFFFFFFFFFF
    return ((value >> 32) & 0xFFFFFFFF) | ((value << 32) & 0xFFFFFFFFFFFFFFFF)


def _u64_get_lo32(value: int) -> int:
    return value & 0xFFFFFFFF


def _u64_get_hi32(value: int) -> int:
    return (value >> 32) & 0xFFFFFFFF


def _get_u64_by_shift_idx(value: int) -> int:
    return des_shift_table_cache[value & 0x3F]


def _map_bit(result: int, src: int, check: int, set_bit: int) -> int:
    if _get_u64_by_shift_idx(check) & src:
        result |= _get_u64_by_shift_idx(set_bit)
    return result


def _map_u32_bits(src_value: int, table: Iterable[int]) -> int:
    result = 0
    for index, value in enumerate(table):
        result = _map_bit(result, src_value, value, index)
    return result & 0xFFFFFFFF


def _map_u64(src_value: int, table: Iterable[int]) -> int:
    table_list = list(table)
    mid_idx = len(table_list) // 2
    table_lo32 = table_list[:mid_idx]
    table_hi32 = table_list[mid_idx:]

    lo32 = 0
    hi32 = 0
    for index, value in enumerate(table_lo32):
        lo32 = _map_bit(lo32, src_value, value, index)
    for index, value in enumerate(table_hi32):
        hi32 = _map_bit(hi32, src_value, value, index)

    return _make_u64(hi32, lo32)


def _update_param(param: int, shift_left: int) -> int:
    shift_right = 28 - shift_left
    param = ((param << shift_left) | ((param >> shift_right) & 0xFFFFFFF0)) & 0xFFFFFFFF
    return param


class QQDes:
    def __init__(self, key_bytes: bytes, encrypt: bool) -> None:
        if len(key_bytes) != 8:
            raise ValueError("QQ DES key must be 8 bytes")
        self.subkeys: list[int] = [0] * 16
        self._set_key(key_bytes, encrypt)

    def _set_key(self, key_bytes: bytes, encrypt: bool) -> None:
        key = struct.unpack("<Q", key_bytes)[0]
        param = _map_u64(key, key_permutation_table)
        param_c = _u64_get_lo32(param)
        param_d = _u64_get_hi32(param)

        for index, shift_left in enumerate(key_rnd_shifts):
            subkey_idx = index if encrypt else 15 - index
            param_c = _update_param(param_c, shift_left)
            param_d = _update_param(param_d, shift_left)
            self.subkeys[subkey_idx] = _map_u64(_make_u64(param_d, param_c), key_compression)

    def transform_block(self, data: int) -> int:
        state = _map_u64(data, ip)
        for subkey in self.subkeys:
            state = self._des_crypt_proc(state, subkey)
        state = _swap_u64_side(state)
        return _map_u64(state, ip_inv)

    def _des_crypt_proc(self, state: int, key: int) -> int:
        state_hi32 = _u64_get_hi32(state)
        state_lo32 = _u64_get_lo32(state)
        state = _map_u64(_make_u64(state_hi32, state_hi32), key_expansion)
        state ^= key
        next_lo32 = self._sbox_transform(state)
        next_lo32 = _map_u32_bits(next_lo32, p_box)
        next_lo32 ^= state_lo32
        return _make_u64(next_lo32, state_hi32)

    @staticmethod
    def _sbox_transform(state: int) -> int:
        result = 0
        for index, shift_value in enumerate(large_state_shifts):
            sbox_idx = (state >> shift_value) & 0b111111
            result = ((result << 4) | sboxes[index][sbox_idx]) & 0xFFFFFFFF
        return result

    def transform_bytes(self, data: bytearray) -> None:
        if len(data) % 8 != 0:
            raise ValueError("data length must be a multiple of 8")
        for offset in range(0, len(data), 8):
            value = struct.unpack("<Q", data[offset : offset + 8])[0]
            value = self.transform_block(value)
            data[offset : offset + 8] = struct.pack("<Q", value)


def triple_transform(data: bytearray, encrypt_flags: tuple[bool, bool, bool], keys: tuple[bytes, bytes, bytes]) -> None:
    for encrypt, key in zip(encrypt_flags, keys):
        QQDes(key, encrypt).transform_bytes(data)
