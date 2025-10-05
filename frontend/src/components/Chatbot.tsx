import React, { useState, useEffect, useRef } from 'react'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: string
  confidence?: number
  sources?: string[]
}

interface ChatbotProps {
  apiUrl: string
  isOpen: boolean
  onClose: () => void
}

const Chatbot: React.FC<ChatbotProps> = ({ apiUrl, isOpen, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [userId] = useState('default') // In a real app, this would come from auth
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load conversation history on mount
  useEffect(() => {
    if (isOpen) {
      loadHistory()
    }
  }, [isOpen])

  const loadHistory = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/chatbot/history?user_id=${userId}&limit=20`)
      const data = await response.json()
      
      if (data.history) {
        const historyMessages: ChatMessage[] = data.history.flatMap((entry: any) => [
          {
            id: `${entry.timestamp}-user`,
            type: 'user' as const,
            content: entry.question,
            timestamp: entry.timestamp
          },
          {
            id: `${entry.timestamp}-assistant`,
            type: 'assistant' as const,
            content: entry.response,
            timestamp: entry.timestamp,
            confidence: entry.confidence
          }
        ])
        setMessages(historyMessages)
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await fetch(`${apiUrl}/api/chatbot/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          user_id: userId
        })
      })

      const data = await response.json()

      if (response.ok) {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: data.response,
          timestamp: data.timestamp,
          confidence: data.confidence,
          sources: data.sources
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        throw new Error(data.error || 'Failed to get response')
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
        confidence: 0
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearHistory = async () => {
    try {
      await fetch(`${apiUrl}/api/chatbot/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId })
      })
      setMessages([])
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-bold">🤖</span>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">CTO Dashboard Assistant</h2>
              <p className="text-sm text-gray-500">Ask me about your assignments, metrics, and costs</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={clearHistory}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
              title="Clear conversation history"
            >
              Clear
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <div className="text-4xl mb-4">🤖</div>
              <h3 className="text-lg font-medium mb-2">Welcome to CTO Dashboard Assistant!</h3>
              <p className="text-sm">I can help you with questions about:</p>
              <ul className="text-sm mt-2 space-y-1">
                <li>• Your assignments and projects</li>
                <li>• AWS costs and resource usage</li>
                <li>• GitHub metrics and activity</li>
                <li>• Jira project status</li>
                <li>• Team information and tech stacks</li>
                <li>• Service health and configuration</li>
              </ul>
              <p className="text-sm mt-4 text-gray-400">Try asking: "What's our total monthly burn rate?" or "Show me AWS costs"</p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.type === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                
                {/* Message metadata */}
                <div className={`text-xs mt-2 ${
                  message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  <div className="flex items-center justify-between">
                    <span>{formatTimestamp(message.timestamp)}</span>
                    {message.type === 'assistant' && message.confidence !== undefined && (
                      <span className="ml-2">
                        Confidence: {Math.round(message.confidence * 100)}%
                      </span>
                    )}
                  </div>
                  
                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-1">
                      <span className="text-xs">Sources: {message.sources.join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about your assignments, costs, metrics..."
              className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
          
          {/* Quick action buttons */}
          <div className="flex flex-wrap gap-2 mt-2">
            {[
              "What's our total monthly burn rate?",
              "Show me AWS costs",
              "How many active assignments do we have?",
              "What's our team size?",
              "Show me GitHub activity"
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => setInputValue(suggestion)}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chatbot

