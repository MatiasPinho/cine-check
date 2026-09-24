import io
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

    def test_new_showing_creates_issue_assigned_to_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            changes = Path(directory) / "changes.json"
            changes.write_text(
                json.dumps([{"date": "2026-09-25", "time": "22:15", "format": "IMAX-Subtitulado"}]),
                encoding="utf-8",
            )
            env = {
                "GITHUB_REPOSITORY": "MatiasPinho/cine-check",
                "GITHUB_REPOSITORY_OWNER": "MatiasPinho",
                "GITHUB_TOKEN": "test-token",
            }
            fake_response = io.BytesIO(json.dumps({"html_url": "https://github.com/MatiasPinho/cine-check/issues/1"}).encode())
            with patch.dict("os.environ", env), patch.object(notify_github, "urlopen", return_value=fake_response) as open_url:
                notify_github.notify(changes)
            request = open_url.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(payload["assignees"], ["MatiasPinho"])
            self.assertIn("22:15", payload["title"])
            self.assertIn("| viernes 25/09/2026 | 22:15", payload["body"])

    def test_manual_test_is_labeled_and_does_not_claim_new_showings(self):
        env = {
            "GITHUB_REPOSITORY": "MatiasPinho/cine-check",
            "GITHUB_REPOSITORY_OWNER": "MatiasPinho",
            "GITHUB_TOKEN": "test-token",
        }
        fake_response = io.BytesIO(json.dumps({"html_url": "https://github.com/MatiasPinho/cine-check/issues/2"}).encode())
        with patch.dict("os.environ", env), patch.object(notify_github, "urlopen", return_value=fake_response) as open_url:
            notify_github.send_test()
        payload = json.loads(open_url.call_args.args[0].data)
        self.assertIn("PRUEBA", payload["title"])
        self.assertIn("No se publicó ninguna función nueva", payload["body"])
        self.assertEqual(payload["assignees"], ["MatiasPinho"])
