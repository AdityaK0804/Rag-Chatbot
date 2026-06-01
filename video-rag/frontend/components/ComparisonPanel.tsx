import type { VideoMeta } from '@/types'

interface ComparisonPanelProps {
    videoA: VideoMeta
    videoB: VideoMeta
}

function getWinnerByReach(vA: VideoMeta, vB: VideoMeta): string {
    if (vA.views === null || vA.views === undefined || vB.views === null || vB.views === undefined) {
        return 'Insufficient Data'
    }
    if (vA.views > vB.views) return 'Video A'
    if (vB.views > vA.views) return 'Video B'
    return 'Tie'
}

function getWinnerByEngagement(vA: VideoMeta, vB: VideoMeta): string {
    if (vA.engagement_rate === null || vA.engagement_rate === undefined || vB.engagement_rate === null || vB.engagement_rate === undefined) {
        return 'Insufficient Data'
    }
    if (vA.engagement_rate > vB.engagement_rate) return 'Video A'
    if (vB.engagement_rate > vA.engagement_rate) return 'Video B'
    return 'Tie'
}

function getWinnerByInteractions(vA: VideoMeta, vB: VideoMeta): string {
    const intA = vA.likes + vA.comments
    const intB = vB.likes + vB.comments
    if (intA > intB) return 'Video A'
    if (intB > intA) return 'Video B'
    return 'Tie'
}

function getPlatformName(platform: string): string {
    if (platform === 'youtube_shorts') return 'YouTube Shorts'
    if (platform === 'youtube') return 'YouTube'
    if (platform === 'instagram') return 'Instagram'
    return platform
}

function getBarWidth(winner: string, valA: number | null | undefined, valB: number | null | undefined): string {
    if (winner === 'Insufficient Data' || valA === null || valA === undefined || valB === null || valB === undefined) {
        return '0%'
    }
    const total = valA + valB
    if (total === 0) return '50%'
    
    // Percentage relative to the total value for visualization
    if (winner === 'Video A') {
        return `${Math.round((valA / total) * 100)}%`
    } else if (winner === 'Video B') {
        return `${Math.round((valB / total) * 100)}%`
    } else if (winner === 'Tie') {
        return '50%'
    }
    return '50%'
}

export function ComparisonPanel({ videoA, videoB }: ComparisonPanelProps) {
    const reachWinner = getWinnerByReach(videoA, videoB)
    const engagementWinner = getWinnerByEngagement(videoA, videoB)
    const interactionsWinner = getWinnerByInteractions(videoA, videoB)
    const platformComparison = `${getPlatformName(videoA.platform)} vs ${getPlatformName(videoB.platform)}`

    const renderWinnerValue = (winner: string) => {
        if (winner === 'Insufficient Data') {
            return (
                <span className="text-[10px] text-on-surface-variant/70 font-bold font-code uppercase">
                    Insufficient Data
                </span>
            )
        }
        if (winner === 'Tie') {
            return (
                <span className="text-[10px] text-primary font-bold font-code uppercase">
                    Tie
                </span>
            )
        }
        return (
            <span className="flex items-center gap-1 text-[10px] text-secondary font-bold font-code uppercase">
                <svg className="w-3.5 h-3.5 text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {winner}
            </span>
        )
    }

    return (
        <div className="glass-panel rounded-2xl p-6 flex flex-col border-surface-variant/30 justify-between">
            <div>
                {/* Header */}
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <svg className="w-4.5 h-4.5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
                        </svg>
                    </div>
                    <h3 className="font-headline text-lg font-bold text-on-surface">Quick Comparison</h3>
                </div>

                {/* Grid Comparison Rows */}
                <div className="space-y-4">
                    {/* Winner by Reach */}
                    <div className="p-4 rounded-xl border border-surface-variant/40 bg-surface-container-low/50 flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <span className="text-[11px] font-code text-on-surface-variant uppercase tracking-wider">Winner by Reach</span>
                            {renderWinnerValue(reachWinner)}
                        </div>
                        <div className="w-full bg-surface-variant/30 h-1.5 rounded-full overflow-hidden">
                            <div 
                                className="bg-secondary h-full transition-all duration-500 rounded-full" 
                                style={{ width: getBarWidth(reachWinner, videoA.views, videoB.views) }}
                            />
                        </div>
                    </div>

                    {/* Winner by Engagement */}
                    <div className="p-4 rounded-xl border border-surface-variant/40 bg-surface-container-low/50 flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <span className="text-[11px] font-code text-on-surface-variant uppercase tracking-wider">Winner by Engagement</span>
                            {renderWinnerValue(engagementWinner)}
                        </div>
                        <div className="w-full bg-surface-variant/30 h-1.5 rounded-full overflow-hidden">
                            <div 
                                className="bg-secondary h-full transition-all duration-500 rounded-full" 
                                style={{ width: getBarWidth(engagementWinner, videoA.engagement_rate, videoB.engagement_rate) }}
                            />
                        </div>
                    </div>

                    {/* Winner by Interactions */}
                    <div className="p-4 rounded-xl border border-surface-variant/40 bg-surface-container-low/50 flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <span className="text-[11px] font-code text-on-surface-variant uppercase tracking-wider">Winner by Interactions</span>
                            {renderWinnerValue(interactionsWinner)}
                        </div>
                        <div className="w-full bg-surface-variant/30 h-1.5 rounded-full overflow-hidden">
                            <div 
                                className="bg-secondary h-full transition-all duration-500 rounded-full" 
                                style={{ width: getBarWidth(interactionsWinner, videoA.likes + videoA.comments, videoB.likes + videoB.comments) }}
                            />
                        </div>
                    </div>
                </div>
            </div>
            
            {/* Platforms Footer Card */}
            <div className="p-4 rounded-xl border border-surface-variant/30 bg-black/20 text-on-surface-variant text-[12px] flex items-center gap-2 mt-4">
                <svg className="w-4.5 h-4.5 text-on-surface-variant/80 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="italic font-medium truncate">Platforms: {platformComparison}</span>
            </div>
        </div>
    )
}
