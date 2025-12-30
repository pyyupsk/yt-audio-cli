"""Unit tests for converter module with mocked FFmpeg subprocess."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_audio_cli.convert.transcoder import (
    _process_ffmpeg_progress,
    check_ffmpeg,
    transcode,
)
from yt_audio_cli.core import ConversionError, FFmpegNotFoundError


class TestCheckFFmpeg:
    """Tests for check_ffmpeg() function."""

    def test_ffmpeg_found(self) -> None:
        """Test when FFmpeg is available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/ffmpeg"
            assert check_ffmpeg() is True

    def test_ffmpeg_not_found(self) -> None:
        """Test when FFmpeg is not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            assert check_ffmpeg() is False


class TestTranscode:
    """Tests for transcode() function."""

    @pytest.fixture
    def input_file(self, temp_dir: Path) -> Path:
        """Create a mock input file."""
        input_path = temp_dir / "input.webm"
        input_path.touch()
        return input_path

    def test_transcode_success_mp3(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test successful MP3 transcoding."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    bitrate=320,
                )

                assert result is True
                assert mock_run.called

                # Verify ffmpeg command includes correct codec
                call_args = mock_run.call_args
                cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
                cmd_str = " ".join(cmd)
                assert "libmp3lame" in cmd_str
                assert "320k" in cmd_str

    def test_transcode_success_aac(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test successful AAC transcoding."""
        output_path = temp_dir / "output.aac"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="aac",
                    bitrate=256,
                )

                assert result is True
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                assert "aac" in cmd_str

    def test_transcode_success_opus(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test successful Opus transcoding."""
        output_path = temp_dir / "output.opus"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="opus",
                    bitrate=192,
                )

                assert result is True
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                assert "libopus" in cmd_str

    def test_transcode_success_wav(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test successful WAV transcoding (lossless)."""
        output_path = temp_dir / "output.wav"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="wav",
                    bitrate=None,  # WAV doesn't use bitrate
                )

                assert result is True
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                assert "pcm_s16le" in cmd_str
                # Bitrate should not be present for WAV
                assert "k" not in cmd_str or "-b:a" not in cmd_str

    def test_transcode_without_bitrate(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test transcoding without bitrate specified."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    bitrate=None,
                )

                assert result is True
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                # Should not contain bitrate flag
                assert "-b:a" not in cmd_str

    def test_transcode_with_metadata(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test transcoding with metadata embedding."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    bitrate=320,
                    embed_metadata=True,
                    metadata={"title": "Test Song", "artist": "Test Artist"},
                )

                assert result is True
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                assert "title=Test Song" in cmd_str
                assert "artist=Test Artist" in cmd_str

    def test_transcode_without_metadata(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test transcoding without metadata embedding."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    bitrate=320,
                    embed_metadata=False,
                    metadata={"title": "Test Song", "artist": "Test Artist"},
                )

                assert result is True
                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)
                # Metadata should not be present when embed_metadata=False
                assert "-metadata" not in cmd_str

    def test_transcode_ffmpeg_not_found(self, temp_dir: Path, input_file: Path) -> None:
        """Test transcode raises error when FFmpeg not found."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value=None):
            with pytest.raises(FFmpegNotFoundError):
                transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                )

    def test_transcode_failure(
        self, temp_dir: Path, input_file: Path, mock_subprocess_failure: MagicMock
    ) -> None:
        """Test transcode raises ConversionError on failure."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_failure

                with pytest.raises(ConversionError):
                    transcode(
                        input_path=input_file,
                        output_path=output_path,
                        audio_format="mp3",
                    )

    def test_transcode_creates_output_directory(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test transcode creates output directory if it doesn't exist."""
        nested_dir = temp_dir / "nested" / "output"
        output_path = nested_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                )

                assert result is True
                assert nested_dir.exists()


class TestTranscodeCodecMapping:
    """Tests for codec mapping in transcode()."""

    @pytest.fixture
    def input_file(self, temp_dir: Path) -> Path:
        """Create a mock input file."""
        input_path = temp_dir / "input.webm"
        input_path.touch()
        return input_path

    def test_mp3_uses_libmp3lame(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test MP3 format uses libmp3lame codec."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                transcode(
                    input_path=input_file,
                    output_path=temp_dir / "output.mp3",
                    audio_format="mp3",
                )

                cmd = mock_run.call_args[0][0]
                assert "-c:a" in cmd
                assert "libmp3lame" in cmd

    def test_aac_uses_aac_codec(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test AAC format uses aac codec."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                transcode(
                    input_path=input_file,
                    output_path=temp_dir / "output.aac",
                    audio_format="aac",
                )

                cmd = mock_run.call_args[0][0]
                assert "-c:a" in cmd
                # AAC is in the list
                assert "aac" in cmd

    def test_opus_uses_libopus(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test Opus format uses libopus codec."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                transcode(
                    input_path=input_file,
                    output_path=temp_dir / "output.opus",
                    audio_format="opus",
                )

                cmd = mock_run.call_args[0][0]
                assert "-c:a" in cmd
                assert "libopus" in cmd

    def test_wav_uses_pcm(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test WAV format uses PCM codec."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                transcode(
                    input_path=input_file,
                    output_path=temp_dir / "output.wav",
                    audio_format="wav",
                )

                cmd = mock_run.call_args[0][0]
                assert "-c:a" in cmd
                assert "pcm_s16le" in cmd


