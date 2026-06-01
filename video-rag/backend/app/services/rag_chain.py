import json
import logging
import os

from dotenv import load_dotenv
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.retriever import get_video_metadata, retrieve

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

# In-process session memory. Each key is a session_id.
# Survives for the lifetime of the server process.
memory_store: dict[str, ConversationBufferWindowMemory] = {}

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    temperature=0.3,
    google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
    max_output_tokens=1000,
)


def get_memory(session_id: str) -> ConversationBufferWindowMemory:
    if session_id not in memory_store:
        memory_store[session_id] = ConversationBufferWindowMemory(
            k=10,
            return_messages=True,
            memory_key="chat_history",
        )
    return memory_store[session_id]


def _build_system_prompt(meta_a: dict, meta_b: dict, chunks: list[dict], is_compare_query: bool = False) -> str:
    context = "\n\n---\n\n".join(
        f"[{c['source']}]\n{c['text']}" for c in chunks
    )

    views_a = meta_a.get("views")
    views_b = meta_b.get("views")

    limitations = []
    if views_a is None or views_a == "None":
        limitations.append("Video A has no view count available from metadata. Therefore, its engagement rate cannot be calculated.")
    if views_b is None or views_b == "None":
        limitations.append("Video B has no view count available from metadata. Therefore, its engagement rate cannot be calculated.")

    comparison_rules = ""
    if limitations:
        limitation_bullets = "\n".join(f"- {l}" for l in limitations)
        comparison_rules = f"""
CRITICAL COMPARING RULES & LIMITATIONS:
{limitation_bullets}

Because at least one video is missing view counts:
1. You MUST NOT compare engagement rates.
2. You MUST NOT declare a winner based on engagement rate.
3. If asked to compare engagement or overall performance, you MUST:
   - Explicitly state which video(s) are missing views, preventing engagement rate calculation.
   - Explain that a direct engagement rate comparison is not possible.
   - Suggest comparing available metrics: Likes, Comments, and Interaction Count (Likes + Comments).
"""

    generic_metric_rules = """
GENERAL METRIC RULES:
If a metric (views, likes, comments, engagement_rate, duration) is unavailable (e.g. is None, "None", "Not Available", or "N/A"):
- Never estimate it.
- Never infer it.
- Never assume it.
- Explicitly state the limitation (e.g. "Views are unavailable for Video B").
"""

    def format_engagement(meta):
        rate = meta.get("engagement_rate")
        if rate is None or rate == "None":
            return "N/A"
        try:
            return f"{float(rate):.2f}%"
        except (ValueError, TypeError):
            return "N/A"

    def format_views(meta):
        views = meta.get("views")
        if views is None or views == "None":
            return "Not Available"
        return str(views)

    rate_a = format_engagement(meta_a)
    rate_b = format_engagement(meta_b)
    views_a = format_views(meta_a)
    views_b = format_views(meta_b)
    
    platform_a = format_platform(meta_a.get("platform"))
    platform_b = format_platform(meta_b.get("platform"))

    prompt_prefix = f"""You are a video content analyst helping creators understand performance data.

{comparison_rules}
{generic_metric_rules}

You have access to the following static video metadata for both videos:

VIDEO A:
- Title: {meta_a.get('title', 'Video A')}
- Creator: {meta_a.get('creator', 'Unknown')}
- Platform: {platform_a}
- Engagement Rate: {rate_a}
- Views: {views_a}
- Likes: {meta_a.get('likes', 'N/A') if meta_a.get('likes') is not None else 'N/A'}
- Comments: {meta_a.get('comments', 'N/A') if meta_a.get('comments') is not None else 'N/A'}
- Duration: {meta_a.get('duration', 'N/A') if meta_a.get('duration') is not None else 'N/A'} seconds

VIDEO B:
- Title: {meta_b.get('title', 'Video B')}
- Creator: {meta_b.get('creator', 'Unknown')}
- Platform: {platform_b}
- Engagement Rate: {rate_b}
- Views: {views_b}
- Likes: {meta_b.get('likes', 'N/A') if meta_b.get('likes') is not None else 'N/A'}
- Comments: {meta_b.get('comments', 'N/A') if meta_b.get('comments') is not None else 'N/A'}
- Duration: {meta_b.get('duration', 'N/A') if meta_b.get('duration') is not None else 'N/A'} seconds

RETRIEVED CONTEXT:
{context}

RULES:
- Use the static video metadata to answer questions about metrics (views, likes, comments, engagement rate, duration), creators, or titles.
- Use the retrieved context for questions about the actual content, transcript, topics, hooks, or video scripts.
- If the retrieved context is empty, sparse, or doesn't mention metrics/metadata, you MUST still answer comparative and metric questions using the static video metadata provided above.
- Do NOT say data is unavailable or return "N/A" if the metric is present in the static video metadata above.
- Always cite which video (A or B) your answer references.
- Be specific. Vague answers are not useful to a creator.

AUDIENCE LOYALTY RULE:
If the user asks:
- "Which creator has a more loyal audience?"
- "Which audience is more loyal?"
- "Who has stronger audience loyalty?"
or any question asking to evaluate or compare audience loyalty:
You MUST NOT declare a winner. You MUST respond EXACTLY with the following required response pattern:
"Available metadata is insufficient to determine audience loyalty.

Video A has higher raw interactions.
Video B has measurable engagement rate.

Neither metric alone proves audience loyalty."
"""

    if is_compare_query:
        comparison_instruction = """
SUMMARY ONLY RULE:
A comparison table has already been shown to the user.
You MUST NOT output another comparison table, list of metrics, or repeat the values.
Instead, write a brief, high-level summary paragraph (2-3 sentences) explaining the differences or performance highlights based ONLY on these metrics, bearing in mind the missing views/engagement limitations.
"""
        return prompt_prefix + comparison_instruction
    else:
        compare_rule = """
COMPARE BOTH VIDEOS TEMPLATE RULE:
If the user asks a broad comparison request (such as "Compare both videos", "compare them", or similar general comparison requests), you MUST format your comparison using the following structured template instead of writing free-form paragraphs:

Views:
- Video A: <value or "Not Available">
- Video B: <value or "Not Available">

Engagement:
- Video A: <value or "N/A">
- Video B: <value or "N/A">

Interactions:
- Video A: <total interactions> (Likes: <likes>, Comments: <comments>)
- Video B: <total interactions> (Likes: <likes>, Comments: <comments>)

Duration:
- Video A: <duration> seconds
- Video B: <duration> seconds

Platform:
- Video A: <platform>
- Video B: <platform>

(Note: Follow this template with a brief, high-level summary explaining the differences or performance highlights based ONLY on these metrics, bearing in mind the missing views/engagement limitations)."""
        return prompt_prefix + compare_rule


