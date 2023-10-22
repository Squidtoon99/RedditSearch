from enum import Enum
import json
from absl import app
from google.cloud import aiplatform
import base64
from google.protobuf import struct_pb2
import typing
import requests

class EmbeddingResponse(typing.NamedTuple):
    text_embedding: typing.Sequence[float]
    content_embedding: typing.Sequence[float]


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
    
    def _get_instances(self, post: "Post"):
        instances = []
        if post.get_type() == PostType.TEXT:
            title_instance = struct_pb2.Struct()
            title_instance.fields["text"].string_value = post.title
            instances.append(title_instance)
            
            if (post.selftext):
                content_instance = struct_pb2.Struct()
                content_instance.fields["text"].string_value = post.selftext
                instances.append(content_instance)
        elif post.get_type() == PostType.IMAGE:
            
            image_instance = struct_pb2.Struct()
            image_instance.fields["text"].string_value = post.title
            if (post.image is None):
                return instances
            image_bytes = post.get_image_bytes()
            encoded_content = base64.b64encode(image_bytes).decode("utf-8")
            image_struct = image_instance.fields['image'].struct_value
            image_struct.fields['bytesBase64Encoded'].string_value = encoded_content
            instances.append(image_instance)
        return instances
        
    def get_embedding(self, post: "Post"):

        instances = self._get_instances(post=post)
        
        endpoint = (f"projects/{self.project}/locations/{self.location}"
      "/publishers/google/models/multimodalembedding@001")
        print("endpoint: ", endpoint, "instances: ", instances)
        predictions = []
        
        for instance in instances:
            response = self.client.predict(endpoint=endpoint, instances=[instance])
            predictions.extend(list(response.predictions))

        # The response includes a list of results, since we only sent one
        print(predictions)
        text_embedding = None
        
        
        
        if post.title:    
            title_emb_value = predictions[0]['textEmbedding']
            text_embedding = [v for v in title_emb_value]

        content_embedding = None
        if post.image:    
            image_emb_value = predictions[0]['imageEmbedding']
            content_embedding = [v for v in image_emb_value]

        elif post.selftext:
            text_emb_value = predictions[1]['textEmbedding']
            content_embedding = [v for v in text_emb_value]
            
        return EmbeddingResponse(
            text_embedding=text_embedding,
            content_embedding=content_embedding
        )
        
        
class PostType(Enum):
    TEXT = "text"
    IMAGE = "image"

class Post(object):
    def __init__(self, data: dict):

        self._id = data["id"]
        self.subreddit = data["subreddit"]
        self.author = data["author"]
        self.score = data["score"]
        self.title = data["title"]
        self.date = data["date"]
        self.selftext = data["selftext"]
        self.spoiler = data["spoiler"]
        self.image = data.get("image")
    
    def is_removed(self):
        return self.selftext and self.selftext in ["[removed]", "[deleted]"]
    
    def get_type(self):
        if self.image is None:
            return PostType.TEXT
        else:
            return PostType.IMAGE
    
    def get_id(self):
        return self._id
    
    @property 
    def selftext(self):
        return self._selftext

    @selftext.setter
    def selftext(self, value):
        self._selftext = value.replace("\n", " ").replace("\t", " ")[:1000]
    
    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        self._title = value.replace("\n", " ").replace("\t", " ")[:1000]
        
    @classmethod
    def from_json(cls, data: str):
        return cls(json.loads(data))
    
    def __repr__(self):
        return f"Post(id={self._id}, subreddit={self.subreddit}, author={self.author}, score={self.score}, title={self.title}, date={self.date}, selftext={self.selftext}, spoiler={self.spoiler} image={self.image[:30] if self.image else None})"
    
    def get_image_bytes(self):
        if not self.image:
            return None 
        
        # http fetch the image as a url
        response = requests.get(self.image, timeout=5)
        print("response: ", response)
        # return the bytes of the image if valid 
        if response.status_code == 200:
            return response.content
        else:
            print("Error response: ", response.status_code, str(response.content)[:200])
            return response.raise_for_status()

    def has_embedding(self):
        with open("RedditData/reddit_embeddings_cute.json", "r+", encoding="utf8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                except json.decoder.JSONDecodeError:
                    continue
                if self.get_id().startswith(data['id']):
                    return True
        return False
    
    def save_embedding(self, embedding: EmbeddingResponse):
        with open('RedditData/reddit_embeddings_cute.json', '+a', encoding='utf8') as f:
            if embedding.text_embedding:
                json.dump({
                    "id": f"{self._id}_title",
                    "embedding": embedding.text_embedding
                }, f)
                f.write("\n")
            if embedding.content_embedding:
                json.dump({
                    "id": f"{self._id}_content",
                    "embedding": embedding.content_embedding
                }, f)
                f.write("\n")
        
            
def get_posts():
    with open("RedditData/reddit_cleaned_cute_data.json", "r", encoding="utf8") as f:
        for line in f:
            yield Post.from_json(line)

def main(argv):
    # import os
    
    project_id = "rosy-hangout-402720" # os.getenv("PROJECT_ID")
    
    if not project_id:
        raise ValueError("PROJECT_ID environment variable must be set.")
    
    client = EmbeddingPredictionClient(project=project_id)
    
    for post in get_posts():
        if post.is_removed():
            print("post %s is removed" % post.get_id())
            continue 
        
        if post.has_embedding():
            print("post %s already has embedding" % post.get_id())
            continue
        
        allowed_subreddits = ["cats", "cat", "dogs", "dog", "aww", ]
        try:
            embeddings = client.get_embedding(post)
        except requests.exceptions.ReadTimeout:
            print("Timeout error, skipping post")
            continue
        except requests.exceptions.HTTPError as err:
            print("deleted post skipping...", str(err), post.get_id())
        except Exception as err:
            allowed = ["Text field must be smaller than 1024 characters"]
            for allow_str in allowed:
                if allow_str in str(err):
                    print("skipping post", post.get_id(), str(err))
                    continue
        else:
            # save embeddings
            post.save_embedding(embeddings)

        
if __name__ == "__main__":
    app.run(main)