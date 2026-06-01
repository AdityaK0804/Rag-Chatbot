'use client'

import { useEffect, useRef, type KeyboardEvent } from 'react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { VideoState } from '@/types'
import { useStreamingChat } from '@/hooks/useStreamingChat'
import { SourceBadge } from './SourceBadge'

interface ChatPanelProps {
    sessionId: string
    videos: VideoState
}

export function ChatPanel({ sessionId, videos }: ChatPanelProps) {
    const [input, setInput] = useState('')
    const bottomRef = useRef<HTMLDivElement>(null)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const { messages, isLoading, sendMessage } = useStreamingChat({
        sessionId,
        urlA: videos.A?.url ?? '',
        urlB: videos.B?.url ?? '',
    })

    // Scroll to bottom on new content (only when messages exist to prevent scroll on mount)
    useEffect(() => {
        if (messages.length > 0) {
            bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
    }, [messages])

    const handleSend = async () => {
        if (!input.trim() || isLoading) return
        const q = input
        setInput('')
        await sendMessage(q)
    }

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const suggestions = [
        'Which video performed better and why?',
        'Compare engagement rates.',
        'Which creator has a more loyal audience?',
        'What can Video B learn from Video A?',
    ]

    return (
        <div className="glass-panel rounded-2xl flex flex-col h-full border border-surface-variant/30 overflow-hidden shadow-2xl">
            {/* Active Model Indicator Header */}
            <div className="px-6 py-3 border-b border-surface-variant/35 flex justify-between items-center bg-background/50 flex-shrink-0">
                <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-primary animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 9.172V5L8 4z" />
                    </svg>
                    <h3 className="font-headline font-bold text-[10px] text-on-surface uppercase tracking-wider">Ask About These Videos</h3>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_8px_#4edea3]"></span>
                    <span className="text-[9px] font-code text-on-surface-variant uppercase tracking-widest font-semibold">GEMINI 2.5 FLASH ACTIVE</span>
                </div>
            </div>

            {/* Video presence indicator */}
            {( !videos.A || !videos.B ) && (
                <div className="px-6 py-2 bg-yellow-900/10 border-t border-surface-variant/20 text-[12px] text-yellow-200 flex items-center gap-2">
                    <svg className="w-4 h-4 text-yellow-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M21 12A9 9 0 1112 3a9 9 0 019 9z" />
                    </svg>
                    <div>
                        <div className="font-semibold text-sm">Waiting for videos</div>
                        <div className="text-[11px] text-on-surface-variant">Ingest both videos to get full content-based comparisons.</div>
                    </div>
                </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 scrollbar-thin bg-background/10">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center min-h-[320px] h-full px-4">
                        <div className="bg-surface-container border border-surface-variant/40 rounded-2xl p-6 w-full max-w-lg shadow-xl space-y-4">
                            <div className="flex items-center gap-2 border-b border-surface-variant/30 pb-3">
                                <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                                <h3 className="text-on-surface text-sm font-semibold tracking-wide font-headline">
                                    Ask about these videos
                                </h3>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                                {suggestions.map(s => (
                                    <button
                                        key={s}
                                        onClick={() => sendMessage(s)}
                                        className="text-left text-xs px-4 py-3 bg-surface-container-low/60 hover:bg-surface-container-high border border-surface-variant/30 hover:border-primary/50 text-on-surface-variant hover:text-on-surface rounded-xl transition-all duration-200 shadow-sm flex items-center justify-between group active:scale-[0.98] w-full cursor-pointer"
                                    >
                                        <span className="leading-normal pr-2 font-medium">{s}</span>
                                        <svg className="w-3.5 h-3.5 text-on-surface-variant/40 group-hover:text-primary transform group-hover:translate-x-0.5 transition-all flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                                        </svg>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {messages.length === 0 && isLoading && (
                    <div className="flex justify-start">
                        <div className="flex flex-col items-start gap-1 max-w-[82%] lg:max-w-[72%] w-full">
                            <div className="p-6 md:p-8 rounded-2xl rounded-tl-none ai-sparkle-gradient border border-primary/15 text-on-surface text-[15px] leading-relaxed space-y-4 shadow-lg w-full">
                                <div className="animate-pulse space-y-3">
                                    <div className="h-4 bg-surface-container/30 rounded w-3/4" />
                                    <div className="h-3 bg-surface-container/20 rounded w-5/6" />
                                    <div className="h-3 bg-surface-container/20 rounded w-2/3" />
                                </div>
                            </div>
                            <div className="flex items-center gap-1.5 ml-1.5">
                                <svg className="w-3 h-3 text-primary animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 9.172V5L8 4z" />
                                </svg>
                                <span className="text-[8px] font-code text-primary uppercase font-bold tracking-widest">Gemini</span>
                            </div>
                        </div>
                    </div>
                )}

                {messages.map(message => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        {message.role === 'user' ? (
                            <div className="flex flex-col items-end gap-1 max-w-[80%]">
                                <div className="p-4 rounded-2xl rounded-tr-none bg-surface-container-high border border-surface-variant/50 text-on-surface text-sm leading-relaxed shadow-sm">
                                    <p className="whitespace-pre-wrap">{message.content}</p>
                                </div>
                                <span className="text-[8px] font-code text-on-surface-variant uppercase tracking-wider mr-1">You</span>
                            </div>
                        ) : (
                            <div className="flex flex-col items-start gap-1 max-w-[82%] lg:max-w-[72%] w-full">
                                <div className="p-6 md:p-8 rounded-2xl rounded-tl-none ai-sparkle-gradient border border-primary/15 text-on-surface text-[15px] leading-relaxed space-y-4 shadow-lg w-full">
                                    <div className={`font-body markdown-content space-y-6 ${message.isStreaming ? 'is-streaming' : ''}`}>
                                        {message.content.split(/(?=^##\s)/m).map((section, idx) => {
                                            const isSection = section.startsWith('##');
                                            return (
                                                <div
                                                    key={idx}
                                                    className={isSection ? "p-5 md:p-6 rounded-xl bg-surface-container/30 border border-surface-variant/20 hover:border-primary/10 transition-colors shadow-sm" : ""}
                                                >
                                                    <ReactMarkdown 
                                                        remarkPlugins={[remarkGfm]}
                                                        components={{
                                                            a: ({ node, ...props }) => (
                                                                <a target="_blank" rel="noopener noreferrer" {...props} />
                                                            )
                                                        }}
                                                    >
                                                        {section}
                                                    </ReactMarkdown>
                                                </div>
                                            );
                                        })}
                                    </div>
                                    {message.citations && message.citations.length > 0 && (
                                        <div className="pt-4 border-t border-surface-variant/20 flex flex-wrap gap-1.5 w-full">
                                            <SourceBadge citations={message.citations} />
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-1.5 ml-1.5">
                                    <svg className="w-3 h-3 text-primary animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 9.172V5L8 4z" />
                                    </svg>
                                    <span className="text-[8px] font-code text-primary uppercase font-bold tracking-widest">Gemini</span>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="flex-shrink-0 border-t border-surface-variant/30 p-4 bg-surface-container-low/40">
                <div className="relative w-full flex items-center">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type your technical query..."
                        disabled={isLoading}
                        rows={1}
                        className="w-full bg-surface-container border border-surface-variant/50 rounded-xl py-3.5 pl-5 pr-14 focus:outline-none focus:ring-1 focus:ring-primary/40 focus:border-primary/50 text-sm text-on-surface placeholder:text-on-surface-variant/40 resize-none overflow-y-auto max-h-24 transition-all shadow-inner disabled:opacity-50"
                    />
                    <div className="absolute right-3">
                        <button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className="bg-primary hover:brightness-110 active:scale-95 disabled:bg-surface-variant disabled:text-on-surface-variant/40 text-black p-2 rounded-lg transition-all flex items-center justify-center cursor-pointer disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin block" />
                            ) : (
                                <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            )}
                        </button>
                    </div>
                </div>
                <div className="flex justify-between items-center mt-2 px-1 text-[9px] font-code text-on-surface-variant/60">
                    <span>Session: {sessionId.slice(0, 8)}…</span>
                    <span>Press Enter to send</span>
                </div>
            </div>
        </div>
    )
}