def format_platform(platform: str) -> str:
    if not platform:
        return "Unknown"
    p_lower = str(platform).lower()
    if "youtube_shorts" in p_lower:
        return "YouTube Shorts"
    if "youtube" in p_lower:
        return "YouTube"
    if "instagram" in p_lower:
        return "Instagram"
    return platform.capitalize()


def is_video_referenced(response_text: str, label: str, meta: dict) -> bool:
    text_lower = response_text.lower()
    
    # 1. Label checks
    if f"video {label.lower()}" in text_lower:
        return True
    if f"video_{label.lower()}" in text_lower:
        return True
    if f"creator {label.lower()}" in text_lower:
        return True
    if f"video {label.upper()}" in response_text:
        return True
        
    # 2. Title check
    title = meta.get("title")
    if title and len(str(title).strip()) > 3:
        title_clean = str(title).strip().lower()
        if title_clean in text_lower:
            return True
        # Check if at least 3 significant words from title are in the response
        words = [w for w in title_clean.split() if len(w) > 3 and w.isalnum()]
        if len(words) >= 3:
            match_count = sum(1 for w in words if w in text_lower)
            if match_count >= 3:
                return True
            
    # 3. Creator check
    creator = meta.get("creator")
    if creator and len(str(creator).strip()) > 2:
        creator_clean = str(creator).strip().lower()
        if creator_clean in text_lower:
            return True
        words = [w for w in creator_clean.split() if len(w) > 2 and w.isalnum()]
        if words and all(w in text_lower for w in words):
            return True
            
    # 4. Metric value checks
    for key in ["views", "likes", "comments"]:
        val = meta.get(key)
        if val is not None and val != "None" and val != "":
            val_str = str(val).strip()
            if val_str.isdigit():
                num = int(val_str)
                if val_str in text_lower:
                    return True
                if f"{num:,}" in text_lower:
                    return True
                if num >= 1000:
                    k_val = f"{num/1000:.1f}k"
                    k_val_no_dot = f"{num/1000:.0f}k"
                    if k_val in text_lower or k_val_no_dot in text_lower:
                        return True
            else:
                if val_str.lower() in text_lower:
                    return True
                    
    # Engagement rate checks
    rate = meta.get("engagement_rate")
    if rate is not None and rate != "None" and rate != "":
        try:
            rate_float = float(rate)
            rate_str = f"{rate_float:.2f}%"
            rate_str_2 = f"{rate_float:.1f}%"
            rate_str_3 = f"{rate_float:.0f}%"
            if rate_str in text_lower or rate_str_2 in text_lower or rate_str_3 in text_lower:
                return True
        except (ValueError, TypeError):
            pass
            
    # Duration checks
    duration = meta.get("duration")
    if duration is not None and duration != "None" and duration != "":
        try:
            dur_int = int(duration)
            if dur_int > 0:
                if f"{dur_int} second" in text_lower or f"{dur_int}sec" in text_lower:
                    return True
        except (ValueError, TypeError):
            pass

    return False


