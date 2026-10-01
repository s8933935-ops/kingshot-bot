#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversation Memory Manager for Satisfactory Discord Bot
Stores the last 30 turns of conversation per channel, persists to JSON,
and injects history into AI prompts for seamless multi-turn context.
"""

import os
import json
from typing import List, Dict, Any, Optional

HISTORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/conversation_history.json"))
DEFAULT_MAX_HISTORY = 30


class ConversationMemoryManager:
    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY):
        self.max_history = max_history
        self.history: Dict[str, List[Dict[str, Any]]] = self._load()

    def _load(self) -> Dict[str, List[Dict[str, Any]]]:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[!] Failed to save conversation history: {e}")

    def add_message(self, channel_id: str, role: str, name: str, content: str):
        """
        Add a message to channel history.
        role: 'user' or 'assistant'
        name: display name of user or bot
        """
        cid = str(channel_id)
        if cid not in self.history:
            self.history[cid] = []

        # Clean content and truncate overly long assistant dumps to preserve token budget
        clean_text = content.strip()
        if role == "assistant" and len(clean_text) > 800:
            clean_text = clean_text[:800] + "...(以下省略)"

        self.history[cid].append({
            "role": role,
            "name": name,
            "content": clean_text
        })

        # Keep only the last max_history turns
        if len(self.history[cid]) > self.max_history:
            self.history[cid] = self.history[cid][-self.max_history:]

        self._save()

    def get_history(self, channel_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        cid = str(channel_id)
        msgs = self.history.get(cid, [])
        if limit and limit < len(msgs):
            return msgs[-limit:]
        return msgs

    def format_for_prompt(self, channel_id: str, limit: int = 20) -> str:
        """Format recent history into a clean string for AI context injection."""
        recent = self.get_history(channel_id, limit=limit)
        if not recent:
            return ""

        formatted_lines = []
        for msg in recent:
            prefix = f"👤 {msg['name']}" if msg['role'] == 'user' else "🤖 FICSIT顧問団"
            formatted_lines.append(f"{prefix}: {msg['content']}")

        return "\n".join(formatted_lines)

    def clear(self, channel_id: str) -> int:
        """Clear memory for a specific channel."""
        cid = str(channel_id)
        count = len(self.history.get(cid, []))
        if cid in self.history:
            del self.history[cid]
            self._save()
        return count
