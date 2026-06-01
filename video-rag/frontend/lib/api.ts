import type { IngestResponse } from '@/types'

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function ingestVideos(urlA: string, urlB: string): Promise<IngestResponse> {
    const res = await fetch(`${API_URL}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url_a: urlA, url_b: urlB }),
    })

    if (!res.ok) {
        let message = `Ingestion failed (${res.status})`
        try {
            const err = await res.json()
            if (typeof err.detail === 'string') message = err.detail
            else if (Array.isArray(err.detail)) message = err.detail[0]?.msg ?? message
        } catch { /* ignore */ }
        throw new Error(message)
    }

    return res.json() as Promise<IngestResponse>
}

export function getChatUrl(): string {
    return `${API_URL}/api/chat`
}
