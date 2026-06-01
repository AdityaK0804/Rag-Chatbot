def compute_engagement_rate(likes: int, comments: int, views: int) -> float | None:
    if views <= 0:
        return None
    return round(((likes + comments) / views) * 100, 4)