class TestProcessFFmpegProgress:
    """Tests for _process_ffmpeg_progress() helper function."""

    def test_parse_valid_out_time_ms(self) -> None:
        """Test parsing valid out_time_ms lines."""
        # Simulate FFmpeg progress output
        progress_output = [
            "bitrate=  64.9kbits/s\n",
            "total_size=40559\n",
            "out_time_ms=5000000\n",  # 5 seconds (in microseconds)
            "progress=continue\n",
        ]

        mock_process = MagicMock()
        mock_process.stdout = iter(progress_output)

        progress_values: list[float] = []

        def callback(seconds: float) -> None:
            progress_values.append(seconds)

        _process_ffmpeg_progress(mock_process, callback)

        assert len(progress_values) == 1
        assert progress_values[0] == 5.0  # NOSONAR

    def test_parse_multiple_progress_updates(self) -> None:
        """Test parsing multiple progress updates."""
        progress_output = [
            "out_time_ms=1000000\n",  # 1 second
            "progress=continue\n",
            "out_time_ms=2000000\n",  # 2 seconds
            "progress=continue\n",
            "out_time_ms=3000000\n",  # 3 seconds
            "progress=end\n",
        ]

        mock_process = MagicMock()
        mock_process.stdout = iter(progress_output)

        progress_values: list[float] = []

        _process_ffmpeg_progress(mock_process, lambda s: progress_values.append(s))

        assert progress_values == [1.0, 2.0, 3.0]

    def test_ignore_non_progress_lines(self) -> None:
        """Test that non-progress lines are ignored."""
        progress_output = [
            "bitrate=  128.0kbits/s\n",
            "total_size=123456\n",
            "out_time=00:00:05.000000\n",  # Human-readable format (not parsed)
            "speed= 10x\n",
            "progress=continue\n",
        ]

        mock_process = MagicMock()
        mock_process.stdout = iter(progress_output)

        progress_values: list[float] = []

        _process_ffmpeg_progress(mock_process, lambda s: progress_values.append(s))

        # No progress values because out_time_ms was not present
        assert progress_values == []

    def test_handle_invalid_out_time_ms(self) -> None:
        """Test handling invalid out_time_ms values gracefully."""
        progress_output = [
            "out_time_ms=invalid\n",  # Invalid value
            "out_time_ms=5000000\n",  # Valid value
            "out_time_ms=\n",  # Empty value
        ]

        mock_process = MagicMock()
        mock_process.stdout = iter(progress_output)

        progress_values: list[float] = []

        _process_ffmpeg_progress(mock_process, lambda s: progress_values.append(s))

        # Only the valid value should be captured
        assert progress_values == [5.0]

    def test_handle_no_stdout(self) -> None:
        """Test handling when stdout is None."""
        mock_process = MagicMock()
        mock_process.stdout = None

        progress_values: list[float] = []

        # Should not raise, just do nothing
        _process_ffmpeg_progress(mock_process, lambda s: progress_values.append(s))

        assert progress_values == []

    def test_ignore_negative_time(self) -> None:
        """Test that negative time values are ignored."""
        progress_output = [
            "out_time_ms=-1\n",  # Invalid negative
            "out_time_ms=1000000\n",  # Valid
        ]

        mock_process = MagicMock()
        mock_process.stdout = iter(progress_output)

        progress_values: list[float] = []

        _process_ffmpeg_progress(mock_process, lambda s: progress_values.append(s))

        assert progress_values == [1.0]


class TestTranscodeWithProgressCallback:
    """Tests for transcode() with progress_callback parameter."""

    @pytest.fixture
    def input_file(self, temp_dir: Path) -> Path:
        """Create a mock input file."""
        input_path = temp_dir / "input.webm"
        input_path.touch()
        return input_path

    def test_uses_popen_when_callback_provided(
        self, temp_dir: Path, input_file: Path
    ) -> None:
        """Test that Popen is used when progress_callback is provided."""
        output_path = temp_dir / "output.mp3"

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter(["out_time_ms=1000000\n"])
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=False)

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                progress_values: list[float] = []

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    bitrate=320,
                    progress_callback=lambda s: progress_values.append(s),
                )

                assert result is True
                assert mock_popen.called
                # Verify -progress flag is in command
                cmd = mock_popen.call_args[0][0]
                assert "-progress" in cmd
                assert "pipe:1" in cmd
                assert "-nostats" in cmd

    def test_uses_subprocess_run_without_callback(
        self, temp_dir: Path, input_file: Path, mock_subprocess_success: MagicMock
    ) -> None:
        """Test that subprocess.run is used when no callback provided."""
        output_path = temp_dir / "output.mp3"

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = mock_subprocess_success

                result = transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    bitrate=320,
                    progress_callback=None,
                )

                assert result is True
                assert mock_run.called
                # -progress should NOT be in command
                cmd = mock_run.call_args[0][0]
                assert "-progress" not in cmd

    def test_progress_callback_receives_updates(
        self, temp_dir: Path, input_file: Path
    ) -> None:
        """Test that progress callback receives time updates."""
        output_path = temp_dir / "output.mp3"

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter(
            [
                "out_time_ms=1000000\n",
                "out_time_ms=2000000\n",
                "out_time_ms=3000000\n",
            ]
        )
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = 0
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=False)

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.Popen", return_value=mock_process):
                progress_values: list[float] = []

                transcode(
                    input_path=input_file,
                    output_path=output_path,
                    audio_format="mp3",
                    progress_callback=lambda s: progress_values.append(s),
                )

                assert progress_values == [1.0, 2.0, 3.0]
