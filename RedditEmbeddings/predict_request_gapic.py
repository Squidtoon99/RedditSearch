# Copyright 2023 Google LLC.
# SPDX-License-Identifier: Apache-2.0
from absl import app
from absl import flags
import base64

# Need to do pip install google-cloud-aiplatform for the following two imports.
# Also run: gcloud auth application-default login.
from google.cloud import aiplatform
from google.protobuf import struct_pb2
import sys
import time
import typing


_IMAGE_FILE = flags.DEFINE_string("image_file", None, "Image filename")
_TEXT = flags.DEFINE_string("text", None, "Text to input")
_PROJECT = flags.DEFINE_string("project", None, "Project id")


# Inspired from https://stackoverflow.com/questions/34269772/type-hints-in-namedtuple.
class EmbeddingResponse(typing.NamedTuple):
    text_embedding: typing.Sequence[float]
    image_embedding: typing.Sequence[float]


class EmbeddingPredictionClient:
    """Wrapper around Prediction Service Client."""

    def __init__(
        self,
        project: str,
        location: str = "us-central1",
        api_regional_endpoint: str = "us-central1-aiplatform.googleapis.com",
    ):
        client_options = {"api_endpoint": api_regional_endpoint}
        # Initialize client that will be used to create and send requests.
        # This client only needs to be created once, and can be reused for multiple requests.
        self.client = aiplatform.gapic.PredictionServiceClient(
            client_options=client_options
        )
        self.location = location
        self.project = project

    def get_embedding(self, text: str = None, image_bytes: bytes = None):
        if not text and not image_bytes:
            raise ValueError("At least one of text or image_bytes must be specified.")

        instance = struct_pb2.Struct()
        if text:
            instance.fields["text"].string_value = text

        if image_bytes:
            encoded_content = base64.b64encode(image_bytes).decode("utf-8")
            image_struct = instance.fields["image"].struct_value
            image_struct.fields["bytesBase64Encoded"].string_value = encoded_content

        instances = [instance]
        endpoint = (
            f"projects/{self.project}/locations/{self.location}"
            "/publishers/google/models/multimodalembedding@001"
        )
        response = self.client.predict(endpoint=endpoint, instances=instances)

        text_embedding = None
        if text:
            text_emb_value = response.predictions[0]["textEmbedding"]
            text_embedding = [v for v in text_emb_value]

        image_embedding = None
        if image_bytes:
            image_emb_value = response.predictions[0]["imageEmbedding"]
            image_embedding = [v for v in image_emb_value]

        return EmbeddingResponse(
            text_embedding=text_embedding, image_embedding=image_embedding
        )


def main(argv):
    image_file_contents = None
    if _IMAGE_FILE.value:
        with open(_IMAGE_FILE.value, "rb") as f:
            image_file_contents = f.read()

    # client can be reused.
    client = EmbeddingPredictionClient(project=_PROJECT.value)

    start = time.time()
    response = client.get_embedding(text=_TEXT.value, image_bytes=image_file_contents)
    end = time.time()

    print(response)
    print("Time taken: ", end - start)


if __name__ == "__main__":
    app.run(main)
