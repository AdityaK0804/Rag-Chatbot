**Video RAG**
-------------------------------------

Video RAG is a video-based chatbot that allows user to compare and analyze Youtube Shorts and Instagram Reels.

The system ingest videos from the 2 platforms input by the user, extracts transcripts and metadata, then stores them in a vector database(ChromaDB) and uses Gemini with RAG to answer questions such as:

- *Why did Video A get more engagement than Video B?*
- *What's the engagement rate of each?*
- *Compare the hooks in the first 5 seconds.*
- *Who's the creator of Video B and what's their follower count?*
- *Suggest improvements for B based on what worked in A.*

**1. Project overview**
--------------------------------------
Video RAG ingests short videos, pulls whatever transcripts and metadata it can, chops content into chunks, indexes them in ChromaDB, and then runs a Gemini-powered RAG chat that can answer questions like:

- *Why did Video A get more engagement than Video B?*
- *What's the engagement rate of each?*
- *Compare the hooks in the first 5 seconds.*
- *Who's the creator of Video B and what's their follower count?*
- *Suggest improvements for B based on what worked in A.*

