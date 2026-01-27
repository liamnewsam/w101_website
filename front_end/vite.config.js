import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: "/"
})

/* 

export default defineConfig({
  plugins: [react()],
  base: process.env.NODE_ENV === "production"
    ? "/projects/w101/w101-demo/"
    : "/",   // Important!
})

*/