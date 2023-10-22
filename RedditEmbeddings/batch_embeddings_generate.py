from vertexai.preview.language_models import TextEmbeddingModel

textembedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko")
batch_prediction_job = textembedding_model.batch_predict(
  dataset=["gs://reddit-search-data/reddit_cleaned_data.json"],
  destination_uri_prefix="gs://reddit-search-data/tmp/2023-10-22-vertex-LLM-Batch-Prediction/result0",
)
print(batch_prediction_job.display_name)
print(batch_prediction_job.resource_name)
print(batch_prediction_job.state)