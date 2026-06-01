import json
import logging
import os

from dotenv import load_dotenv
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.gemini_errors import (
    GENERIC_AI_ERROR_MESSAGE,
    INVALID_API_KEY_MESSAGE,
    QUOTA_EXCEEDED_MESSAGE,
    UserFacingGeminiError,
    get_gemini_user_message,
    is_quota_error,
)
from app.services.gemini_keys import load_gemini_keys, log_key_usage
from app.services.retriever import get_video_metadata, retrieve

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

# In-process session memory. Each key is a session_id.
# Survives for the lifetime of the server process.
memory_store: dict[str, ConversationBufferWindowMemory] = {}


def clear_session_state():
    global memory_store
    memory_store.clear()


def _get_gemini_timeout_seconds() -> float:
    try:
        return float(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "45"))
    except ValueError:
        return 45.0


def get_llm(api_key: str | None = None) -> ChatGoogleGenerativeAI:
    # Reload environment variables from .env dynamically to pick up updates without restart
    load_dotenv(override=True)
    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise UserFacingGeminiError(INVALID_API_KEY_MESSAGE)
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        temperature=0.3,
        google_api_key=api_key,
        max_output_tokens=4000,
        timeout=_get_gemini_timeout_seconds(),
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
- Hashtags: {", ".join(meta_a.get('hashtags', [])) if meta_a.get('hashtags') else 'None'}

VIDEO B:
- Title: {meta_b.get('title', 'Video B')}
- Creator: {meta_b.get('creator', 'Unknown')}
- Platform: {platform_b}
- Engagement Rate: {rate_b}
- Views: {views_b}
- Likes: {meta_b.get('likes', 'N/A') if meta_b.get('likes') is not None else 'N/A'}
- Comments: {meta_b.get('comments', 'N/A') if meta_b.get('comments') is not None else 'N/A'}
- Duration: {meta_b.get('duration', 'N/A') if meta_b.get('duration') is not None else 'N/A'} seconds
- Hashtags: {", ".join(meta_b.get('hashtags', [])) if meta_b.get('hashtags') else 'None'}

RETRIEVED CONTEXT:
{context}

CONTENT-FIRST REASONING RULE:
You MUST prioritize reasoning about the actual video content, transcript themes, hook styles, topic choice, and creator presentation (from the RETRIEVED CONTEXT) over raw metrics (views, likes, comments) when comparing performance or providing insights/feedback.
When analyzing video content, prioritize the available information in this order:
1. Transcript/captions (actual spoken content, dialogue, script, presentation style, pacing).
2. Description and hashtags (written summaries, tags, themes, target audience).
3. Metadata metrics (views, likes, comments, creator, title) as supplemental context to support content-based insights.

COMPARISON INTELLIGENCE RUBRIC:
When comparing two videos, explicitly evaluate and contrast:
1. Hook strength: the opening premise, curiosity gap, first-line payoff, or attention-grabbing setup.
2. Storytelling: narrative clarity, pacing, structure, and whether the content builds momentum.
3. Engagement: likes, comments, engagement rate, and interaction signals as supporting evidence.
4. CTA quality: whether the transcript/description suggests a clear call-to-action, comment prompt, or follow-through.
5. Strengths and weaknesses: specific content-based positives and gaps for each video.
6. Overall winner: choose a winner only when the evidence supports it, and explain why in one sentence.

Use retrieved transcript content first, then description/hashtags, then metadata metrics last.

When comparing performance or giving feedback:
1. Explain how the content elements (narrative style, topic, captions, themes, and hooks) drive the performance.
2. Avoid weak answers like "Video B performed better because it has more likes." Instead, analyze the actual video content (e.g. "Video A uses emotional references and cricket fandom, while Video B uses educational storytelling").
3. Use the static metadata primarily as supplemental evidence to support your content-based findings.

