'use client'

import { useState, useMemo } from 'react'
import type { VideoState } from '@/types'
import { ingestVideos } from '@/lib/api'
import { IngestForm } from '@/components/IngestForm'
import { VideoCard } from '@/components/VideoCard'
import { ComparisonPanel } from '@/components/ComparisonPanel'
import { ChatPanel } from '@/components/ChatPanel'

export default function Page() {
  const [videos, setVideos] = useState<VideoState>({ A: null, B: null })
  const [isIngesting, setIsIngesting] = useState(false)

  // Stable for the lifetime of the page — new session on hard refresh
  const sessionId = useMemo(() => crypto.randomUUID(), [])

  const hasVideos = videos.A !== null && videos.B !== null

  const handleIngest = async (urlA: string, urlB: string) => {
    setIsIngesting(true)
    try {
      const data = await ingestVideos(urlA, urlB)
      setVideos({ A: data.videos.A, B: data.videos.B })
    } finally {
      setIsIngesting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background font-body text-on-surface antialiased pb-20">
      {/* Header - Fixed top bar */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 md:px-12 h-16 bg-background/80 backdrop-blur-md border-b border-surface-variant/50">
        <div className="flex items-center gap-3">
          <h1 className="font-headline text-lg font-bold tracking-tight text-on-surface">Video RAG</h1>
        </div>
        {hasVideos && (
          <button
            onClick={() => setVideos({ A: null, B: null })}
            className="text-on-surface-variant font-medium text-xs hover:text-on-surface transition-all active:scale-95 flex items-center gap-1.5 cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.253 8H18" />
            </svg>
            Reset
          </button>
        )}
      </header>

      {/* Main Flow Content Container */}
      <main className="pt-24 px-6 md:px-12 max-w-[1280px] mx-auto flex flex-col gap-10">
        {/* Analyze Form Input Bar */}
        <section>
          <IngestForm onSubmit={handleIngest} isLoading={isIngesting} />
        </section>

        {!hasVideos ? (
          // Empty State centered below the form
          <div className="flex flex-col items-center justify-center text-center py-20 px-6 gap-4">
            <p className="text-on-surface-variant text-sm max-w-md font-body leading-relaxed">
              Enter two video URLs above to analyze and compare them. Supports YouTube Shorts and Instagram Reels.
            </p>
            {isIngesting && (
              <div className="flex items-center gap-3 text-primary text-sm font-semibold bg-surface-container/60 border border-surface-variant/40 px-5 py-3 rounded-2xl shadow-lg animate-pulse">
                <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <span>Fetching transcripts and indexing content…</span>
              </div>
            )}
          </div>
        ) : (
          // Main layout content
          <>
            {/* 3-Column Video Cards & Comparison Panel Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <VideoCard video={videos.A!} label="A" />
              <VideoCard video={videos.B!} label="B" />
              <ComparisonPanel videoA={videos.A!} videoB={videos.B!} />
            </div>

            {/* AI Chat interaction section - full width below */}
            <section className="h-[600px] flex flex-col">
              <ChatPanel sessionId={sessionId} videos={videos} />
            </section>
          </>
        )}
      </main>
    </div>
  )
}