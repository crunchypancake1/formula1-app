import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from database.repositories.car_frame_motion_ex import CAR_FRAME_MOTION_EX_COLUMNS
from services.motion_ex import MotionExService

from . import factories

from .mock_repo import MockRepo


def _make_motion_ex_data():
    return SimpleNamespace(
        suspension_position=(1, 2, 3, 4),
        suspension_velocity=(5, 6, 7, 8),
        suspension_acceleration=(9, 10, 11, 12),
        wheel_speed=(80, 81, 82, 83),
        wheel_slip_ratio=(0.01, 0.02, 0.03, 0.04),
        wheel_slip_angle=(0.1, 0.2, 0.3, 0.4),
        wheel_lat_force=(100, 200, 300, 400),
        wheel_long_force=(500, 600, 700, 800),
        wheel_vert_force=(3000, 3100, 3200, 3300),
        wheel_camber=(-3.5, -3.4, -3.3, -3.2),
        wheel_camber_gain=(0.5, 0.6, 0.7, 0.8),
        height_of_cog_above_ground=0.35,
        local_velocity_x=55.0,
        local_velocity_y=0.5,
        local_velocity_z=-1.0,
        angular_velocity_x=0.01,
        angular_velocity_y=0.02,
        angular_velocity_z=0.03,
        angular_acceleration_x=0.04,
        angular_acceleration_y=0.05,
        angular_acceleration_z=0.06,
        front_wheels_angle=0.12,
        front_aero_height=0.05,
        rear_aero_height=0.08,
        front_roll_angle=0.003,
        rear_roll_angle=0.004,
        chassis_yaw=1.57,
        chassis_pitch=0.01,
    )


def _make_motion_ex_packet(session_uid=123, player_car_index=0):
    return SimpleNamespace(
        header=factories.make_header(
            packet_id=13, session_uid=session_uid, player_car_index=player_car_index
        ),
        motion_ex_data=_make_motion_ex_data(),
    )


def _make_service():
    repo = MockRepo()
    svc = MotionExService(repo)
    return svc, repo


def test_writes_player_car():
    svc, repo = _make_service()
    packet = _make_motion_ex_packet(player_car_index=0)
    svc.write_motion_ex(packet, user_map={0: 100})
    assert repo.call_count("insert") == 1


def test_skips_unknown_player():
    svc, repo = _make_service()
    packet = _make_motion_ex_packet(player_car_index=5)
    svc.write_motion_ex(packet, user_map={0: 100})
    assert repo.call_count("insert") == 0


def test_row_tuple_length():
    svc, repo = _make_service()
    packet = _make_motion_ex_packet(player_car_index=0)
    svc.write_motion_ex(packet, user_map={0: 100})
    args, _ = repo.last_call("insert")
    row = args[0]
    # The row must line up with the repository's column list exactly, or the
    # INSERT silently binds values to the wrong columns.
    assert len(row) == len(CAR_FRAME_MOTION_EX_COLUMNS)
