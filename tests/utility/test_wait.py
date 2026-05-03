"""
Test suite for the 'wait' token handler.
All tests mock time.sleep to avoid actual waiting.
"""

import unittest
from unittest.mock import patch, call
from tokens.utility.wait import handle, _parse_duration


class test_parse_duration(unittest.TestCase):
    """test duration parsing logic."""

    # --- basic numbers ---
    def test_bare_number(self):
        self.assertEqual(_parse_duration("5"), 5.0)

    def test_float_number(self):
        self.assertEqual(_parse_duration("2.5"), 2.5)

    # --- seconds ---
    def test_seconds(self):
        self.assertEqual(_parse_duration("10 seconds"), 10.0)

    def test_secs_short(self):
        self.assertEqual(_parse_duration("3 secs"), 3.0)

    def test_sec(self):
        self.assertEqual(_parse_duration("1 sec"), 1.0)

    def test_second(self):
        self.assertEqual(_parse_duration("1 second"), 1.0)

    # --- minutes ---
    def test_minutes(self):
        self.assertEqual(_parse_duration("2 minutes"), 120.0)

    def test_mins_short(self):
        self.assertEqual(_parse_duration("2 mins"), 120.0)

    def test_min(self):
        self.assertEqual(_parse_duration("1 min"), 60.0)

    def test_minute(self):
        self.assertEqual(_parse_duration("1 minute"), 60.0)

    # --- hours ---
    def test_hours(self):
        self.assertEqual(_parse_duration("2 hours"), 7200.0)

    def test_hr(self):
        self.assertEqual(_parse_duration("1 hr"), 3600.0)

    def test_hrs(self):
        self.assertEqual(_parse_duration("1 hrs"), 3600.0)

    # --- a / an ---
    def test_a_minute(self):
        self.assertEqual(_parse_duration("a minute"), 60.0)

    def test_an_minute(self):
        self.assertEqual(_parse_duration("an minute"), 60.0)

    def test_a_second(self):
        self.assertEqual(_parse_duration("a second"), 1.0)

    def test_a_hour(self):
        self.assertEqual(_parse_duration("an hour"), 3600.0)

    # --- half ---
    def test_half_a_minute(self):
        self.assertEqual(_parse_duration("half a minute"), 30.0)

    def test_half_a_second(self):
        self.assertEqual(_parse_duration("half a second"), 0.5)

    def test_half_an_hour(self):
        self.assertEqual(_parse_duration("half an hour"), 1800.0)

    def test_half_bare(self):
        self.assertEqual(_parse_duration("half"), 0.5)

    # --- quarter ---
    def test_quarter_minute(self):
        self.assertEqual(_parse_duration("quarter minute"), 15.0)

    def test_quarter_of_a_minute(self):
        self.assertEqual(_parse_duration("quarter of a minute"), 15.0)

    def test_a_quarter_of_a_minute(self):
        self.assertEqual(_parse_duration("a quarter of a minute"), 15.0)

    def test_a_quarter_of_an_hour(self):
        self.assertEqual(_parse_duration("a quarter of an hour"), 900.0)

    def test_2_quarters_of_a_min(self):
        self.assertEqual(_parse_duration("2 quarters of a min"), 30.0)

    def test_3_quarters_of_an_hour(self):
        self.assertEqual(_parse_duration("3 quarters of an hour"), 2700.0)

    # --- compound ---
    def test_compound(self):
        self.assertEqual(_parse_duration("1 minute and 30 seconds"), 90.0)

    def test_compound_hours_minutes(self):
        self.assertEqual(_parse_duration("1 hour and 30 minutes"), 5400.0)

    def test_two_and_a_half_minutes(self):
        self.assertEqual(_parse_duration("2 and a half minutes"), 150.0)

    # --- filler ---
    def test_for_filler(self):
        self.assertEqual(_parse_duration("for 5 seconds"), 5.0)

    def test_of_filler(self):
        self.assertEqual(_parse_duration("quarter of a min"), 15.0)

    # --- empty ---
    def test_empty(self):
        self.assertEqual(_parse_duration(""), 0.0)


