import React from 'react'

interface LoadingSpinnerProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'hourglass' | 'spinner'
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  message = "Loading...", 
  size = 'md',
  variant = 'hourglass'
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8', 
    lg: 'w-12 h-12'
  }

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg'
  }

  if (variant === 'hourglass') {
    return (
      <div className="flex flex-col items-center justify-center p-8">
        {/* Hourglass Animation */}
        <div className={`${sizeClasses[size]} mb-4`}>
          <div className="hourglass-spinner">
            <div className="hourglass-top"></div>
            <div className="hourglass-bottom"></div>
            <div className="hourglass-sand"></div>
          </div>
        </div>
        <p className={`text-gray-600 ${textSizeClasses[size]} animate-pulse`}>
          {message}
        </p>
        
        <style jsx>{`
          .hourglass-spinner {
            position: relative;
            width: 100%;
            height: 100%;
            animation: rotate 2s infinite linear;
          }
          
          .hourglass-top,
          .hourglass-bottom {
            position: absolute;
            width: 100%;
            height: 50%;
            border: 2px solid #3b82f6;
            border-radius: 50% 50% 0 0;
            box-sizing: border-box;
          }
          
          .hourglass-bottom {
            top: 50%;
            border-radius: 0 0 50% 50%;
            border-top: none;
            border-bottom: 2px solid #3b82f6;
          }
          
          .hourglass-sand {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 2px;
            height: 2px;
            background: #3b82f6;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: sand-fall 2s infinite linear;
          }
          
          .hourglass-sand::before {
            content: '';
            position: absolute;
            top: -20px;
            left: -10px;
            width: 20px;
            height: 20px;
            background: linear-gradient(45deg, transparent 40%, #3b82f6 40%, #3b82f6 60%, transparent 60%);
            border-radius: 50%;
            animation: sand-pour 2s infinite linear;
          }
          
          .hourglass-sand::after {
            content: '';
            position: absolute;
            top: 20px;
            left: -8px;
            width: 16px;
            height: 8px;
            background: #3b82f6;
            border-radius: 50%;
            animation: sand-collect 2s infinite linear;
          }
          
          @keyframes rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          
          @keyframes sand-fall {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
          }
          
          @keyframes sand-pour {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(0.8); }
            100% { opacity: 1; transform: scale(1); }
          }
          
          @keyframes sand-collect {
            0% { transform: scaleY(0.5); opacity: 0.8; }
            50% { transform: scaleY(1); opacity: 1; }
            100% { transform: scaleY(0.8); opacity: 0.9; }
          }
        `}</style>
      </div>
    )
  }

  // Regular spinner fallback
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className={`${sizeClasses[size]} mb-4`}>
        <div className="animate-spin rounded-full border-4 border-gray-300 border-t-blue-500 w-full h-full"></div>
      </div>
      <p className={`text-gray-600 ${textSizeClasses[size]} animate-pulse`}>
        {message}
      </p>
    </div>
  )
}

export default LoadingSpinner
