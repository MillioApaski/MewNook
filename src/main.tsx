/// <reference types="vite-plugin-pwa/client" />
import React from 'react'
import{registerSW}from'virtual:pwa-register'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './immersive.css'

// Use the update-aware client: the former injected registration never reloaded
// an already-open preview after the replacement worker took control.
registerSW({immediate:true})

createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
)
