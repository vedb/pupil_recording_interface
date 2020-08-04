from pupil_recording_interface.encoder import VideoEncoderFFMPEG


class TestVideoEncoderFFMPEG:
    def test_get_ffmpeg_cmd(self):
        """"""
        cmd = VideoEncoderFFMPEG._get_ffmpeg_cmd(
            "test.mp4", (1280, 720), 30.0, "libx264", "bgr24",
        )

        assert cmd == [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-an",
            "-r",
            "30.0",
            "-f",
            "rawvideo",
            "-s",
            "1280x720",
            "-pix_fmt",
            "bgr24",
            "-i",
            "pipe:",
            "-preset",
            "ultrafast",
            "-crf",
            "18",
            "-c:v",
            "libx264",
            "test.mp4",
        ]
