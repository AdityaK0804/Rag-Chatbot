**Video RAG**
-------------------------------------

Video RAG is a video-based chatbot that allows user to compare and analyze Youtube Shorts and Instagram Reels.

The system ingest videos from the 2 platforms input by the user, extracts transcripts and metadata, then stores them in a vector database(ChromaDB) and uses Gemini with RAG to answer questions such as:

- *Why did Video A get more engagement than Video B?*
- *What's the engagement rate of each?*
- *Compare the hooks in the first 5 seconds.*
- *Who's the creator of Video B and what's their follower count?*
- *Suggest improvements for B based on what worked in A.*

1)Project overview
--------------------------------------
Video RAG ingests short videos, pulls whatever transcripts and metadata it can, chops content into chunks, indexes them in ChromaDB, and then runs a Gemini-powered RAG chat that can answer questions like:

- *Why did Video A get more engagement than Video B?*
- *What's the engagement rate of each?*
- *Compare the hooks in the first 5 seconds.*
- *Who's the creator of Video B and what's their follower count?*
- *Suggest improvements for B based on what worked in A.*

2)Features
-----------------------------------
- *Video Ingestion(Yt/Instagram)*
- *Transcript extraction with fallback strategies*
- *Metadata extraction(views, likes, comments, creator, follower count, hashtags, upload date, duration)*
- *LangChain-based RAG pipeline*
- *ChromaDB vector storage*
- *Gemini-powerd RAG chat with respone streaming*
- *Cross-platform comparison tools*
- *Metdata fallback if transcripts are unavailable*
- *Source aware responses with citations*


3)Architecture
-----------------------------------
**FrontEnd:**
- *Next.js*
- *Typescript*
- *Tailwind CSS*

**BackEnd:**
- *FastAPI*
- *LangChain*
- *Google Gemini*
- *ChromaDB*

**DataFlow:**
- *User inputs two video URLs*
- *Backend extracts transcripts and metadata*
- *Content is chunked and embedded*
- *Embeddings are stored in ChromaDB*
- *User asks a question*
- *Relevant chunks are retrieved*
- *Gemini generates an answer using retrieved context*
- *Response is streamed back to the frontend*

4)Design Decisions
---------------------------------
**Why ChromaDB?**

For this challenge, ChromaDB was a good fit because:

- Easy local setup
- Lightweight
- Works well with LangChain
- No external infrastructure required

For production-scale, I would consider Pinecone, Qdrant, or Weaviate.


**Why Gemini?**

Gemini provides a strong balance between:

- Response quality
- Speed
- Cost
Since the chatbot mainly performs retrieval-based question answering rather than extremely complex reasoning, Gemini Flash offered good performance without increasing operating costs.


**Handling Missing Data?**

One challenge i came up with was that the transcript and metadata for the videos from yt/insta were often incomplete.
Ex:
- YouTube transcripts may be unavailable
- yt-dlp may get rate limited
- Engagement metrics may be hidden
- Creator information may be missing
Instead of failing completely, the system uses fallback strategies.

- Transcript Fallback
- YouTube Transcript API
- yt-dlp captions
- Description text
- Metadata fallback chunk


**Metadata Fallback Chunk:**

When no transcript is available, the system creates a synthetic chunk containing:

- Title
- Creator
- Description
- Views
- Likes
- Comments
- Follower count
- Platform information

This allows the chatbot to continue answering factual questions even when transcript extraction fails.

5)Screenshots
----------------------------------

**1.Home Page/Landing Page**
<img width="1919" height="867" alt="home page" src="https://github.com/user-attachments/assets/b54b573c-849b-4785-96d7-8b1f946eacce" />

**2.YT Shorts V/S Insta Reel**
<img width="1902" height="850" alt="YT Shorts vs Insta Reel" src="https://github.com/user-attachments/assets/0e65e31d-35d8-4c5e-a4cf-f42e3acd3e0f" />

**3.Sample Responses to Questions**
<img width="1914" height="870" alt="Follower Count" src="https://github.com/user-attachments/assets/1b27566b-9183-4e45-8cf6-f015909b7950" />
<img width="1093" height="567" alt="Q1 A" src="https://github.com/user-attachments/assets/66e80a13-09f9-4e84-a6c7-0efb1d1db099" />
<img width="1077" height="590" alt="Content analysis" src="https://github.com/user-attachments/assets/4d363560-f87b-48af-af23-81d526e0005b" />
<img width="1288" height="571" alt="Recommendation" src="https://github.com/user-attachments/assets/dc2c72ec-57d7-4705-9570-1a9196926e74" />


6)Scalability and Cost
---------------------------------
The system is designed so that expensive processing happens only once during ingestion.

**Ingestion**
- Transcript extraction
- Metadata extraction
- Embedding generation

These operations happen once per video.

**Querying**
When users ask questions:

- Existing embeddings are reused.
- Only relevant chunks are retrieved.
- Gemini receives a small amount of context.

This keeps inference costs low.

**Scaling to 1000 Creators per Day**

A production version could:

- Queue ingestion jobs asynchronously
- Batch embedding requests
- Cache frequently requested videos
- Move metadata to PostgreSQL
- Use a managed vector database
- Horizontally scale FastAPI workers

Because embeddings are generated once and reused, the architecture scales much better than repeatedly processing entire videos for every query.


7)Tech Stack
----------------------------------
**Frontend**
- Next.js
- TypeScript
- Tailwind CSS
**Backend**
- FastAPI
- Python
**AI & RAG**
- LangChain
- Google Gemini
- Google Embeddings
**Storage**
- ChromaDB
**Video Processing**
- yt-dlp
- YouTube Transcript API
**Deployment**
- Vercel (Frontend)
- Render (Backend)

8)Local Setup
----------------------------------
**BackEnd:**
cd video-rag/backend

python -m venv venv


**Windows**
.\venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload


**Frontend**
cd video-rag/frontend

npm install

npm run dev


9)Demo Links
---------------------------------------

**FrontEnd:**
https://rag-chatbot-kryptex08s-projects.vercel.app/
**BackEnd:**
https://rag-chatbot-backend-mrdn.onrender.com
    
