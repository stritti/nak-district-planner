import { test, expect } from '@playwright/test'
import { createServer, type Server } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { resolve, extname, sep } from 'node:path'

const dist = resolve('dist')
const requests: { path: string; authorization?: string }[] = []
let server: Server
let origin: string

// Real HTTP responses: Playwright route mocks can bypass or miss service workers.
test.beforeAll(async () => {
  server = createServer((request, response) => {
    void (async () => {
      const url = new URL(request.url ?? '/', 'http://localhost')
      if (url.pathname.startsWith('/api/') || url.pathname === '/health') {
        requests.push({ path: url.pathname + url.search, authorization: request.headers.authorization })
        if (/^\/api\/v1\/export\/(public|internal)-fixture\/calendar\.ics$/.test(url.pathname)) {
          response.writeHead(200, {
            'Content-Type': 'text/calendar; charset=utf-8',
            'Content-Disposition': 'attachment; filename="calendar.ics"',
          })
          response.end([
            'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Export routing fixture//EN',
            'BEGIN:VEVENT', 'UID:routing-fixture@example.invalid',
            'DTSTAMP:20261010T000000Z', 'DTSTART:20261011T080000Z',
            'DTEND:20261011T090000Z', 'SUMMARY:Routing fixture',
            'END:VEVENT', 'END:VCALENDAR', '',
          ].join('\r\n'))
          return
        }
        if (url.pathname === '/health') {
          response.writeHead(200, { 'Content-Type': 'application/json' })
          response.end(JSON.stringify({ status: 'ok' }))
          return
        }
        response.writeHead(url.pathname.startsWith('/api/v1/export/') ? 404 : 401, {
          'Content-Type': 'application/json',
        })
        response.end(JSON.stringify({ detail: 'Fixture response' }))
        return
      }

      const candidate = resolve(dist, '.' + decodeURIComponent(url.pathname))
      if (candidate !== dist && !candidate.startsWith(dist + sep)) {
        response.writeHead(400)
        response.end()
        return
      }
      let file = candidate
      try {
        if (!(await stat(file)).isFile()) file = resolve(dist, 'index.html')
      } catch {
        file = resolve(dist, 'index.html')
      }
      const types: Record<string, string> = {
        '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
        '.json': 'application/json', '.webmanifest': 'application/manifest+json',
        '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
      }
      response.writeHead(200, {
        'Content-Type': types[extname(file)] ?? 'application/octet-stream',
        'Cache-Control': 'no-cache',
      })
      response.end(await readFile(file))
    })().catch(() => {
      if (!response.headersSent) response.writeHead(500)
      response.end()
    })
  })
  await new Promise<void>((done) => server.listen(0, '127.0.0.1', done))
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('Missing test server address')
  origin = 'http://127.0.0.1:' + address.port
})

test.afterAll(async () => {
  await new Promise<void>((done, reject) => {
    server.close((error) => error ? reject(error) : done())
    server.closeAllConnections()
  })
})

test('built PWA sends calendar navigations and health to the network', async ({ browser }) => {
  const context = await browser.newContext({ serviceWorkers: 'allow', acceptDownloads: true })
  try {
    const page = await context.newPage()
    await page.goto(origin + '/login')
    await page.evaluate(async () => { await navigator.serviceWorker.ready })
    await page.reload()
    await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true)

    for (const type of ['public', 'internal']) {
      const path = '/api/v1/export/' + type + '-fixture/calendar.ics?approval_status=confirmed_only'
      const downloadTab = await context.newPage()
      const downloadPromise = downloadTab.waitForEvent('download')
      // A real attachment navigation is aborted by Chromium when handed to download.
      await downloadTab.goto(origin + path).catch((error: Error) => {
        if (!error.message.includes('net::ERR_ABORTED') &&
            !error.message.includes('Download is starting')) throw error
      })
      const download = await downloadPromise
      expect(await download.failure()).toBeNull()
      expect(download.suggestedFilename()).toBe('calendar.ics')
      const downloadPath = await download.path()
      if (!downloadPath) throw new Error('Missing download')
      expect(await readFile(downloadPath, 'utf8')).toContain('BEGIN:VCALENDAR')
      expect(requests).toContainEqual({ path, authorization: undefined })
      await downloadTab.close()
    }

    // Navigation, not fetch(): the old NavigationRoute would return index.html here.
    for (const token of ['unknown-fixture', 'deleted-fixture']) {
      const response = await page.goto(origin + '/api/v1/export/' + token + '/calendar.ics')
      expect(response?.status()).toBe(404)
      expect(response?.headers()['content-type']).toContain('application/json')
      expect(await page.content()).not.toContain('Freigabe ausstehend')
    }

    const health = await page.goto(origin + '/health')
    expect(health?.status()).toBe(200)
    expect(await health?.json()).toEqual({ status: 'ok' })

    // Ordinary frontend routes still use the cached app shell.
    await page.goto(origin + '/login')
    await context.setOffline(true)
    const app = await page.goto(origin + '/login?offline-fixture')
    expect(app?.status()).toBe(200)
    expect(app?.headers()['content-type']).toContain('text/html')
    await context.setOffline(false)
  } finally {
    await context.close()
  }
})
