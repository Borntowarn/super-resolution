import os
os.environ["LOGURU_LEVEL"] = "INFO"

import time
import math
import sys
from enum import Enum
from multiprocessing import Manager, Pool, Queue
from pathlib import Path
from typing import  Callable, Optional

import ffmpeg
import cv2
from loguru import logger
from rich.console import Console
from rich.file_proxy import FileProxy
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from .processor import Processor

from .decoder import VideoDecoder, VideoDecoderThread
from .encoder import VideoEncoder
from .upscaler import UpscalerProcessor


# format string for Loguru loggers
LOGURU_FORMAT = (
    "<green>{time:HH:mm:ss.SSSSSS!UTC}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


class ProcessingSpeedColumn(ProgressColumn):
    """Custom progress bar column that displays the processing speed"""

    def render(self, task: Task) -> Text:
        speed = task.finished_speed or task.speed
        return Text(
            f"{round(speed, 2) if isinstance(speed, float) else '?'} FPS",
            style="progress.data.speed",
        )


class Video2X:
    def __init__(self, progress_callback: Optional[Callable] = None) -> None:
        self.progress_callback = progress_callback

    @staticmethod
    def _get_video_info(path: Path) -> tuple:
        # probe video file info
        logger.info("Reading input video information")
        logger.info(path)
        for stream in ffmpeg.probe(path)["streams"]:
            if stream["codec_type"] == "video":
                video_info = stream
                break
        else:
            raise RuntimeError("unable to find video stream")

        # get total number of frames to be processed
        capture = cv2.VideoCapture(str(path))

        # check if file is opened successfully
        if not capture.isOpened():
            raise RuntimeError("OpenCV has failed to open the input file")

        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_rate = capture.get(cv2.CAP_PROP_FPS)

        return video_info["width"], video_info["height"], total_frames, frame_rate

    def _run(
        self,
        input_path: Path,
        width: int,
        height: int,
        total_frames: int,
        frame_rate: float,
        output_path: Path,
        output_width: int,
        output_height: int,
        processes: int,
        processing_settings: tuple,
    ) -> None:

        # record original STDOUT and STDERR for restoration
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        # create console for rich's Live display
        console = Console()

        # redirect STDOUT and STDERR to console
        sys.stdout = FileProxy(console, sys.stdout)
        sys.stderr = FileProxy(console, sys.stderr)

        # re-add Loguru to point to the new STDERR
        logger.remove()
        logger.add(sys.stderr, colorize=True, format=LOGURU_FORMAT)

        # TODO: add docs
        tasks_queue = Queue(maxsize=processes * 10)
        # logger.info(tasks_queue.)
        processed_frames = Manager().dict()

        # set up and start decoder thread
        logger.info("Starting video decoder")
        decoder = VideoDecoder(
            input_path,
            width,
            height,
            frame_rate,
        )
        decoder_thread = VideoDecoderThread(tasks_queue, decoder, processing_settings)
        decoder_thread.start()

        # set up and start encoder thread
        logger.info("Starting video encoder")
        encoder = VideoEncoder(
            input_path,
            frame_rate,
            output_path,
            output_width,
            output_height,
        )

        # create a pool of processor processes to process the queue
        processor: Processor = UpscalerProcessor(
            tasks_queue, processed_frames
        )
        processor_pool = Pool(processes, processor.process)

        # create progress bar
        self.progress = Progress(
            "[progress.description]{task.description}",
            BarColumn(complete_style="blue", finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "[color(240)]({task.completed}/{task.total})",
            ProcessingSpeedColumn(),
            TimeElapsedColumn(),
            "<",
            TimeRemainingColumn(),
            console=console,
            speed_estimate_period=300.0,
            disable=True,
        )
        task = self.progress.add_task(
            f"[cyan]Upscaling", total=total_frames
        )

        # a temporary variable that stores the exception
        exceptions = []

        try:
            # let the context manager automatically stop the progress bar
            with self.progress:
                frame_index = 0
                while frame_index < total_frames:
                    current_frame = processed_frames.get(frame_index)

                    if current_frame is None:
                        time.sleep(0.1)
                        continue

                    # show the progress bar after the processing starts
                    # reduces speed estimation inaccuracies and print overlaps
                    if frame_index == 0:
                        self.progress.disable = False
                        self.progress.start()

                    if current_frame is True:
                        encoder.write(processed_frames.get(frame_index - 1))
                    else:
                        encoder.write(current_frame)

                        if frame_index > 0:
                            del processed_frames[frame_index - 1]

                    self.progress.update(task, completed=frame_index + 1)
                    if self.progress_callback is not None:
                        self.progress_callback(frame_index + 1, total_frames)
                    frame_index += 1

        except Exception as error:
            logger.exception(error)
            exceptions.append(error)

        else:
            logger.info("Processing has completed")
            logger.info("Writing video trailer")

        finally:

            # if errors have occurred, kill the FFmpeg processes
            if len(exceptions) > 0:
                decoder.kill()
                encoder.kill()

            # stop the decoder
            decoder_thread.stop()
            decoder_thread.join()

            # clear queue and signal processors to exit
            # multiprocessing.Queue has no Queue.queue.clear
            while tasks_queue.empty() is not True:
                tasks_queue.get()
            for _ in range(processes):
                tasks_queue.put(None)

            # close and join the process pool
            processor_pool.close()
            processor_pool.join()

            # stop the encoder
            encoder.join()

            # restore original STDOUT and STDERR
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            # re-add Loguru to point to the restored STDERR
            logger.remove()
            logger.add(sys.stderr, colorize=True, format=LOGURU_FORMAT)

            # raise the first collected error
            if len(exceptions) > 0:
                raise exceptions[0]

    def upscale(
        self,
        model_name,
        input_path: Path,
        output_path: Path,
        output_width: int,
        output_height: int,
        processes: int,
        threshold: float,
    ) -> None:
        # get basic video information
        width, height, total_frames, frame_rate = self._get_video_info(input_path)

        # automatically calculate output width and height if only one is given
        if output_width == 0 or output_width is None:
            output_width = output_height / height * width

        elif output_height == 0 or output_width is None:
            output_height = output_width / width * height

        # sanitize output width and height to be divisible by 2
        output_width = int(math.ceil(output_width / 2.0) * 2)
        output_height = int(math.ceil(output_height / 2.0) * 2)

        # start processing
        self._run(
            input_path,
            width,
            height,
            total_frames,
            frame_rate,
            output_path,
            output_width,
            output_height,
            processes,
            (
                model_name,
                output_width,
                output_height,
                threshold,
            ),
        )