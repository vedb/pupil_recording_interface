from .test_base import InterfaceTester

from pupil_recording_interface import OdometryInterface


class TestOdometryInterface(InterfaceTester):

    def setUp(self):
        """"""
        super(TestOdometryInterface, self).setUp()
        self.n_odometry = 4220

    def test_load_odometry(self):
        """"""
        t, c, p, q, v, w = OdometryInterface._load_odometry(self.folder)

        assert t.shape == (self.n_odometry,)
        assert c.shape == (self.n_odometry,)
        assert c.dtype == int
        assert p.shape == (self.n_odometry, 3)
        assert q.shape == (self.n_odometry, 4)
        assert v.shape == (self.n_odometry, 3)
        assert w.shape == (self.n_odometry, 3)

    def test_load_dataset(self):
        """"""
        # from recording
        ds = OdometryInterface(self.folder).load_dataset()

        self.assertDictEqual(dict(ds.sizes), {
            'time': self.n_odometry,
            'cartesian_axis': 3,
            'quaternion_axis': 4})

        assert set(ds.data_vars) == {
            'tracker_confidence', 'linear_velocity', 'angular_velocity',
            'linear_position', 'angular_position'}

        # bad odometry argument
        with self.assertRaises(ValueError):
            OdometryInterface(
                self.folder, source='not_supported').load_dataset()
