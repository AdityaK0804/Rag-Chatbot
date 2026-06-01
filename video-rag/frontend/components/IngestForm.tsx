'use client'

import { useState, type FormEvent } from 'react'

interface IngestFormProps {
    onSubmit: (urlA: string, urlB: string) => Promise<void>
    isLoading: boolean
}

export function IngestForm({ onSubmit, isLoading }: IngestFormProps) {
    const [urlA, setUrlA] = useState('')
    const [urlB, setUrlB] = useState('')
    const [error, setError] = useState<string | null>(null)

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        if (!urlA.trim() || !urlB.trim()) {
            setError('Both URLs are required.')
            return
        }
        try {
            await onSubmit(urlA.trim(), urlB.trim())
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Ingestion failed.')
        }
    }

    return (
        <form onSubmit={handleSubmit} className="w-full">
            <div className="glass-panel rounded-2xl p-2 md:p-3 flex flex-col md:flex-row items-center gap-3">
                <div className="relative flex-1 w-full group">
                    <svg className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-primary transition-colors w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    <input
                        type="text"
                        value={urlA}
                        onChange={e => setUrlA(e.target.value)}
                        placeholder="Video A URL (YouTube/Reels)"
                        disabled={isLoading}
                        className="w-full bg-transparent border-none rounded-xl py-3 pl-12 pr-6 focus:ring-0 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none disabled:opacity-50"
                    />
                </div>
                <div className="hidden md:block w-px h-8 bg-surface-variant/50"></div>
                <div className="relative flex-1 w-full group">
                    <svg className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-primary transition-colors w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    <input
                        type="text"
                        value={urlB}
                        onChange={e => setUrlB(e.target.value)}
                        placeholder="Video B URL (YouTube/Reels)"
                        disabled={isLoading}
                        className="w-full bg-transparent border-none rounded-xl py-3 pl-12 pr-6 focus:ring-0 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none disabled:opacity-50"
                    />
                </div>
                <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full md:w-auto bg-primary text-black px-8 h-12 rounded-xl font-bold flex items-center justify-center gap-2 transition-all active:scale-95 hover:shadow-[0_0_25px_rgba(139,92,246,0.25)] shrink-0 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                    {isLoading ? (
                        <>
                            <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                            <span>Analyzing...</span>
                        </>
                    ) : (
                        <>
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            <span>Analyze</span>
                        </>
                    )}
                </button>
            </div>
            {error && (
                <p className="mt-2 text-xs text-red-400 pl-4">{error}</p>
            )}
        </form>
    )
}