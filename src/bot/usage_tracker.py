#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Usage Tracker & Rate Limiter for Satisfactory Discord Bot
Tracks Claude 3.7 Sonnet usage (30 shared queries/day), resets daily,
and provides real-time limit indicators without money focus.
"""

import os
import json
from datetime import datetime, date
from typing import Dict, Any, Tuple

TRACKER_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/bot_usage.json"))
CLAUDE_DAILY_LIMIT = 30


class UsageTracker:
    def __init__(self, limit: int = CLAUDE_DAILY_LIMIT):
        self.daily_limit = limit
        self.data = self._load()
        self._ensure_today()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(TRACKER_FILE):
            try:
                with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _get_jst_today(self) -> str:
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        return datetime.now(jst).date().isoformat()

    def _ensure_today(self):
        today_str = self._get_jst_today()
        if self.data.get("current_date") != today_str:
            # Archive previous day if exists
            if self.data.get("current_date"):
                history = self.data.get("history", [])
                history.append({
                    "date": self.data.get("current_date"),
                    "claude_used": self.data.get("claude_used", 0),
                    "gemini_used": self.data.get("gemini_used", 0),
                    "users_count": len(self.data.get("users", {}))
                })
                # Keep last 30 days of history
                self.data["history"] = history[-30:]

            self.data.update({
                "current_date": today_str,
                "claude_used": 0,
                "gemini_used": 0,
                "db_used": 0,
                "users": {}  # user_id -> {"name": str, "claude": int, "other": int}
            })
            self._save()

    def can_use_claude(self) -> bool:
        self._ensure_today()
        return self.data["claude_used"] < self.daily_limit

    def record_usage(self, model_type: str, user_id: str, username: str) -> Tuple[bool, int]:
        """
        Record query usage.
        model_type: 'claude', 'gemini', or 'db'
        Returns: (success_using_claude, remaining_claude_quota)
        """
        self._ensure_today()
        user_key = str(user_id)
        if user_key not in self.data["users"]:
            self.data["users"][user_key] = {"name": username, "claude": 0, "other": 0}

        if model_type == "claude":
            if self.data["claude_used"] < self.daily_limit:
                self.data["claude_used"] += 1
                self.data["users"][user_key]["claude"] += 1
                self._save()
                return True, (self.daily_limit - self.data["claude_used"])
            else:
                # Quota exceeded: fallback to other
                self.data["gemini_used"] += 1
                self.data["users"][user_key]["other"] += 1
                self._save()
                return False, 0
        elif model_type == "gemini":
            self.data["gemini_used"] += 1
            self.data["users"][user_key]["other"] += 1
        else:
            self.data["db_used"] += 1

        self._save()
        remaining = max(0, self.daily_limit - self.data["claude_used"])
        return True, remaining

    def get_progress_bar(self, length: int = 10) -> str:
        self._ensure_today()
        used = self.data["claude_used"]
        filled = int((used / self.daily_limit) * length)
        filled = min(length, max(0, filled))
        bar = "■" * filled + "□" * (length - filled)
        return bar

    def get_status_embed_data(self) -> Dict[str, Any]:
        self._ensure_today()
        used = self.data["claude_used"]
        remaining = max(0, self.daily_limit - used)
        bar = self.get_progress_bar(10)

        user_breakdown = []
        for uid, uinfo in self.data.get("users", {}).items():
            user_breakdown.append(f"• **{uinfo['name']}**: Claude {uinfo['claude']}回 / その他 {uinfo['other']}回")

        return {
            "date": self.data["current_date"],
            "claude_used": used,
            "claude_limit": self.daily_limit,
            "claude_remaining": remaining,
            "progress_bar": bar,
            "gemini_used": self.data["gemini_used"],
            "db_used": self.data["db_used"],
            "users_list": "\n".join(user_breakdown) if user_breakdown else "本日まだ利用はありません"
        }