class test_wait(unittest.TestCase):
    """test wait handler behavior."""

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_bare_number(self, mock_sleep):
        result = handle("wait 5")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 5.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_seconds(self, mock_sleep):
        result = handle("wait 10 seconds")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 10.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_secs_short(self, mock_sleep):
        result = handle("wait 3 secs")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 3.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_minutes(self, mock_sleep):
        result = handle("wait 2 minutes")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 120.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_a_minute(self, mock_sleep):
        result = handle("wait a minute")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 60.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_half_a_minute(self, mock_sleep):
        result = handle("wait half a minute")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 30.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_quarter_minute(self, mock_sleep):
        result = handle("wait quarter minute")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 15.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_compound(self, mock_sleep):
        result = handle("wait 1 minute and 30 seconds")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 90.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_for_filler(self, mock_sleep):
        result = handle("wait for 5 seconds")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 5.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_then_remainder(self, mock_sleep):
        result = handle("wait 5 seconds and then say done")
        self.assertEqual(result, "say done")

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_and_remainder(self, mock_sleep):
        result = handle("wait 2 secs and say hi")
        self.assertEqual(result, "say hi")

    @patch("tokens.utility.wait.time.sleep")
    def test_countdown_printed(self, mock_sleep):
        """stdout should contain countdown messages."""
        with patch("builtins.print") as mock_print:
            handle("wait 3 seconds")
            printed = [str(c) for c in mock_print.call_args_list]
            # should have countdown lines
            self.assertTrue(any("3s" in p for p in printed))
            self.assertTrue(any("1s" in p for p in printed))

    @patch("tokens.utility.wait.time.sleep")
    def test_no_duration(self, mock_sleep):
        """'wait' alone should return empty and not crash."""
        result = handle("wait")
        self.assertEqual(result, "")
        mock_sleep.assert_not_called()

    @patch("tokens.utility.wait.time.sleep")
    def test_alias_pause(self, mock_sleep):
        result = handle("pause for 3 seconds")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 3.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_case_insensitive(self, mock_sleep):
        result = handle("WAIT 5")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 5.0)

    def test_no_match(self):
        """sentence without wait/pause returns unchanged."""
        result = handle("add 5 and 3")
        self.assertEqual(result, "add 5 and 3")

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_mid_sentence(self, mock_sleep):
        """wait in middle: 'say starting and wait 2 secs and say done'."""
        result = handle("say starting and wait 2 secs and say done")
        self.assertEqual(result, "say starting and say done")

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_quarter_of_a_min(self, mock_sleep):
        """'wait a quarter of a min and delete me' -> 15s, 'delete me'."""
        result = handle("wait a quarter of a min and delete me")
        self.assertEqual(result, "delete me")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 15.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_2_quarters_of_a_min(self, mock_sleep):
        """'wait 2 quarters of a min and say hi' -> 30s, 'say hi'."""
        result = handle("wait 2 quarters of a min and say hi")
        self.assertEqual(result, "say hi")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 30.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_half_an_hour(self, mock_sleep):
        result = handle("wait half an hour")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 1800.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_an_hour(self, mock_sleep):
        result = handle("wait an hour")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 3600.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_2_and_a_half_minutes(self, mock_sleep):
        result = handle("wait 2 and a half minutes")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 150.0)

    @patch("tokens.utility.wait.time.sleep")
    def test_wait_3_quarters_of_an_hour(self, mock_sleep):
        result = handle("wait 3 quarters of an hour")
        self.assertEqual(result, "")
        total_slept = sum(c.args[0] for c in mock_sleep.call_args_list)
        self.assertEqual(total_slept, 2700.0)


if __name__ == "__main__":
    unittest.main()
