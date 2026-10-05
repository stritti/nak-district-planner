## 1. Coverage-Konfiguration

- [x] 1.1 Production-Code-Scope auf `src/**/*.{ts,vue}` erweitern.
- [x] 1.2 Tests, Test-Support, `*.d.ts` und reines Bootstrap-Wiring explizit ausschliessen.
- [x] 1.3 Mindestschwellen von 80 Prozent pro Production-Datei fuer Statements, Branches, Functions und Lines beibehalten.
- [x] 1.4 Ausfuehrbare Startup-Logik aus `main.ts` in ein separat getestetes Production-Modul verschieben.

## 2. Verifikation

- [ ] 2.1 Frontend Unit Tests erfolgreich.
- [ ] 2.2 Vollstaendige Frontend-Coverage liegt fuer jede gemessene Production-Datei in allen vier Metriken bei mindestens 80 Prozent.
- [ ] 2.3 Falls die neue Messung reale Luecken aufdeckt, gezielte Tests ergaenzen statt den Scope zu verkleinern.

## 3. Async-Testhygiene

- [ ] 3.1 Verbleibende Backend-`coroutine was never awaited`-Warnungen in einem separaten Folge-PR zu #435 bereinigen.
