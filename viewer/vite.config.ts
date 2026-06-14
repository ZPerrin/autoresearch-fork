import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import * as fs from 'fs'
import * as path from 'path'
import type { Connect } from 'vite'

const ROOT = path.resolve(__dirname, '..')

function contentType(filePath: string): string {
  if (filePath.endsWith('.json')) return 'application/json'
  if (filePath.endsWith('.png'))  return 'image/png'
  return 'application/octet-stream'
}

/** Minimal path-traversal guard: resolve and ensure it starts with ROOT */
function safeResolve(root: string, ...parts: string[]): string | null {
  const resolved = path.resolve(root, ...parts)
  return resolved.startsWith(root + path.sep) || resolved === root ? resolved : null
}

function makeStaticMiddleware(urlPrefix: string, fsDir: string): Connect.NextHandleFunction {
  return (req, res) => {
    // rest is the path after the prefix, e.g. "/index.json" or "/grid-invoice-v1/images/0.png"
    const rest = req.url ?? '/'
    const segments = rest.split('/').filter(Boolean)
    const filePath = safeResolve(fsDir, ...segments)

    if (!filePath) {
      res.statusCode = 400
      res.end('Bad request')
      return
    }

    // Synthesized datasets index
    if (urlPrefix === '/datasets' && rest === '/index.json') {
      const synthesized = synthesizeDatasetsIndex(fsDir)
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify(synthesized))
      return
    }

    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
      res.statusCode = 404
      res.end('Not found')
      return
    }

    res.setHeader('Content-Type', contentType(filePath))
    fs.createReadStream(filePath).pipe(res)
  }
}

function synthesizeDatasetsIndex(datasetsDir: string): { schema_version: number; datasets: unknown[] } {
  if (!fs.existsSync(datasetsDir)) {
    return { schema_version: 2, datasets: [] }
  }
  const datasets: unknown[] = []
  try {
    for (const entry of fs.readdirSync(datasetsDir)) {
      const manifestPath = path.join(datasetsDir, entry, 'manifest.json')
      if (fs.existsSync(manifestPath)) {
        try {
          const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
          datasets.push(manifest)
        } catch {
          // skip malformed manifests
        }
      }
    }
  } catch {
    // skip unreadable dir
  }
  return { schema_version: 2, datasets }
}

// https://vite.dev/config/
export default defineConfig({
  // Honor the PORT env var (e.g. from preview/launch tooling); default to Vite's 5173.
  server: process.env.PORT ? { port: Number(process.env.PORT) } : undefined,
  plugins: [
    react(),
    {
      name: 'repo-data-middleware',
      configureServer(server) {
        server.middlewares.use('/runs',     makeStaticMiddleware('/runs',     path.join(ROOT, 'runs')))
        server.middlewares.use('/datasets', makeStaticMiddleware('/datasets', path.join(ROOT, 'datasets')))
      },
    },
  ],
})
