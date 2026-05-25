import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import TabbedApp from './TabbedApp.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TabbedApp />
  </StrictMode>,
)
