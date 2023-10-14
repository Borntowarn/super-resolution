from abc import ABC, abstractmethod
from multiprocessing import Queue
from multiprocessing.managers import DictProxy
from multiprocessing.sharedctypes import Synchronized

from PIL import Image, ImageChops, ImageStat


class Processor(ABC):
    def __init__(
        self, tasks_queue: Queue, processed_frames: DictProxy
    ) -> None:
        self.tasks_queue = tasks_queue
        self.processed_frames = processed_frames

    @abstractmethod
    def process(self):
        raise NotImplementedError

    @staticmethod
    def get_image_diff(image0: Image.Image, image1: Image.Image) -> float:
        difference_stat = ImageStat.Stat(ImageChops.difference(image0, image1))
        return sum(difference_stat.mean) / (len(difference_stat.mean) * 255) * 100