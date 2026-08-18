import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header
from packets.session import unpack_session

from .packet_builder.session import build_session_packet


class TestSessionParser:

    def test_track_id_and_session_type(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            track_id=11, session_type=15,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert result.track_id == 11
        assert result.session_type == 15

    def test_weather_fields(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            weather=2, track_temperature=35, air_temperature=28,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert result.weather == 2
        assert result.track_temperature == 35
        assert result.air_temperature == 28

    def test_total_laps_and_track_length(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            total_laps=50, track_length=5793,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert result.total_laps == 50
        assert result.track_length == 5793

    def test_marshal_zones_count(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert len(result.marshal_zones) == 21

    def test_weather_forecast_samples_count(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert len(result.weather_forecast_samples) == 64

    def test_2026_tail_fields_round_trip(self):
        active_aero_zones_full = [(0.0, 0.0)] * 8
        active_aero_zones_full[0] = (0.1, 0.2)
        active_aero_zones_full[5] = (0.6, 0.65)

        active_aero_zones_partial = [(0.0, 0.0)] * 8
        active_aero_zones_partial[1] = (0.15, 0.25)
        active_aero_zones_partial[7] = (0.9, 0.95)

        drs_zones = [(0.0, 0.0)] * 4
        drs_zones[0] = (0.3, 0.4)
        drs_zones[3] = (0.85, 0.99)

        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            track_id=11, session_type=15, total_laps=50,
            track_length=5793, weather=2, track_temperature=35,
            air_temperature=28,
            active_aero_track_status=1,
            num_active_aero_zones_full=8,
            active_aero_zones_full=active_aero_zones_full,
            num_active_aero_zones_partial=8,
            active_aero_zones_partial=active_aero_zones_partial,
            num_drs_zones=4,
            drs_zones=drs_zones,
            start_reaction_time=0.234,
            anti_lock_brakes_assist=1,
            traction_control_assist=2,
            dynamic_racing_line_hi_vis=1,
            dynamic_racing_line_colour_blind=3,
            recurring_rewind_prompt=1,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)

        # Pre-tail fields (including sector_3_lap_distance_start) must still
        # round-trip correctly - catches an off-by-one at the old/new seam.
        assert result.track_id == 11
        assert result.session_type == 15
        assert result.total_laps == 50
        assert result.track_length == 5793
        assert result.weather == 2
        assert result.track_temperature == 35
        assert result.air_temperature == 28
        assert len(result.marshal_zones) == 21
        assert len(result.weather_forecast_samples) == 64
        assert result.sector_2_lap_distance_start == 2400.0
        assert result.sector_3_lap_distance_start == 4200.0

        # New tail fields
        assert result.active_aero_track_status == 1
        assert result.num_active_aero_zones_full == 8
        assert len(result.active_aero_zones_full) == 8
        assert (result.active_aero_zones_full[0].zone_start,
                result.active_aero_zones_full[0].zone_end) == (0.1, 0.2)
        assert (round(result.active_aero_zones_full[5].zone_start, 4),
                round(result.active_aero_zones_full[5].zone_end, 4)) == (0.6, 0.65)

        assert result.num_active_aero_zones_partial == 8
        assert len(result.active_aero_zones_partial) == 8
        assert (round(result.active_aero_zones_partial[1].zone_start, 4),
                round(result.active_aero_zones_partial[1].zone_end, 4)) == (0.15, 0.25)
        assert (round(result.active_aero_zones_partial[7].zone_start, 4),
                round(result.active_aero_zones_partial[7].zone_end, 4)) == (0.9, 0.95)

        assert result.num_drs_zones == 4
        assert len(result.drs_zones) == 4
        assert (round(result.drs_zones[0].zone_start, 4),
                round(result.drs_zones[0].zone_end, 4)) == (0.3, 0.4)
        assert (round(result.drs_zones[3].zone_start, 4),
                round(result.drs_zones[3].zone_end, 4)) == (0.85, 0.99)

        assert round(result.start_reaction_time, 4) == 0.234
        assert result.anti_lock_brakes_assist == 1
        assert result.traction_control_assist == 2
        assert result.dynamic_racing_line_hi_vis == 1
        assert result.dynamic_racing_line_colour_blind == 3
        assert result.recurring_rewind_prompt == 1
