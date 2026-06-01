export interface VideoMeta {
    video_id: string
    url: string
    platform: string
    title: string
    creator: string
    views: number | null
    likes: number
    comments: number
    follower_count: number
    hashtags: string[]
    upload_date: string
    duration: number
    thumbnail: string
    engagement_rate: number | null
    chunks_stored: number
    already_indexed?: boolean
}

export interface Citation {
    video_id: string
    chunk_index: number
    preview: string
}

export interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    citations?: Citation[]
    isStreaming?: boolean
}

export interface IngestResponse {
    status: string
    videos: {
        A: VideoMeta
        B: VideoMeta
    }
}

export interface VideoState {
    A: VideoMeta | null
    B: VideoMeta | null
}