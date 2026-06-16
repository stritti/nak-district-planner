# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: matrix-assignment.spec.ts >> Matrix assignment flow >> gap can be assigned and turns into assigned cell
- Location: tests/e2e/matrix-assignment.spec.ts:6:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: 'Zuweisen' })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - navigation [ref=e4]:
    - generic [ref=e6]:
      - generic [ref=e7]:
        - generic [ref=e8]: NAK Bezirksplaner
        - generic [ref=e9]:
          - link "Ereignisse" [ref=e10] [cursor=pointer]:
            - /url: /events
            - img [ref=e11]
            - text: Ereignisse
          - link "Dienstplan-Matrix" [ref=e13] [cursor=pointer]:
            - /url: /matrix
            - img [ref=e14]
            - text: Dienstplan-Matrix
          - link "Bezirke & Gemeinden" [ref=e16] [cursor=pointer]:
            - /url: /admin/districts
            - img [ref=e17]
            - text: Bezirke & Gemeinden
          - link "Amtstragende" [ref=e19] [cursor=pointer]:
            - /url: /admin/leaders
            - img [ref=e20]
            - text: Amtstragende
          - link "Kalender" [ref=e22] [cursor=pointer]:
            - /url: /admin/calendars
            - img [ref=e23]
            - text: Kalender
          - link "Export" [ref=e25] [cursor=pointer]:
            - /url: /admin/export
            - img [ref=e26]
            - text: Export
      - generic [ref=e28]:
        - button "Dark Mode aktivieren" [ref=e29]:
          - img [ref=e30]
        - button "Planner User planner@example.com" [ref=e33]:
          - generic [ref=e34]:
            - generic [ref=e35]: Planner User
            - generic [ref=e36]: planner@example.com
          - img [ref=e37]
  - generic [ref=e40]: "Freigabe ausstehend: Ihr Konto ist angemeldet, aber noch keinem Bezirk oder keiner Gemeinde zugeordnet."
  - main [ref=e41]:
    - generic [ref=e42]:
      - heading "Dienstplan-Matrix" [level=1] [ref=e43]
      - generic [ref=e44]:
        - generic [ref=e45]:
          - generic [ref=e46]: "Schnellfilter:"
          - button "Aktueller Monat" [ref=e47]
          - button "Kommender Monat" [ref=e48]
        - generic [ref=e49]:
          - generic [ref=e50]:
            - generic [ref=e51]: Bezirk
            - combobox [ref=e52]:
              - option "Bezirk 1" [selected]
          - generic [ref=e53]:
            - generic [ref=e54]: Sortierung
            - combobox [ref=e55]:
              - option "Standard" [selected]
              - option "Nach Gruppen"
          - generic [ref=e56]:
            - generic [ref=e57]: Von
            - textbox [ref=e58]: 2026-06-01
          - generic [ref=e59]:
            - generic [ref=e60]: Bis
            - textbox [ref=e61]: 2026-06-30
          - button "Anzeigen" [ref=e62]:
            - img [ref=e63]
            - text: Anzeigen
          - button "Excel" [ref=e65]:
            - img [ref=e66]
            - text: Excel
          - button "Entwuerfe erzeugen" [ref=e68]:
            - img [ref=e69]
            - text: Entwuerfe erzeugen
          - button "Freigabe" [ref=e71]:
            - img [ref=e72]
            - text: Freigabe
          - generic [ref=e74]:
            - button "Normal" [ref=e75]
            - button "Kompakt" [ref=e76]
      - table [ref=e78]:
        - rowgroup [ref=e79]:
          - row "Gemeinde Mi 08.04.2026" [ref=e80]:
            - columnheader "Gemeinde" [ref=e81]
            - columnheader "Mi 08.04.2026" [ref=e82]:
              - generic [ref=e83]: Mi
              - generic [ref=e84]: 08.04.2026
        - rowgroup [ref=e85]:
          - row "Gemeinde A Gottesdienst Pr. Tester Gottesdienst" [ref=e86]:
            - cell "Gemeinde A" [ref=e87]
            - cell "Gottesdienst Pr. Tester Gottesdienst" [ref=e88] [cursor=pointer]:
              - button "Gottesdienst Pr. Tester Gottesdienst" [ref=e89]:
                - generic [ref=e90]: Gottesdienst
                - generic [ref=e91]: Pr. Tester
                - generic [ref=e92]: Gottesdienst
      - generic [ref=e94]:
        - generic [ref=e95]:
          - heading "Zuweisung bearbeiten" [level=2] [ref=e96]
          - button [ref=e97]:
            - img [ref=e98]
        - paragraph [ref=e100]: Gemeinde A — 08.04.2026
        - paragraph [ref=e101]: "Ereignis: Gottesdienst"
        - generic [ref=e102]:
          - paragraph [ref=e103]: Einladung fuer diesen Gottesdienst
          - generic [ref=e104]:
            - combobox [ref=e105]:
              - option "Kein Einladungsziel" [selected]
              - option "Gemeinde im Bezirk"
              - option "Freitext-Hinweis"
            - button "Einladung anlegen/aktualisieren" [disabled] [ref=e106]
            - generic [ref=e107]:
              - paragraph [ref=e108]: Bestehende Einladungen
              - paragraph [ref=e109]: Noch keine Einladung gespeichert.
        - generic [ref=e110]:
          - paragraph [ref=e111]: Gottesdienst verschieben
          - generic [ref=e112]:
            - textbox [ref=e113]: 2026-04-08
            - textbox [ref=e114]: 20:00
            - spinbutton [ref=e115]: "90"
            - button "Termin verschieben" [ref=e116]
        - generic [ref=e117]: Amtstragende:r
        - combobox "Name eingeben oder auswählen…" [active] [ref=e119]: Pr. Tester
        - generic [ref=e120]:
          - button "Entfernen" [ref=e121]
          - button "Abbrechen" [ref=e122]
          - button "Bestaetigen" [ref=e123]
          - button "Speichern" [ref=e124]
