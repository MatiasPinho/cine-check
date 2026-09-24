import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import notify_github


class GitHubNotificationTests(unittest.TestCase):
    def test_message_contains_only_new_showings_and_link(self):
        title, body = notify_github.issue_content(
            [{"date": "2026-09-25", "time": "22:15", "format": "IMAX-Subtitulado"}]
        )
        self.assertIn("viernes 25/09/2026 22:15", title)
        self.assertIn("| viernes 25/09/2026 | 22:15 | IMAX-Subtitulado |", body)
        self.assertIn("filmid=6017&house_id=3250", body)

    def test_empty_change_list_never_calls_github(self):
        with tempfile.TemporaryDirectory() as directory:
            changes = Path(directory) / "changes.json"
            changes.write_text(json.dumps([]), encoding="utf-8")
            with patch.object(notify_github, "urlopen") as open_url:
                self.assertIsNone(notify_github.notify(changes))
            open_url.assert_not_called()
