from pupil_recording_interface.utils import (
    multiprocessing_deque,
    merge_pupils,
)


class TestUtils:
    def test_multiprocessing_deque(self):
        """"""
        max_len = 10
        test_len = 12
        deque = multiprocessing_deque(max_len)
        for it in range(test_len):
            deque.append(it)

        for it in range(test_len - 1, test_len - max_len - 1, -1):
            assert deque.pop() == it

        assert not deque._getvalue()

    def test_interleave_pupils(self):
        """"""
        pupils_eye0 = [{"timestamp": ts} for ts in (0, 2, 4, 5, 6)]
        pupils_eye1 = [{"timestamp": ts} for ts in (1, 3, 7, 8)]

        pupils = merge_pupils(pupils_eye0, pupils_eye1)
        for idx, pupil in enumerate(pupils):
            assert pupil == {"timestamp": idx}
