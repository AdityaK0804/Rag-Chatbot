import type { VideoMeta } from '@/types'

interface VideoCardProps {
    video: VideoMeta
    label: 'A' | 'B'
}

function fmt(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
    if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, '')}K`
    return n.toLocaleString()
}

function fmtDuration(seconds: number): string {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
}

function fmtDate(raw: string): string {
    if (!raw || raw.length !== 8) return raw
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
}

export function VideoCard({ video, label }: VideoCardProps) {
    const isA = label === 'A'
    const isInstagram = video.platform === 'instagram'

    const platformBadge = isInstagram ? (
        <span className="bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 text-white font-code text-[10px] px-2.5 py-1 rounded font-bold uppercase tracking-wide">
            Instagram Reels
        </span>
    ) : (
        <span className="bg-red-600 text-white font-code text-[10px] px-2.5 py-1 rounded font-bold uppercase tracking-wide">
            {video.platform === 'youtube_shorts' ? 'YouTube Shorts' : 'YouTube'}
        </span>
    )

    return (
        <div className={`glass-panel rounded-2xl overflow-hidden flex flex-col group border-surface-variant/30 ${isA ? 'border-primary/15' : ''}`}>
            {/* Thumbnail - cinematic aspect-video */}
            {video.thumbnail ? (
                <div className="relative aspect-video bg-surface-container-low overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                        src={video.thumbnail}
                        alt={video.title}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent"></div>
                    <div className="absolute top-3 left-3 flex flex-col gap-1">
                        {platformBadge}
                    </div>
                    <div className="absolute top-3 right-3 flex items-center gap-1.5">
                        <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                            Video {label}
                        </span>
                        {video.already_indexed && (
                            <span className="bg-primary/20 backdrop-blur-sm text-primary text-[10px] px-1.5 py-0.5 rounded border border-primary/20">
                                cached
                            </span>
                        )}
                    </div>
                    {video.duration > 0 && (
                        <div className="absolute bottom-3 right-3">
                            <span className="font-code text-white bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded text-[11px]">
                                {fmtDuration(video.duration)}
                            </span>
                        </div>
                    )}
                </div>
            ) : (
                <div className="relative aspect-video bg-surface-container flex items-center justify-center border-b border-surface-variant/30">
                    <span className="text-xs font-bold text-on-surface-variant bg-black/40 px-3 py-1.5 rounded">
                        Video {label} (No Thumbnail)
                    </span>
                    <div className="absolute top-3 right-3">
                        {platformBadge}
                    </div>
                </div>
            )}

            {/* Content area with increased vertical padding (p-6) */}
            <div className="p-6 flex-1 flex flex-col justify-between space-y-4">
                {/* Title + Creator */}
                <div className="mb-4">
                    <h3 
                        className="font-headline font-bold text-base leading-tight mb-1 text-on-surface line-clamp-2 hover:text-primary transition-colors cursor-help"
                        title={video.title || 'Untitled'}
                    >
                        {video.title || 'Untitled'}
                    </h3>
                    <p className="text-on-surface-variant text-sm">
                        @{video.creator || 'Unknown'}
                        {video.follower_count > 0 && (
                            <span className="text-on-surface-variant/60"> · {fmt(video.follower_count)} followers</span>
                        )}
                    </p>
                </div>

                {/* 2x2 Stats grid matching Stitch layout */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                    {/* Views */}
                    <div className="p-3 rounded-xl bg-surface-container-low border border-surface-variant/30 flex flex-col justify-between">
                        <p className="text-[10px] font-code text-on-surface-variant uppercase mb-1">Views</p>
                        <p className="text-base font-bold text-on-surface leading-tight">
                            {video.views !== null && video.views !== undefined ? fmt(video.views) : 'Not Available'}
                        </p>
                    </div>

                    {/* Likes */}
                    <div className="p-3 rounded-xl bg-surface-container-low border border-surface-variant/30 flex flex-col justify-between">
                        <p className="text-[10px] font-code text-on-surface-variant uppercase mb-1">Likes</p>
                        <p className="text-base font-bold text-on-surface leading-tight">{fmt(video.likes)}</p>
                    </div>

                    {/* Engagement / Interactions */}
                    <div className="p-3 rounded-xl bg-surface-container-low border border-surface-variant/30 flex flex-col justify-between">
                        {video.views === null || video.views === undefined ? (
                            <>
                                <p className="text-[10px] font-code text-on-surface-variant uppercase mb-1">Interactions</p>
                                <p className="text-base font-bold text-secondary leading-tight">
                                    {fmt(video.likes + video.comments)}
                                </p>
                            </>
                        ) : (
                            <>
                                <p className="text-[10px] font-code text-on-surface-variant uppercase mb-1">Engagement</p>
                                <p className="text-base font-bold text-secondary leading-tight">
                                    {video.engagement_rate !== null && video.engagement_rate !== undefined
                                        ? `${video.engagement_rate.toFixed(2)}%`
                                        : 'N/A'}
                                </p>
                            </>
                        )}
                    </div>

                    {/* Comments */}
                    <div className="p-3 rounded-xl bg-surface-container-low border border-surface-variant/30 flex flex-col justify-between">
                        <p className="text-[10px] font-code text-on-surface-variant uppercase mb-1">Comments</p>
                        <p className="text-base font-bold text-on-surface leading-tight">{fmt(video.comments)}</p>
                    </div>
                </div>

                {/* Meta row */}
                <div className="flex flex-wrap items-center gap-2 text-[10px] text-on-surface-variant/70 font-code border-t border-surface-variant/20 pt-2">
                    {video.upload_date && (
                        <span>{fmtDate(video.upload_date)}</span>
                    )}
                    {video.chunks_stored > 0 && (
                        <span>· {video.chunks_stored} chunks</span>
                    )}
                </div>

                {/* Hashtags */}
                {video.hashtags.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1 items-center">
                        {video.hashtags.slice(0, 5).map(tag => {
                            const cleanTag = tag.startsWith('#') ? tag.slice(1) : tag
                            const displayTag = cleanTag.length > 15 
                                ? `${cleanTag.slice(0, 12)}...` 
                                : cleanTag
                            
                            const tagStyle = isA 
                                ? 'bg-primary/5 text-primary/80 border-primary/10'
                                : 'bg-secondary/5 text-secondary border-secondary/10'

                            return (
                                <span 
                                    key={tag} 
                                    className={`font-code text-[10px] px-2 py-1 rounded border uppercase leading-none ${tagStyle}`}
                                    title={tag.startsWith('#') ? tag : `#${tag}`}
                                >
                                    #{displayTag}
                                </span>
                            )
                        })}
                        {video.hashtags.length > 5 && (
                            <span 
                                className="font-code text-[9px] text-on-surface-variant bg-surface-container-low px-2 py-1 rounded leading-none border border-surface-variant/30 cursor-help"
                                title={video.hashtags.slice(5).map(t => t.startsWith('#') ? t : `#${t}`).join(', ')}
                            >
                                +{video.hashtags.length - 5}
                            </span>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}