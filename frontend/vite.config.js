import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from "path"
import { fileURLToPath } from "url"

// Emulamos __dirname para ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function packageChunkName(id) {
  if (id.includes('node_modules/exceljs')) {
    return 'vendor-exceljs'
  }

  if (
    id.includes('node_modules/react/') ||
    id.includes('node_modules/react-dom/') ||
    id.includes('node_modules/react-router/') ||
    id.includes('node_modules/react-router-dom/') ||
    id.includes('node_modules/@reduxjs/toolkit/') ||
    id.includes('node_modules/react-redux/') ||
    id.includes('node_modules/redux/') ||
    id.includes('node_modules/reselect/') ||
    id.includes('node_modules/immer/')
  ) {
    return 'vendor-react'
  }

  if (
    id.includes('node_modules/@react-pdf/')
  ) {
    const afterReactPdf = id.split('node_modules/@react-pdf/')[1]
    const packageName = afterReactPdf.split('/')[0]
    return `vendor-react-pdf-${packageName}`
  }

  if (id.includes('node_modules/pdfkit/')) {
    return 'vendor-pdfkit'
  }

  if (id.includes('node_modules/fontkit/')) {
    return 'vendor-fontkit'
  }

  if (id.includes('node_modules/yoga-layout/')) {
    return 'vendor-yoga'
  }

  return null
}


// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/src/modules/')) {
            const normalized = id.replace(/\\/g, '/')
            const match = normalized.match(/\/src\/modules\/([^/]+)\//)
            if (match?.[1]) {
              return `module-${match[1]}`
            }
          }

          return packageChunkName(id)
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setupTests.js'],
    css: false,
    include: ['src/**/*.test.{js,jsx,ts,tsx}'],
  },
})
