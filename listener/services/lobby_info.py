"""Lobby info service for handling Lobby Info packets (Packet 9)."""

import logging
from typing import Optional

from database.repositories import LobbyInfoRepository
from database.repositories.base import safe_enum_name
from enums import Nationalities, Platform
from packets import LobbyInfoPacket


class LobbyInfoService:
    """Processes lobby info packets and persists player snapshots."""

    def __init__(self, repo: LobbyInfoRepository, logger: Optional[logging.Logger] = None):
        self._repo = repo
        self._logger = logger or logging.getLogger(__name__)

    def handle_lobby_info_packet(self, packet: LobbyInfoPacket):
        """Snapshot the lobby roster.

        name is the driver name unless the player has "show online ID" on, in
        which case it is their platform gamertag — show_online_names says which
        of the two you are looking at.
        """
        session_uid = str(packet.header.session_uid)
        active_players = packet.lobby_players[:packet.num_players]

        players = [
            {
                "name": p.m_name,
                "team_id": p.team_id,
                "car_number": p.car_number,
                "nationality": safe_enum_name(Nationalities, p.nationality, self._logger),
                "platform": safe_enum_name(Platform, p.platform, self._logger),
                "tech_level": p.tech_level,
                "ready_status": p.ready_status,
                "telemetry_public": bool(p.your_telemetry),
                "show_online_names": bool(p.show_online_names),
                "ai_controlled": bool(p.ai_controlled),
            }
            for p in active_players
        ]

        self._repo.upsert(session_uid, players, packet.num_players)