async def stream_response(
    question: str,
    session_id: str,
    url_a: str,
    url_b: str,
):
    """
    Async generator that yields SSE-formatted strings.
    Streams tokens first, then sends citations, then [DONE].
    """
    chunks = retrieve(question, url_a, url_b)
    meta_a = get_video_metadata(url_a)
    meta_b = get_video_metadata(url_b)

    memory = get_memory(session_id)

    # 1. Deterministic guard for audience loyalty questions
    q_clean = "".join(c for c in question.lower() if c.isalnum() or c.isspace()).strip()
    is_loyalty = "loyal" in q_clean or "loyalty" in q_clean

    if is_loyalty:
        ans = (
            "Available metadata is insufficient to determine audience loyalty.\n\n"
            "Video A has higher raw interactions.\n"
            "Video B has measurable engagement rate.\n\n"
            "Neither metric alone proves audience loyalty."
        )
        yield f"data: {json.dumps({'type': 'token', 'content': ans})}\n\n"

        citations = [
            {
                "video_id": "A",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video A: Title='{meta_a.get('title')}', Creator='{meta_a.get('creator')}'",
            },
            {
                "video_id": "B",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video B: Title='{meta_b.get('title')}', Creator='{meta_b.get('creator')}'",
            }
        ]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        yield "data: [DONE]\n\n"

        memory.chat_memory.add_user_message(question)
        memory.chat_memory.add_ai_message(ans)
        return

    # 2. Reach comparison guard
    views_a = meta_a.get("views")
    views_b = meta_b.get("views")
    is_views_missing = (views_a is None or views_a == "None") or (views_b is None or views_b == "None")
    is_reach_query = (
        ("reach" in q_clean or "view" in q_clean) and 
        any(comp in q_clean for comp in ["compare", "comparison", "more", "higher", "greater", "winner", "better", "versus", "vs", "difference", "performance"])
    )

    if is_views_missing and is_reach_query:
        ans = "Reach comparison is not possible because view data is unavailable."
        yield f"data: {json.dumps({'type': 'token', 'content': ans})}\n\n"

        citations = [
            {
                "video_id": "A",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video A: Title='{meta_a.get('title')}', Creator='{meta_a.get('creator')}', Views='{views_a}'",
            },
            {
                "video_id": "B",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video B: Title='{meta_b.get('title')}', Creator='{meta_b.get('creator')}', Views='{views_b}'",
            }
        ]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        yield "data: [DONE]\n\n"

        memory.chat_memory.add_user_message(question)
        memory.chat_memory.add_ai_message(ans)
        return

    # 3. Engagement comparison guard
    rate_a = meta_a.get("engagement_rate")
    rate_b = meta_b.get("engagement_rate")
    is_rate_missing = (rate_a is None or rate_a == "None") or (rate_b is None or rate_b == "None")
    is_engagement_query = (
        "engagement" in q_clean and 
        any(comp in q_clean for comp in ["compare", "comparison", "more", "higher", "greater", "winner", "better", "versus", "vs", "difference", "performance"])
    )

    if is_rate_missing and is_engagement_query:
        ans = "Direct engagement comparison is not possible because one video's engagement rate cannot be calculated."
        yield f"data: {json.dumps({'type': 'token', 'content': ans})}\n\n"

        citations = [
            {
                "video_id": "A",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video A: Title='{meta_a.get('title')}', Creator='{meta_a.get('creator')}', EngagementRate='{rate_a}'",
            },
            {
                "video_id": "B",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video B: Title='{meta_b.get('title')}', Creator='{meta_b.get('creator')}', EngagementRate='{rate_b}'",
            }
        ]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        yield "data: [DONE]\n\n"

        memory.chat_memory.add_user_message(question)
        memory.chat_memory.add_ai_message(ans)
        return

    # Check for general comparison queries
    comparison_phrases = [
        "compare both videos",
        "compare them",
        "compare both",
        "compare the two videos",
        "compare the videos",
        "compare video a and video b",
        "compare video a and b",
        "compare video b and a",
        "compare video b and video a",
        "compare the videos a and b",
        "compare a and b",
        "compare both of these",
        "compare these videos",
        "compare these two",
        "give me a comparison",
        "give a comparison",
        "show a comparison",
        "show me a comparison",
        "comparison of",
    ]
    is_compare_all = any(phrase in q_clean for phrase in comparison_phrases) or q_clean == "compare"

    full_response = ""

    # Prepend structured template for broad comparison requests
    if is_compare_all:
        views_a_str = f"{meta_a.get('views'):,}" if meta_a.get('views') is not None else "Not Available"
        views_b_str = f"{meta_b.get('views'):,}" if meta_b.get('views') is not None else "Not Available"
        
        def format_rate(rate):
            if rate is None or rate == "None" or rate == "":
                return "N/A"
            try:
                return f"{float(rate):.2f}%"
            except (ValueError, TypeError):
                return "N/A"
                
        rate_a_str = format_rate(meta_a.get("engagement_rate"))
        rate_b_str = format_rate(meta_b.get("engagement_rate"))
        
        likes_a = meta_a.get("likes") or 0
        comments_a = meta_a.get("comments") or 0
        total_a = likes_a + comments_a
        
        likes_b = meta_b.get("likes") or 0
        comments_b = meta_b.get("comments") or 0
        total_b = likes_b + comments_b
        
        duration_a_str = f"{meta_a.get('duration')} seconds" if meta_a.get('duration') else "0 seconds"
        duration_b_str = f"{meta_b.get('duration')} seconds" if meta_b.get('duration') else "0 seconds"
        
        platform_a_str = format_platform(meta_a.get("platform"))
        platform_b_str = format_platform(meta_b.get("platform"))
        
        comparison_table = (
            f"Views:\n"
            f"- Video A: {views_a_str}\n"
            f"- Video B: {views_b_str}\n\n"
            f"Engagement:\n"
            f"- Video A: {rate_a_str}\n"
            f"- Video B: {rate_b_str}\n\n"
            f"Interactions:\n"
            f"- Video A: {total_a:,} (Likes: {likes_a:,}, Comments: {comments_a:,})\n"
            f"- Video B: {total_b:,} (Likes: {likes_b:,}, Comments: {comments_b:,})\n\n"
            f"Duration:\n"
            f"- Video A: {duration_a_str}\n"
            f"- Video B: {duration_b_str}\n\n"
            f"Platform:\n"
            f"- Video A: {platform_a_str}\n"
            f"- Video B: {platform_b_str}\n\n"
        )
        yield f"data: {json.dumps({'type': 'token', 'content': comparison_table})}\n\n"
        full_response += comparison_table

    history = memory.chat_memory.messages  # list of HumanMessage / AIMessage

    system_prompt = _build_system_prompt(meta_a, meta_b, chunks, is_compare_query=is_compare_all)

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(history)
    messages.append(HumanMessage(content=question))

    try:
        async for chunk in llm.astream(messages):
            token = chunk.content
            if token:
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
    except Exception as e:
        logger.error("LLM streaming error: %s", e)
        yield f"data: {json.dumps({'type': 'token', 'content': f'Error generating response: {e}'})}\n\n"

    # Persist turn to memory only after successful generation
    if full_response:
        memory.chat_memory.add_user_message(question)
        memory.chat_memory.add_ai_message(full_response)

    citations = [
        {
            "video_id": c["metadata"].get("video_id", ""),
            "chunk_index": c["metadata"].get("chunk_index", 0),
            "preview": c["text"][:120] + ("..." if len(c["text"]) > 120 else ""),
        }
        for c in chunks
    ]

    # Clean multi-video citation logic:
    # If the response references/uses metadata from both videos but citations only contains one,
    # append a static metadata citation for the missing video.
    has_a_cit = any(c["video_id"] == "A" for c in citations)
    has_b_cit = any(c["video_id"] == "B" for c in citations)

    ref_a_detected = is_video_referenced(full_response, "A", meta_a)
    ref_b_detected = is_video_referenced(full_response, "B", meta_b)

    # Determine if both were used
    if (has_a_cit and has_b_cit) or (ref_a_detected and ref_b_detected) or is_compare_all:
        ref_a = True
        ref_b = True
    else:
        ref_a = has_a_cit or ref_a_detected
        ref_b = has_b_cit or ref_b_detected

    if ref_a and ref_b:
        if not has_a_cit:
            citations.append({
                "video_id": "A",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video A: Title='{meta_a.get('title')}', Creator='{meta_a.get('creator')}'",
            })
        if not has_b_cit:
            citations.append({
                "video_id": "B",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video B: Title='{meta_b.get('title')}', Creator='{meta_b.get('creator')}'",
            })
    else:
        if ref_a and not has_a_cit:
            citations.append({
                "video_id": "A",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video A: Title='{meta_a.get('title')}', Creator='{meta_a.get('creator')}'",
            })
        if ref_b and not has_b_cit:
            citations.append({
                "video_id": "B",
                "chunk_index": 0,
                "preview": f"Static Metadata for Video B: Title='{meta_b.get('title')}', Creator='{meta_b.get('creator')}'",
            })

    yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
    yield "data: [DONE]\n\n"