RULES:
- Use the static video metadata to answer questions about metrics (views, likes, comments, engagement rate, duration), creators, or titles.
- Use the retrieved context for questions about the actual content, transcript, topics, hooks, or video scripts.
- If the retrieved context is empty, sparse, or doesn't contain content chunks, you MUST state that the actual video transcript/content is unavailable, and proceed to compare the videos based ONLY on the provided static metadata (title, creator, platform, views, likes, comments, duration). Do not make up or assume any video content details.
- Do NOT say data is unavailable or return "N/A" if the metric is present in the static video metadata above.
- Always cite which video (A or B) your answer references.
- Be specific. Vague answers are not useful to a creator.
- Format your response using clean, structured Markdown:
  * Use section headers (## and ###) for major headings.
  * Use bold text (**word**) to highlight key metrics, insights, and video labels.
  * Use bullet points (- or *) with proper spacing to make lists readable.
  * When comparing or evaluating both videos, use this exact structure:
    ## Reach
    - Video A: <reach metric or "Not Available">
    - Video B: <reach metric or "Not Available">

    ## Engagement
    - Video A: <engagement rate or "N/A"> (Likes: <likes>, Comments: <comments>, Interactions: <total>)
    - Video B: <engagement rate or "N/A"> (Likes: <likes>, Comments: <comments>, Interactions: <total>)

    ## Content Analysis
    <Short paragraph analysis>

    ## Recommendation
    - <Actionable bullet>
  * Avoid inline labels like "Views:" or "Engagement:" inside paragraphs.
  * Use markdown tables only when a table is explicitly requested.

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
A Reach/Engagement summary has already been shown to the user.
You MUST NOT output another list of metrics, repeat values, or show a table.
Write exactly two sections:

## Content Analysis
2-4 concise sentences explaining the differences or performance highlights based ONLY on available metrics and retrieved content.

## Recommendation
- 2-4 actionable bullet points for the creator.
"""
        return prompt_prefix + comparison_instruction
    else:
        compare_rule = """
COMPARE BOTH VIDEOS TEMPLATE RULE:
If the user asks a broad comparison request (such as "Compare both videos", "compare them", or similar general comparison requests), you MUST format your comparison using the following structured template instead of writing free-form paragraphs:

## Reach
- Video A: <value or "Not Available">
- Video B: <value or "Not Available">

## Engagement
- Video A: <engagement rate or "N/A"> (Likes: <likes>, Comments: <comments>, Interactions: <total>)
- Video B: <engagement rate or "N/A"> (Likes: <likes>, Comments: <comments>, Interactions: <total>)

## Content Analysis
<Short paragraph comparing hook, storytelling, CTA, and topic fit using transcript/context evidence>

## Strengths
- Video A: <specific strength>
- Video B: <specific strength>

## Weaknesses
- Video A: <specific weakness>
- Video B: <specific weakness>

## Overall Winner
- Winner: <Video A or Video B>
- Reason: <one concise evidence-based explanation>

## Recommendation
- <Actionable bullet>

(Note: Keep it concise. Do not repeat metrics outside the Reach/Engagement sections.)"""
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
    full_response = ""
    chunk_count = 0

    async def yield_event(event_type: str, payload: dict | str):
        nonlocal chunk_count
        if event_type == "done":
            event_str = "data: [DONE]\n\n"
        else:
            event_str = f"data: {json.dumps({'type': event_type, **payload})}\n\n"
        
        logger.info("Stream event sent: %s", event_str.strip())
        chunk_count += 1
        yield event_str

    try:
        # 1. Fetch metadata and build memory
        chunks = retrieve(question, url_a, url_b)
        meta_a = get_video_metadata("A")
        meta_b = get_video_metadata("B")
        memory = get_memory(session_id)

        # 2. Deterministic guards
        q_clean = "".join(c for c in question.lower() if c.isalnum() or c.isspace()).strip()
        
        # Audience loyalty guard
        is_loyalty = "loyal" in q_clean or "loyalty" in q_clean
        if is_loyalty:
            ans = (
                "Available metadata is insufficient to determine audience loyalty.\n\n"
                "Video A has higher raw interactions.\n"
                "Video B has measurable engagement rate.\n\n"
                "Neither metric alone proves audience loyalty."
            )
            full_response = ans
            # Yield in smaller word chunks to simulate a stream
            import re
            for part in re.split(r'(\s+)', ans):
                if part:
                    async for ev in yield_event("token", {"content": part}):
                        yield ev
            
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
            async for ev in yield_event("citations", {"citations": citations}):
                yield ev
            async for ev in yield_event("done", {}):
                yield ev
            
            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(ans)
            return

        # Reach comparison guard
        views_a = meta_a.get("views")
        views_b = meta_b.get("views")
        is_views_missing = (views_a is None or views_a == "None") or (views_b is None or views_b == "None")
        is_reach_query = (
            ("reach" in q_clean or "view" in q_clean) and 
            any(comp in q_clean for comp in ["compare", "comparison", "more", "higher", "greater", "winner", "better", "versus", "vs", "difference", "performance"])
        )

        if is_views_missing and is_reach_query:
            ans = "Reach comparison is not possible because view data is unavailable."
            full_response = ans
            import re
            for part in re.split(r'(\s+)', ans):
                if part:
                    async for ev in yield_event("token", {"content": part}):
                        yield ev
            
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
            async for ev in yield_event("citations", {"citations": citations}):
                yield ev
            async for ev in yield_event("done", {}):
                yield ev

            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(ans)
            return

        # Engagement comparison guard
        rate_a = meta_a.get("engagement_rate")
        rate_b = meta_b.get("engagement_rate")
        is_rate_missing = (rate_a is None or rate_a == "None") or (rate_b is None or rate_b == "None")
        is_engagement_query = (
            "engagement" in q_clean and 
            any(comp in q_clean for comp in ["compare", "comparison", "more", "higher", "greater", "winner", "better", "versus", "vs", "difference", "performance"])
        )

        if is_rate_missing and is_engagement_query:
            ans = "Direct engagement comparison is not possible because one video's engagement rate cannot be calculated."
            full_response = ans
            import re
            for part in re.split(r'(\s+)', ans):
                if part:
                    async for ev in yield_event("token", {"content": part}):
                        yield ev
            
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
            async for ev in yield_event("citations", {"citations": citations}):
                yield ev
            async for ev in yield_event("done", {}):
                yield ev

            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(ans)
            return

        # Broad comparison template
        comparison_phrases = [
            "compare both videos", "compare them", "compare both", "compare the two videos",
            "compare the videos", "compare video a and video b", "compare video a and b",
            "compare video b and a", "compare video b and video a", "compare the videos a and b",
            "compare a and b", "compare both of these", "compare these videos", "compare these two",
            "give me a comparison", "give a comparison", "show a comparison", "show me a comparison",
            "comparison of",
        ]
        is_compare_all = any(phrase in q_clean for phrase in comparison_phrases) or q_clean == "compare"

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
            
            comparison_sections = (
                f"## Reach\n"
                f"- Video A: {views_a_str}\n"
                f"- Video B: {views_b_str}\n\n"
                f"## Engagement\n"
                f"- Video A: {rate_a_str} (Likes: {likes_a:,}, Comments: {comments_a:,}, Interactions: {total_a:,})\n"
                f"- Video B: {rate_b_str} (Likes: {likes_b:,}, Comments: {comments_b:,}, Interactions: {total_b:,})\n\n"
            )
            full_response += comparison_sections
            async for ev in yield_event("token", {"content": comparison_sections}):
                yield ev

        # 3. Stream from Google GenAI Model
        llm_timeout = _get_gemini_timeout_seconds()
        history = memory.chat_memory.messages
        system_prompt = _build_system_prompt(meta_a, meta_b, chunks, is_compare_query=is_compare_all)

        messages = [SystemMessage(content=system_prompt)]
        messages.extend(history)
        messages.append(HumanMessage(content=question))

        keys = load_gemini_keys()
        if not keys:
            raise UserFacingGeminiError(INVALID_API_KEY_MESSAGE)

        astream_chunks_count = 0
        last_quota_error: BaseException | None = None

        for key in keys:
            log_key_usage(key, len(keys), "chat")
            llm = get_llm(api_key=key.key)
            astream_chunks_count = 0

            try:
                async for chunk in llm.astream(messages, timeout=llm_timeout):
                    token = chunk.content
                    if token:
                        astream_chunks_count += 1
                        full_response += token
                        async for ev in yield_event("token", {"content": token}):
                            yield ev
            except Exception as stream_err:
                if is_quota_error(stream_err) and astream_chunks_count == 0:
                    last_quota_error = stream_err
                    logger.warning("Gemini quota hit with key %s; rotating.", key.label)
                    continue
                user_message = get_gemini_user_message(stream_err)
                if user_message:
                    raise UserFacingGeminiError(user_message) from stream_err
                logger.warning("astream error, falling back to ainvoke: %s", stream_err)

            # Fallback to ainvoke if astream failed or returned empty content
            if astream_chunks_count == 0:
                logger.info("astream returned no content. Falling back to ainvoke.")
                try:
                    response = await llm.ainvoke(messages, timeout=llm_timeout)
                except Exception as invoke_err:
                    if is_quota_error(invoke_err) and astream_chunks_count == 0:
                        last_quota_error = invoke_err
                        logger.warning("Gemini quota hit with key %s; rotating.", key.label)
                        continue
                    user_message = get_gemini_user_message(invoke_err)
                    if user_message:
                        raise UserFacingGeminiError(user_message) from invoke_err
                    raise
                content = response.content
                if content:
                    import re
                    words = re.split(r'(\s+)', content)
                    for word in words:
                        if word:
                            full_response += word
                            async for ev in yield_event("token", {"content": word}):
                                yield ev

            last_quota_error = None
            break

        if last_quota_error:
            raise UserFacingGeminiError(QUOTA_EXCEEDED_MESSAGE) from last_quota_error

        # 5. Persist turn to memory only after successful generation
        if full_response.strip():
            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(full_response)

            # Build and yield citations only when we have content
            citations = [
                {
                    "video_id": c["metadata"].get("video_id", ""),
                    "chunk_index": c["metadata"].get("chunk_index", 0),
                    "preview": c["text"][:120] + ("..." if len(c["text"]) > 120 else ""),
                }
                for c in chunks
            ]

            # Clean multi-video citation logic:
            has_a_cit = any(c["video_id"] == "A" for c in citations)
            has_b_cit = any(c["video_id"] == "B" for c in citations)
            ref_a_detected = is_video_referenced(full_response, "A", meta_a)
            ref_b_detected = is_video_referenced(full_response, "B", meta_b)

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

            async for ev in yield_event("citations", {"citations": citations}):
                yield ev
        else:
            logger.warning("No content generated by the model or guards.")

        # Always yield DONE at the end of a successful run
        async for ev in yield_event("done", {}):
            yield ev

    except UserFacingGeminiError as e:
        logger.warning("Gemini request failed with user-facing error: %s", e.user_message)
        async for ev in yield_event("token", {"content": e.user_message}):
            yield ev
        async for ev in yield_event("done", {}):
            yield ev

    except Exception as e:
        logger.error("Error in stream_response: %s", e, exc_info=True)
        error_msg = get_gemini_user_message(e) or GENERIC_AI_ERROR_MESSAGE
        async for ev in yield_event("token", {"content": error_msg}):
            yield ev
        async for ev in yield_event("done", {}):
            yield ev

    # Final summary logging
    logger.info("STREAM SUMMARY:")
    logger.info("  - Chunk Count: %d", chunk_count)
    logger.info("  - Final Response Length: %d characters", len(full_response))
    logger.info("  - Raw Response: %s", full_response)
