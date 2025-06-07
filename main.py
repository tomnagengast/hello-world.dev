import os
import logging
import pygame
from typing import IO
from io import BytesIO
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not ELEVENLABS_API_KEY:
    logging.error("ELEVENLABS_API_KEY environment variable not set")
    raise ValueError("ELEVENLABS_API_KEY environment variable is required")

logging.info("Initializing pygame mixer for audio playback")
pygame.mixer.init()

logging.info("Initializing ElevenLabs client")
elevenlabs = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)


def text_to_speech_stream(text: str) -> IO[bytes]:
    logging.info(
        f"Starting text-to-speech conversion for text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
    )

    try:
        # Perform the text-to-speech conversion
        logging.debug("Calling ElevenLabs text_to_speech.stream API")
        response = elevenlabs.text_to_speech.stream(
            voice_id="pNInz6obpgDQGcFmaJgB",  # Adam pre-made voice
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_flash_v2_5",
            # Optional voice settings that allow you to customize the output
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
                speed=1.2,
            ),
        )
        logging.debug("Successfully received response from ElevenLabs API")

        # Create a BytesIO object to hold the audio data in memory
        audio_stream = BytesIO()
        logging.debug("Created BytesIO stream for audio data")

        # Write each chunk of audio data to the stream
        chunk_count = 0
        total_bytes = 0
        for chunk in response:
            if chunk:
                chunk_size = len(chunk)
                audio_stream.write(chunk)
                chunk_count += 1
                total_bytes += chunk_size
                logging.debug(f"Processed chunk {chunk_count}: {chunk_size} bytes")

        logging.info(
            f"Audio conversion completed: {chunk_count} chunks, {total_bytes} total bytes"
        )

        # Reset stream position to the beginning
        audio_stream.seek(0)
        logging.debug("Reset audio stream position to beginning")

        # Return the stream for further use
        return audio_stream

    except Exception as e:
        logging.error(f"Error during text-to-speech conversion: {str(e)}")
        raise


def play_audio_stream(audio_stream: IO[bytes]) -> None:
    """Play audio stream through speakers using pygame mixer."""
    logging.info("Starting audio playback")

    try:
        # Reset stream position to beginning
        audio_stream.seek(0)

        # Load the audio data into pygame mixer
        logging.debug("Loading audio data into pygame mixer")
        pygame.mixer.music.load(audio_stream)

        # Play the audio
        pygame.mixer.music.play()
        logging.info("Audio playback started")

        # Wait for playback to complete
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)  # Wait 100ms between checks

        logging.info("Audio playback completed")

    except Exception as e:
        logging.error(f"Error during audio playback: {str(e)}")
        raise


if __name__ == "__main__":
    logging.info("Starting application")
    try:
        audio_stream = text_to_speech_stream("Hello World")
        # Get the current position to determine stream size
        current_pos = audio_stream.tell()
        audio_stream.seek(0, 2)  # Seek to end
        stream_size = audio_stream.tell()
        audio_stream.seek(current_pos)  # Restore position
        logging.info(f"Successfully generated audio stream with {stream_size} bytes")

        # Play the audio through speakers
        play_audio_stream(audio_stream)

    except Exception as e:
        logging.error(f"Application failed: {str(e)}")
        raise
