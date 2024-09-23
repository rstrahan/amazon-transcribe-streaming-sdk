import asyncio
import time
import sys

# This example uses aiofile for asynchronous file reads.
# It's not a dependency of the project but can be installed
# with `pip install aiofile`.
import aiofile

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from typing import AsyncIterable
from amazon_transcribe.model import StartStreamTranscriptionEventStream

"""
Here's an example of a custom event handler you can extend to
process the returned transcription results as needed. This
handler will simply print the text out to your interpreter.
"""


SAMPLE_RATE = 8000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 2
ENABLE_CHANNEL_IDENTIFICATION = True


# An example file can be found at tests/integration/assets/test.wav
# read audio path from command line arg
if len(sys.argv) >= 2:
    AUDIO_PATH = sys.argv[1]
else:
    AUDIO_PATH = "tests/integration/assets/test.wav"
# CHUNK_SIZE = 1024 * 8
# CHUNK_SIZE = 3200
# emulate the smaller average  chunk size seen in logs
CHUNK_SIZE = 640

REGION = "us-east-1"

start_time = time.time()


class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        elapsed_time = round((time.time() - start_time) * 1000)/1000
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                print(elapsed_time, result.result_id, result.start_time,
                      result.end_time, result.is_partial, alt.transcript)


# emulate delay seen in logs
VAR_DELAY = [
    142,
    79,
    1880,
    119,
    262,
    639,
    162,
    397,
    123,
    516,
    103,
    160,
    639,
    59,
    80,
    2,
    220,
    58,
    140,
    41,
    20,
    139,
    41,
    219,
    2,
    137,
    722,
    80,
    140,
    278,
    180,
    161,
    120,
    61,
    359,
    61,
    139,
    2,
    120,
    39,
    99,
    2,
    59,
    60,
    118,
    2,
    59,
    280,
    1,
    79,
    1,
    59,
    1,
    2,
    58,
    1,
    78,
    2,
    38,
    40,
    2,
    77,
    2,
    1,
    59,
    1,
    177,
    2,
    1,
    58,
    2,
    1,
    77,
    20,
    2,
    97,
    1,
    40,
    1,
    1,
    38,
    1,
    1,
    29599
]
i = 0


async def apply_variable_delay(
    stream: StartStreamTranscriptionEventStream,
    reader: AsyncIterable,
    bytes_per_sample: int,
    sample_rate: float,
    channel_nums: int,
) -> None:
    """Applies a delay when reading an audio file steam to simulate a real-time delay."""
    start_time = time.time()
    elapsed_audio_time = 0.0
    async for chunk in reader:
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
        """
        elapsed_audio_time += len(chunk) / (
            bytes_per_sample * sample_rate * channel_nums
        )
        """
        # variable delay
        global i
        elapsed_audio_time += VAR_DELAY[i]/1000
        # sleep to simulate real-time streaming
        wait_time = start_time + elapsed_audio_time - time.time()
        await asyncio.sleep(wait_time)
        print(f"wait_time: {wait_time}, Chunk size: {len(chunk)}")
        i += 1


async def basic_transcribe():
    # Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region=REGION)

    # Start transcription to generate our async stream
    transcribe_args = dict(
        language_code="en-US",
        media_sample_rate_hz=SAMPLE_RATE,
        media_encoding="pcm",
        number_of_channels=CHANNEL_NUMS,
        enable_channel_identification=ENABLE_CHANNEL_IDENTIFICATION,
    )
    print(f"Transcribe Args: {transcribe_args}")
    stream = await client.start_stream_transcription(
        **transcribe_args
    )

    async def write_chunks():
        # NOTE: For pre-recorded files longer than 5 minutes, the sent audio
        # chunks should be rate limited to match the realtime bitrate of the
        # audio stream to avoid signing issues.
        async with aiofile.AIOFile(AUDIO_PATH, "rb") as afp:
            reader = aiofile.Reader(afp, chunk_size=CHUNK_SIZE)
            await apply_variable_delay(
                stream, reader, BYTES_PER_SAMPLE, SAMPLE_RATE, CHANNEL_NUMS
            )
        await stream.input_stream.end_stream()
        print("done streaming")

    # Instantiate our handler and start processing events
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(), handler.handle_events())


loop = asyncio.get_event_loop()
loop.run_until_complete(basic_transcribe())
loop.close()
