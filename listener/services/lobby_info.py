"""Lobby info service for handling Lobby Info packets (Packet 9)."""

import logging
from typing import Optional

from database.repositories import LobbyInfoRepository
from packets import LobbyInfoPacket


class LobbyInfoService:
    """Processes lobby info packets and persists player snapshots."""

    def __init__(self, repo: LobbyInfoRepository, logger: Optional[logging.Logger] = None):
        self._repo = repo
        self._logger = logger or logging.getLogger(__name__)

    def handle_lobby_info_packet(self, packet: LobbyInfoPacket):
        """Extract lobby player data and upsert to database."""
        session_uid = str(packet.header.session_uid)
        active_players = packet.lobby_players[:packet.num_players]

        players = [
            {
                "m_name": p.m_name,
                "team_id": p.team_id,
                "car_number": p.car_number,
                "ready_status": p.ready_status,
                "platform": p.platform,
                "ai_controlled": bool(p.ai_controlled),
            }
            for p in active_players
        ]

        self._repo.upsert(session_uid, players, packet.num_players)