```

# Test source

```ts
  92  |       })
  93  |     })
  94  | 
  95  |     await page.route('**/api/v1/events/event-1/assignments', async (route) => {
  96  |       if (route.request().method() !== 'POST') {
  97  |         await route.fallback()
  98  |         return
  99  |       }
  100 |       await route.fulfill({
  101 |         status: 201,
  102 |         contentType: 'application/json',
  103 |         body: JSON.stringify({
  104 |           id: 'assignment-1',
  105 |           event_id: 'event-1',
  106 |           leader_id: null,
  107 |           leader_name: 'Pr. Tester',
  108 |           status: 'ASSIGNED',
  109 |           created_at: '2026-04-01T00:00:00Z',
  110 |           updated_at: '2026-04-01T00:00:00Z',
  111 |         }),
  112 |       })
  113 |     })
  114 | 
  115 |     await page.route('**/api/v1/districts/district-1/matrix**', async (route) => {
  116 |       matrixCalls += 1
  117 |       if (matrixCalls === 1) {
  118 |         await route.fulfill({
  119 |           status: 200,
  120 |           contentType: 'application/json',
  121 |           body: JSON.stringify({
  122 |             dates: ['2026-04-08'],
  123 |             holidays: {},
  124 |             rows: [
  125 |               {
  126 |                 congregation_id: 'cong-1',
  127 |                 congregation_name: 'Gemeinde A',
  128 |                 group_id: null,
  129 |                 group_name: null,
  130 |                 cells: {
  131 |                   '2026-04-08': {
  132 |                     event_id: 'event-1',
  133 |                     assignment_event_id: 'event-1',
  134 |                     invitation_count: 0,
  135 |                     event_title: 'Gottesdienst',
  136 |                     category: 'Gottesdienst',
  137 |                     is_gap: true,
  138 |                     is_assignment_editable: true,
  139 |                     assignment_id: null,
  140 |                     assignment_status: null,
  141 |                     leader_id: null,
  142 |                     leader_name: null,
  143 |                   },
  144 |                 },
  145 |               },
  146 |             ],
  147 |           }),
  148 |         })
  149 |         return
  150 |       }
  151 | 
  152 |       await route.fulfill({
  153 |         status: 200,
  154 |         contentType: 'application/json',
  155 |         body: JSON.stringify({
  156 |           dates: ['2026-04-08'],
  157 |           holidays: {},
  158 |           rows: [
  159 |             {
  160 |               congregation_id: 'cong-1',
  161 |               congregation_name: 'Gemeinde A',
  162 |               group_id: null,
  163 |               group_name: null,
  164 |               cells: {
  165 |                 '2026-04-08': {
  166 |                   event_id: 'event-1',
  167 |                   assignment_event_id: 'event-1',
  168 |                   invitation_count: 0,
  169 |                   event_title: 'Gottesdienst',
  170 |                   category: 'Gottesdienst',
  171 |                   is_gap: false,
  172 |                   is_assignment_editable: true,
  173 |                   assignment_id: 'assignment-1',
  174 |                   assignment_status: 'ASSIGNED',
  175 |                   leader_id: null,
  176 |                   leader_name: 'Pr. Tester',
  177 |                 },
  178 |               },
  179 |             },
  180 |           ],
  181 |         }),
  182 |       })
  183 |     })
  184 | 
  185 |     await page.goto(`${FRONTEND_URL}/matrix`)
  186 | 
  187 |     await expect(page.getByRole('button', { name: /Gottesdienst/i })).toBeVisible({ timeout: 10000 })
  188 |     await page.getByRole('button', { name: /Gottesdienst/i }).click()
  189 | 
  190 |     const input = page.getByPlaceholder(/Name eingeben/i)
  191 |     await input.fill('Pr. Tester')
> 192 |     await page.getByRole('button', { name: 'Zuweisen' }).click()
      |                                                          ^ Error: locator.click: Test timeout of 30000ms exceeded.
  193 | 
  194 |     await expect(page.getByText('Pr. Tester')).toBeVisible({ timeout: 10000 })
  195 |   })
  196 | })
  197 | 
```