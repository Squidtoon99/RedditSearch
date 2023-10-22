import json
from tqdm import tqdm
from generate_embeddings import get_posts 
with open("RedditData/reddit_cleaned_cute_data.json", "r+", encoding="utf8") as f:
    for post in tqdm(get_posts()):
        if post.subreddit in ["cat", "cats", "dog", "dogs", "aww", "food", "dankmemes", "memes"]:
            json.dump({
                "title": post.title,
                "selftext": post.selftext,
                "image": post.image,
                "subreddit": post.subreddit,
                "author": post.author,
                "score": post.score,
                "date": post.date,
                "spoiler": post.spoiler,
                "id": post.get_id()
                }, f)
            f.write("\n")