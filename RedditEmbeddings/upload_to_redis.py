from redis import Redis

redis = Redis.from_url("redis://default:a0a37d10814d4bf894acf2249b85151a@us1-optimum-dassie-41399.upstash.io:41399")

from generate_embeddings import get_posts

for post in get_posts():
    redis.hmset(post.get_id(), {
        "subreddit": post.subreddit or "",
        "author": post.author or "", 
        "score": post.score or 0,
        "title": post.title or "",
        "date": post.date or 0,
        "selftext": post.selftext or "",
        "spoiler": int(post.spoiler) or 0,
        "image": post.image or ""
    })