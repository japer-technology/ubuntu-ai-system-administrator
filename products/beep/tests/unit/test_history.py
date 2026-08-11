from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from history import History


class HistoryDeletionTests(unittest.TestCase):
    def test_delete_conversation_cascades_messages_events_and_reactivation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            history = History(Path(directory) / "history.db")
            try:
                conversation_id = history.create_conversation("private")
                history.add_message(conversation_id, "user", "secret text")
                history.add_event(conversation_id, "tool_call", {"tool": "sys.info"})
                history.schedule_reactivation(
                    conversation_id,
                    60,
                    "continue",
                    "continue",
                    actor="operator",
                    replace_existing=False,
                )
                self.assertTrue(history.delete_conversation(conversation_id))
                self.assertFalse(history.conversation_exists(conversation_id))
                self.assertEqual(history.get_messages(conversation_id), [])
                self.assertEqual(history.get_events(conversation_id), [])
                self.assertIsNone(history.pending_reactivation())
                self.assertFalse(history.delete_conversation(conversation_id))
            finally:
                history.close()


if __name__ == "__main__":
    unittest.main()
