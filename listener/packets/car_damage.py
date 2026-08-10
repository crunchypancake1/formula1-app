import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

# float[4] tyresWear, uint8[4] tyresDamage, uint8[4] brakesDamage,
# uint8[4] tyreBlisters, 18×uint8 (wing/floor/diffuser/sidepod damage + faults + engine wear)
_CAR_DAMAGE_FORMAT = '<4f4B4B4B18B'
_CAR_DAMAGE_FORMAT_SIZE = struct.calcsize(_CAR_DAMAGE_FORMAT)


@dataclass
class CarDamageData:
    tyres_wear: tuple               # float[4]  | percentage per wheel
    tyres_damage: tuple             # uint8[4]  | percentage per wheel
    brakes_damage: tuple            # uint8[4]  | percentage per wheel
    tyre_blisters: tuple            # uint8[4]  | percentage per wheel
    front_left_wing_damage: int     # uint8     | percentage
    front_right_wing_damage: int    # uint8     | percentage
    rear_wing_damage: int           # uint8     | percentage
    floor_damage: int               # uint8     | percentage
    diffuser_damage: int            # uint8     | percentage
    sidepod_damage: int             # uint8     | percentage
    drs_fault: bool                 # uint8     | 0=OK, 1=fault
    ers_fault: bool                 # uint8     | 0=OK, 1=fault
    gearbox_damage: int             # uint8     | percentage
    engine_damage: int              # uint8     | percentage
    engine_mguh_wear: int           # uint8     | percentage
    engine_es_wear: int             # uint8     | percentage
    engine_ce_wear: int             # uint8     | percentage
    engine_ice_wear: int            # uint8     | percentage
    engine_mguk_wear: int           # uint8     | percentage
    engine_tc_wear: int             # uint8     | percentage
    engine_blown: bool              # uint8     | 0=OK, 1=fault
    engine_seized: bool             # uint8     | 0=OK, 1=fault


@dataclass
class CarDamagePacket:
    header: PacketHeader
    car_damage_data: list[CarDamageData]


def unpack_car_damage(packet_header: PacketHeader, data: bytes) -> CarDamagePacket:
    """Unpack Car Damage packet (Packet ID: 10). Extracts all per-car damage fields."""
    car_data_bytes = data[:(_CAR_DAMAGE_FORMAT_SIZE * 22)]

    car_list = []
    for f in struct.iter_unpack(_CAR_DAMAGE_FORMAT, car_data_bytes):
        # f indices: 0-3=tyresWear[4], 4-7=tyresDamage[4], 8-11=brakesDamage[4],
        # 12-15=tyreBlisters[4], 16-33=18 individual uint8 fields
        car_list.append(CarDamageData(
            tyres_wear=(f[0], f[1], f[2], f[3]),
            tyres_damage=(f[4], f[5], f[6], f[7]),
            brakes_damage=(f[8], f[9], f[10], f[11]),
            tyre_blisters=(f[12], f[13], f[14], f[15]),
            front_left_wing_damage=f[16],
            front_right_wing_damage=f[17],
            rear_wing_damage=f[18],
            floor_damage=f[19],
            diffuser_damage=f[20],
            sidepod_damage=f[21],
            drs_fault=bool(f[22]),
            ers_fault=bool(f[23]),
            gearbox_damage=f[24],
            engine_damage=f[25],
            engine_mguh_wear=f[26],
            engine_es_wear=f[27],
            engine_ce_wear=f[28],
            engine_ice_wear=f[29],
            engine_mguk_wear=f[30],
            engine_tc_wear=f[31],
            engine_blown=bool(f[32]),
            engine_seized=bool(f[33]),
        ))

    return CarDamagePacket(packet_header, car_list)
