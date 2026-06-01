from langchain_text_splitters import RecursiveCharacterTextSplitter


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