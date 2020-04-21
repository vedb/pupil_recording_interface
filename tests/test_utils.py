from pupil_recording_interface.utils import multiprocessing_deque


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
