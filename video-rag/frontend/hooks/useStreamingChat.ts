'use client'

import { useState, useCallback } from 'react'
import type { Message, Citation } from '@/types'
import { getChatUrl } from '@/lib/api'

interface UseStreamingChatOptions {
    sessionId: string
    urlA: string
    urlB: string
}

export function useStreamingChat({ sessionId, urlA, urlB }: UseStreamingChatOptions) {
    const [messages, setMessages] = useState<Message[]>([])
    const [isLoading, setIsLoading] = useState(false)

    const sendMessage = useCallback(async (question: string) => {
        if (isLoading || !question.trim()) return

        const userMessage: Message = {
            id: crypto.randomUUID(),
            role: 'user',
            content: question.trim(),
        }

        const assistantId = crypto.randomUUID()
        const assistantMessage: Message = {
            id: assistantId,
            role: 'assistant',
            content: '',
            isStreaming: true,
        }

        setMessages(prev => [...prev, userMessage, assistantMessage])
        setIsLoading(true)

        try {
            const res = await fetch(getChatUrl(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question.trim(),
                    session_id: sessionId,
                    url_a: urlA,
                    url_b: urlB,
                }),
            })

            if (!res.ok || !res.body) {
                throw new Error(`Request failed: ${res.status}`)
            }

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            outer: while (true) {
                const { done, value } = await reader.read()
                if (done) break

                // Buffer handles SSE events split across multiple reads
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() ?? ''

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue

                    const raw = line.slice(6).trim()
                    if (raw === '[DONE]') break outer

                    try {
                        const parsed = JSON.parse(raw) as
                            | { type: 'token'; content: string }
                            | { type: 'citations'; citations: Citation[] }

                        if (parsed.type === 'token') {
                            setMessages(prev =>
                                prev.map(m =>
                                    m.id === assistantId
                                        ? { ...m, content: m.content + parsed.content }
                                        : m
                                )
                            )
                        } else if (parsed.type === 'citations') {
                            setMessages(prev =>
                                prev.map(m =>
                                    m.id === assistantId
                                        ? { ...m, citations: parsed.citations }
                                        : m
                                )
                            )
                        }
                    } catch { /* malformed line — skip */ }
                }
            }
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Something went wrong.'
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantId ? { ...m, content: msg } : m
                )
            )
        } finally {
            setIsLoading(false)
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantId ? { ...m, isStreaming: false } : m
                )
            )
        }
    }, [isLoading, sessionId, urlA, urlB])

    return { messages, isLoading, sendMessage }
}