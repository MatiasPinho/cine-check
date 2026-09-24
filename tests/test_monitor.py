import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import monitor


def response(show_times):
    return {
        "id": monitor.FILM_ID,
        "days": {
            "2026-09-25": [
                {
                    "name": "IMAX Theatre (Norcenter)",
                    "formats": [
                        {
                            "formatDescription": "IMAX-Subtitulado",
                            "performances": [{"showTime": time} for time in show_times],
                        }
                    ],
                }
            ]
        },
    }


class MonitorTests(unittest.TestCase):
    def test_new_time_is_reported_after_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "showings.json"
            with patch.object(monitor, "fetch_data", side_effect=[response(["18:50"]), response(["18:50", "22:15"])]):
                with patch("builtins.print") as first_log:
                    monitor.run(state)
                self.assertTrue(state.exists())
                self.assertFalse(any("NUEVA FUNCIÓN:" in str(call) for call in first_log.call_args_list))

                with patch("builtins.print") as second_log:
                    monitor.run(state)
                log = "\n".join(str(call) for call in second_log.call_args_list)
                self.assertIn("NUEVA FUNCIÓN: 2026-09-25 22:15", log)
                self.assertNotIn("NUEVA FUNCIÓN: 2026-09-25 18:50", log)
                self.assertEqual(len(monitor.load_state(state)), 2)

    def test_invalid_response_does_not_replace_last_good_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "showings.json"
            monitor.save_state(state, monitor.extract_showings(response(["18:50"])))
            before = state.read_bytes()
            with patch.object(monitor, "fetch_data", return_value={"id": monitor.FILM_ID}):
                with self.assertRaises(ValueError):
                    monitor.run(state)
            self.assertEqual(state.read_bytes(), before)

    def test_other_cinema_is_ignored(self):
        data = response(["N 01:10"])
        data["days"]["2026-09-25"].append(
            {
                "name": "Showcase Norcenter",
                "formats": [{"formatDescription": "2D", "performances": [{"showTime": "16:00"}]}],
            }
        )
        self.assertEqual(
            monitor.extract_showings(data),
            [{"date": "2026-09-25", "time": "N 01:10", "format": "IMAX-Subtitulado"}],
        )


if __name__ == "__main__":
    unittest.main()
