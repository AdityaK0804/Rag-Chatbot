from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_metadata_fallback_chunk(data: dict) -> str:
    return "\n".join([
        f"Title: {data.get('title') or ''}",
        f"Creator: {data.get('creator') or ''}",
        f"Platform: {data.get('platform') or ''}",
        f"Description: {data.get('description') or ''}",
        f"Views: {data.get('views') if data.get('views') is not None else ''}",
        f"Followers: {data.get('follower_count') if data.get('follower_count') is not None else ''}",
        f"Likes: {data.get('likes') if data.get('likes') is not None else ''}",
        f"Comments: {data.get('comments') if data.get('comments') is not None else ''}",
        f"Duration: {data.get('duration') if data.get('duration') is not None else ''}",
        "",
        "Transcript Status: Unavailable",
    ])


def get_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)
