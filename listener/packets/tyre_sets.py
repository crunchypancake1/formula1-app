import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

# TyreSetData per slot:
#   7×uint8 (actualCompound, visualCompound, wear, available,
#            recommendedSession, lifeSpan, usableLife)
#   1×int16 (lapDeltaTime)
#   1×uint8 (fitted)
# = 10 bytes per slot, 20 slots per car
_TYRE_SET_FORMAT = '<7BhB'
_TYRE_SET_FORMAT_SIZE = struct.calcsize(_TYRE_SET_FORMAT)


@dataclass
class TyreSetData:
    actual_compound: int
    visual_compound: int
    wear: int
    available: int
    recommended_session: int
    life_span: int
    usable_life: int
    lap_delta_time: int
    fitted: int


@dataclass
class TyreSetsPacket:
    header: PacketHeader
    car_idx: int
    tyre_set_data: list[TyreSetData]
    fitted_idx: int


def unpack_tyre_sets(packet_header: PacketHeader, data: bytes) -> TyreSetsPacket:
    """
    Unpack Tyre Sets packet (Packet ID: 12). 20 tyre set slots for one car.

    The packet cycles one car per send — key it by car_idx. It arrives entirely
    zeroed for a driver whose Your Telemetry setting is Restricted.
    """
    car_idx = struct.unpack('<B', data[:1])[0]
    set_data_bytes = data[1:1 + (_TYRE_SET_FORMAT_SIZE * 20)]
    remaining = data[1 + (_TYRE_SET_FORMAT_SIZE * 20):]

    tyre_sets = []
    for f in struct.iter_unpack(_TYRE_SET_FORMAT, set_data_bytes):
        tyre_sets.append(TyreSetData(*f))

    fitted_idx = struct.unpack('<B', remaining[:1])[0]
    return TyreSetsPacket(packet_header, car_idx, tyre_sets, fitted_idx)
