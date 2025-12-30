"""Unit tests for converter module with mocked FFmpeg subprocess."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yt_audio_cli.converter import check_ffmpeg, transcode
from yt_audio_cli.errors import ConversionError, FFmpegNotFoundError


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
