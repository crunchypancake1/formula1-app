import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.lap_history import LapHistoryService

from .mock_repo import MockRepo


def _make_lap_history(lap_time_in_ms=88000,
                      sector_1_time_ms_part=28000, sector_1_time_minutes_part=0,
                      sector_2_time_ms_part=30000, sector_2_time_minutes_part=0,
                      sector_3_time_ms_part=30000, sector_3_time_minutes_part=0,
                      lap_valid_bit_flags=0x0F):
    return SimpleNamespace(
        lap_time_in_ms=lap_time_in_ms,
        sector_1_time_ms_part=sector_1_time_ms_part,
        sector_1_time_minutes_part=sector_1_time_minutes_part,
        sector_2_time_ms_part=sector_2_time_ms_part,
        sector_2_time_minutes_part=sector_2_time_minutes_part,
        sector_3_time_ms_part=sector_3_time_ms_part,
        sector_3_time_minutes_part=sector_3_time_minutes_part,
        lap_valid_bit_flags=lap_valid_bit_flags,
    )


def _make_stint(tyre_actual_compound=20, tyre_visual_compound=16, end_lap=15):
    return SimpleNamespace(
        tyre_actual_compound=tyre_actual_compound,
        tyre_visual_compound=tyre_visual_compound,
        end_lap=end_lap,
    )


def _make_history_packet(session_uid=123, car_index=0, num_laps=1,
                         laps=None, stints=None):
    if laps is None:
        laps = [_make_lap_history()]
    header = SimpleNamespace(session_uid=session_uid, session_time=10.0, overall_frame_identifier=1)
    return SimpleNamespace(
        header=header,
        car_index=car_index,
        num_laps=num_laps,
        lap_history_list=laps,
        tyre_stints_list=stints or [],
        num_tyre_stints=len(stints or []),
    )


def _make_service():
    laps_repo = MockRepo()
    stints_repo = MockRepo()
    svc = LapHistoryService(laps_repo, stints_repo)
    return svc, laps_repo, stints_repo


def test_upserts_laps():
    svc, laps_repo, _ = _make_service()
    laps = [_make_lap_history(), _make_lap_history()]
    packet = _make_history_packet(num_laps=2, laps=laps)
    svc.handle_session_history_packet(packet, user_map={0: 100})
    args, _ = laps_repo.last_call("upsert_laps_batch")
    batch = args[0]
    assert len(batch) == 2


def test_incremental_processing():
    svc, laps_repo, _ = _make_service()

    # First: 1 lap
    packet1 = _make_history_packet(num_laps=1, laps=[_make_lap_history()])
    svc.handle_session_history_packet(packet1, user_map={0: 100})

    # Second: 2 laps — should process from lap 1 (overlap by 1)
    packet2 = _make_history_packet(num_laps=2, laps=[_make_lap_history(), _make_lap_history()])
    svc.handle_session_history_packet(packet2, user_map={0: 100})

    assert laps_repo.call_count("upsert_laps_batch") == 2


def test_zero_lap_time_skipped():
    svc, laps_repo, _ = _make_service()
    laps = [_make_lap_history(lap_time_in_ms=0)]
    packet = _make_history_packet(num_laps=1, laps=laps)
    svc.handle_session_history_packet(packet, user_map={0: 100})
    assert laps_repo.call_count("upsert_laps_batch") == 0


def test_sector_validity_bits():
    svc, laps_repo, _ = _make_service()
    # 0x05 = 0b0101: bit0 (lap valid) = 1, bit1 (sector1 valid) = 0,
    # bit2 (sector2 valid) = 1, bit3 (sector3 valid) = 0
    laps = [_make_lap_history(lap_valid_bit_flags=0x05)]
    packet = _make_history_packet(num_laps=1, laps=laps)
    svc.handle_session_history_packet(packet, user_map={0: 100})
    args, _ = laps_repo.last_call("upsert_laps_batch")
    row = args[0][0]
    # row layout: (session_uid, user_id, lap_num, lap_time, s1, s2, s3,
    #              is_valid, s1_valid, s2_valid, s3_valid)
    is_valid = row[7]
    sector1_valid = row[8]
    sector2_valid = row[9]
    sector3_valid = row[10]
    assert is_valid is True
    assert sector1_valid is False
    assert sector2_valid is True
    assert sector3_valid is False


def test_sector_time_conversion():
    svc, laps_repo, _ = _make_service()
    # 1 minute + 30000ms = 90000ms total
    laps = [_make_lap_history(sector_1_time_minutes_part=1, sector_1_time_ms_part=30000)]
    packet = _make_history_packet(num_laps=1, laps=laps)
    svc.handle_session_history_packet(packet, user_map={0: 100})
    args, _ = laps_repo.last_call("upsert_laps_batch")
    row = args[0][0]
    # sector1_time_ms is at index 4
    assert row[4] == 90000


def test_tyre_stints_written():
    svc, _, stints_repo = _make_service()
    stints = [_make_stint(), _make_stint(tyre_actual_compound=18)]
    packet = _make_history_packet(stints=stints)
    svc.handle_tyre_stints(packet, user_map={0: 100})
    assert stints_repo.call_count("upsert_stints_batch") == 1
    args, _ = stints_repo.last_call("upsert_stints_batch")
    batch = args[0]
    assert len(batch) == 2
