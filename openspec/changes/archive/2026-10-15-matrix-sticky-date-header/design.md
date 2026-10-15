## Context

The current `MatrixTable.vue` has `overflow-x-auto` on the table wrapper. In CSS this establishes a scrolling ancestor for sticky descendants, so simply adding `top: 0` to header cells would not keep them visible when the document scrolls.

## Decision

Bound the matrix scroll region to 70dvh with `overflow: auto`. Both horizontal and vertical scrolling now occur inside the same container, so per-cell `position: sticky` works without cloning the header or syncing multiple tables.

- Date headings: `top: 0`, `z-index: 20`, opaque holiday/regular background.
- Congregation names: `left: 0`, `z-index: 10`.
- Corner heading: `top: 0; left: 0`, `z-index: 30`, opaque background.
- Scroll region remains keyboard-focusable and has an accessible label.
- Preserve `useStickyScrollbar` for horizontal navigation; size the proxy viewport to the matrix `clientWidth`. Synchronize normalized scroll progress in both directions, since the browser's effective scroll ranges may still differ by a scrollbar gutter or after layout updates. Keep the native vertical scrollbar and suppress only the native horizontal scrollbar in WebKit to avoid a duplicate.
- Contain horizontal overscroll only (`overscroll-x-contain`); allow vertical scroll chaining to the surrounding page at the first/last row.
- Use a fully opaque holiday heading background (`dark:bg-amber-950`) so content cannot show through sticky cells.
- Empty and short tables do not expand to the maximum height. Header content stays in normal table layout, including multi-line holidays.

## Trade-offs

Long matrices use an inner vertical scroll area rather than extending the full document. This is intentional to make the header sticky with the same horizontal scroll ancestor, but must be verified on narrow/touch viewports. Firefox may expose both its native horizontal scrollbar and the synchronized proxy; both remain functional.

## Verification

Component tests check classes, stacking and holiday/compact variants. Playwright tests must scroll the actual element in both axes and compare `getBoundingClientRect()` coordinates, including a narrow dark-mode viewport, plus exercise the existing proxy scrollbar and a classic vertical scrollbar gutter through the last column. Compare the maximum position reachable by the native matrix scrollbar against the proxy: in Chromium, `scrollbar-gutter: stable` can make `scrollWidth - clientWidth` exceed the actual maximum `scrollLeft` by the gutter width. Test wheel-based scroll chaining at the lower boundary. Render computed header colors into a 1px canvas to assert alpha 255 independently of CSS color serialization (e.g. `rgb()` or `oklch()`).
