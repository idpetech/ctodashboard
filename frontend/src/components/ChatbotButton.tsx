import React, { useState } from 'react'
import Chatbot from './Chatbot'

interface ChatbotButtonProps {
  apiUrl: string
}

const ChatbotButton: React.FC<ChatbotButtonProps> = ({ apiUrl }) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Floating Chatbot Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-blue-500 hover:bg-blue-600 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center z-40 group"
        title="Ask me about your assignments, costs, and metrics"
      >
        <svg 
          className="w-6 h-6 transition-transform group-hover:scale-110" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" 
          />
        </svg>
        
        {/* Notification dot */}
        <div className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
          <span className="text-xs text-white font-bold">!</span>
        </div>
      </button>

      {/* Chatbot Modal */}
      <Chatbot 
        apiUrl={apiUrl} 
        isOpen={isOpen} 
        onClose={() => setIsOpen(false)} 
      />
    </>
  )
}

export default ChatbotButton

