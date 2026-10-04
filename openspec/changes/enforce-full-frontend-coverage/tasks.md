## 1. Coverage-Konfiguration

- [x] 1.1 Production-Code-Scope auf `src/**/*.{ts,vue}` erweitern.
- [x] 1.2 Tests, `*.d.ts` und Bootstrap-Datei explizit ausschliessen.
- [x] 1.3 Globale Mindestschwellen von 80 Prozent fuer Statements, Branches, Functions und Lines beibehalten.

## 2. Verifikation

- [ ] 2.1 Frontend Unit Tests erfolgreich.
- [ ] 2.2 Vollstaendige Frontend-Coverage liegt in allen vier Metriken bei mindestens 80 Prozent.
- [ ] 2.3 Falls die neue Messung reale Luecken aufdeckt, gezielte Tests ergaenzen statt den Scope zu verkleinern.

## 3. Async-Testhygiene

- [ ] 3.1 Verbleibende Backend-`coroutine was never awaited`-Warnungen in einem separaten Folge-PR zu #435 bereinigen.