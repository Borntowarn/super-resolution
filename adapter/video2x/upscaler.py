import math
import time


from PIL import Image
from .processor import Processor

import torch
import numpy as np
import torchvision.transforms as T
import tritonclient.grpc as grpcclient
from PIL import Image


def inference(triton_client, model_name, input0_data):
    inputs = []
    outputs = []
    inputs.append(grpcclient.InferInput("input", [*input0_data.shape], "FP16"))

    # Initialize the data
    inputs[0].set_data_from_numpy(input0_data)
    outputs.append(grpcclient.InferRequestedOutput("output"))
    
    results = triton_client.infer(
        model_name,
        inputs,
        outputs=outputs
    )

    return results


class Upscaler:
    triton_client = grpcclient.InferenceServerClient(url="tritonserver:8001", verbose=False)

    def upscale_image(
        self,
        model_name,
        image: Image.Image,
        output_width: int,
        output_height: int,
    ) -> Image.Image:
        time.sleep(0.01)
        # image = T.Compose([T.ToTensor()])(image).unsqueeze(0).numpy().astype(np.float16)
        # image = inference(self.triton_client, model_name, image)
        # image = image.as_numpy("output").astype(np.float32)
        # image = np.clip(image, 0, 1)
        # image = T.ToPILImage()(torch.tensor(image[0]))

        return image.resize((output_width, output_height), Image.Resampling.LANCZOS)
        # return image


class UpscalerProcessor(Processor, Upscaler):
    def process(self) -> None:
        task = self.tasks_queue.get()
        while task is not None:
            # unpack the task's values
            (
                frame_index,
                previous_frame,
                current_frame,
                (model_name, output_width, output_height, threshold),
            ) = task

            # calculate the %diff between the current frame and the previous frame
            difference_ratio = 0
            if previous_frame is not None:
                difference_ratio = self.get_image_diff(
                    previous_frame, current_frame
                )

            # if the difference is lower than threshold, skip this frame
            if difference_ratio < threshold:
                # make the current image the same as the previous result
                self.processed_frames[frame_index] = True

            # if the difference is greater than threshold
            # process this frame
            else:
                self.processed_frames[frame_index] = self.upscale_image(
                    model_name, current_frame, output_width, output_height
                )

            task = self.tasks_queue.get()