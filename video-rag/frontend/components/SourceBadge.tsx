import { useState } from 'react'
import type { Citation } from '@/types'

interface SourceBadgeProps {
    citations: Citation[]
}

export function SourceBadge({ citations }: SourceBadgeProps) {
    const [open, setOpen] = useState(false)

    if (!citations || citations.length === 0) return null

    // Determine unique video_ids
    const videoIds = Array.from(new Set(citations.map(c => c.video_id))).sort()
    const hasA = videoIds.includes('A')
    const hasB = videoIds.includes('B')

    let labelText = ''
    let chipColorClass = ''
    let indicatorColorClass = ''
    let popoverHeaderColorClass = ''

    if (hasA && hasB) {
        labelText = 'Sources: Video A, Video B'
        chipColorClass = 'bg-indigo-900/50 text-indigo-300 hover:bg-indigo-800/60'
        indicatorColorClass = 'bg-indigo-400'
        popoverHeaderColorClass = 'text-indigo-400'
    } else if (hasA) {
        labelText = 'Source: Video A'
        chipColorClass = 'bg-blue-900/50 text-blue-300 hover:bg-blue-800/60'
        indicatorColorClass = 'bg-blue-400'
        popoverHeaderColorClass = 'text-blue-400'
    } else if (hasB) {
        labelText = 'Source: Video B'
        chipColorClass = 'bg-emerald-900/50 text-emerald-300 hover:bg-emerald-800/60'
        indicatorColorClass = 'bg-emerald-400'
        popoverHeaderColorClass = 'text-emerald-400'
    } else {
        return null
    }

    return (
        <span className="relative inline-block">
            <button
                onClick={() => setOpen(o => !o)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${chipColorClass}`}
            >
                <span className={`w-1.5 h-1.5 rounded-full ${indicatorColorClass}`} />
                {labelText}
            </button>

            {open && (
                <>
                    {/* Backdrop to close */}
                    <span
                        className="fixed inset-0 z-10"
                        onClick={() => setOpen(false)}
                    />
                    <span className="absolute bottom-full left-0 mb-1.5 z-20 w-80 bg-gray-800 border border-gray-700 rounded-xl p-3 text-[11px] text-gray-300 leading-relaxed shadow-2xl max-h-60 overflow-y-auto scrollbar-thin">
                        <span className={`font-semibold block mb-2 text-xs ${popoverHeaderColorClass}`}>
                            {labelText}
                        </span>
                        <div className="space-y-3">
                            {hasA && (
                                <div>
                                    <span className="font-semibold text-blue-400 block mb-1">Video A Context:</span>
                                    <ul className="list-disc pl-4 space-y-1.5">
                                        {citations
                                            .filter(c => c.video_id === 'A')
                                            .map((c, idx) => (
                                                <li key={idx} className="text-gray-300">
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="flex-1 pr-2">{c.preview}</div>
                                                        <div className="flex-shrink-0 flex items-center gap-2">
                                                            {c.source_type && (
                                                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-800/60 text-blue-200">{c.source_type}</span>
                                                            )}
                                                            {c.confidence_level && (
                                                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${c.confidence_level === 'high' ? 'bg-emerald-700 text-emerald-100' : c.confidence_level === 'medium' ? 'bg-yellow-700 text-yellow-100' : 'bg-rose-700 text-rose-100'}`}>{c.confidence_level}</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </li>
                                            ))}
                                    </ul>
                                </div>
                            )}
                            {hasB && (
                                <div className={hasA ? "border-t border-gray-700/60 pt-2.5" : ""}>
                                    <span className="font-semibold text-emerald-400 block mb-1">Video B Context:</span>
                                    <ul className="list-disc pl-4 space-y-1.5">
                                        {citations
                                            .filter(c => c.video_id === 'B')
                                            .map((c, idx) => (
                                                <li key={idx} className="text-gray-300">
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="flex-1 pr-2">{c.preview}</div>
                                                        <div className="flex-shrink-0 flex items-center gap-2">
                                                            {c.source_type && (
                                                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-800/60 text-emerald-200">{c.source_type}</span>
                                                            )}
                                                            {c.confidence_level && (
                                                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${c.confidence_level === 'high' ? 'bg-emerald-700 text-emerald-100' : c.confidence_level === 'medium' ? 'bg-yellow-700 text-yellow-100' : 'bg-rose-700 text-rose-100'}`}>{c.confidence_level}</span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </li>
                                            ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </span>
                </>
            )}
        </span>
    )
}