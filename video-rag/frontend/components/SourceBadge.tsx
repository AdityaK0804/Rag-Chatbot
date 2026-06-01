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
                                                    {c.preview}
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
                                                    {c.preview}
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