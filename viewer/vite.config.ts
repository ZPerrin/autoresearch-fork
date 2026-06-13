import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import * as fs from 'fs'
import * as path from 'path'
import type { Connect } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'runs-middleware',
      configureServer(server) {
        server.middlewares.use('/runs', ((req, res, _next) => {
          // req.url is the path after /runs, e.g. /index.json or /_fixture/run.json
          const rest = req.url ?? '/'
          const filePath = path.resolve(__dirname, '..', 'runs', ...rest.split('/').filter(Boolean))

          if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
            res.statusCode = 404
            res.end('Not found')
            return
          }

          res.setHeader('Content-Type', 'application/json')
          fs.createReadStream(filePath).pipe(res)
        }) as Connect.NextHandleFunction)
      },
    },
  ],
})
