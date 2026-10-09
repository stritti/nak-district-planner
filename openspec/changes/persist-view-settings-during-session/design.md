## Context

Die bestehende Capability `frontend-ux` beschreibt gemeinsame UX-Regeln. Die Matrix bietet bereits einen Gemeindetextfilter und eine optionale Gruppensortierung. Für Filter und Sortierungen soll eine gemeinsame Sitzungsregel gelten, ohne Matrix- und Eventlisten-Einstellungen zu vermischen.

## Goals / Non-Goals

**Ziele:** Den zuletzt gewählten Filter- und Sortierzustand während der Sitzung wiederherstellen, einschließlich Navigation und Reload; Ansicht, Benutzer und fachlichen Kontext voneinander trennen.

**Nicht Bestandteil:** Dauerhafte Benutzerpräferenzen über mehrere Sitzungen hinweg, tabübergreifende Synchronisierung, Speicherung von Ergebnisdaten, Scrollpositionen oder Bearbeitungsformularen.

## Decisions

### Sitzung als Browser-Tab-Sitzung

Eine Sitzung umfasst die Nutzung im selben Browser-Tab einschließlich Neuladen. Das Ende der Tab-Sitzung oder eine explizite Abmeldung beendet die Gültigkeit gespeicherter Einstellungen. Ein neu begonnener, unabhängig geöffneter Tab startet mit Standardwerten. Kopierte oder wiederhergestellte Tabs müssen beim späteren Implementieren anhand der Browser-Semantik geprüft werden; eine dauerhafte oder tabübergreifende Synchronisierung ist nicht gefordert.

### Zustände pro Benutzer, Kontext und Ansicht

Ein Matrix-Zustand und ein Eventlisten-Zustand werden unabhängig geführt. Innerhalb einer Sitzung darf der Wechsel zu einer anderen Ansicht den bisherigen Zustand nicht überschreiben. Der Schlüssel berücksichtigt die Benutzeridentität und den jeweiligen Bezirk bzw. die Gemeinde. Ein Kontextwechsel darf keine Einstellungen des vorherigen Kontexts übernehmen; beim Zurückwechseln wird dessen gültiger Zustand wiederhergestellt.

### Gültige Werte wiederherstellen

Filter, Sortierfeld, Sortierrichtung und vorhandene Sortieroptionen werden gemeinsam als letzter Zustand einer Ansicht erfasst. Bei Wiederherstellung müssen die angezeigten Bedienelemente und das angeforderte bzw. dargestellte Ergebnis übereinstimmen. Entfallene oder nicht mehr zugängliche Filterwerte werden auf gültige Standardwerte zurückgesetzt; unveränderte gültige Werte bleiben erhalten. Gespeicherte Einstellungen erweitern niemals Zugriffsrechte.

### Technische Umsetzung später festlegen

Die Anforderung legt das beobachtbare Verhalten fest. Die konkrete Frontend-Speicherung und Integration werden bei der Umsetzung ausgewählt. Falls Sitzungsspeicherung nicht verfügbar oder beschädigt ist, bleibt die Ansicht mit Standardwerten nutzbar.

## Risks / Trade-offs

- Sitzungsspeicherung kann veraltete Gruppen- oder Gemeinde-IDs enthalten: vor Anwendung gegen den aktuellen Kontext validieren.
- Abmeldung oder Benutzerwechsel könnte Zustand vermischen: Speicher und In-Memory-Zustand beim Identitätswechsel bereinigen.
- Nur die Controls wiederherzustellen würde falsche Ergebnisse zeigen: Datenabfrage und Controls aus demselben Zustand ableiten.

## Validation

Navigation, Reload, getrennte Ansichten/Kontexte, explizite Rücksetzung, Abmeldung, neue Sitzung und ungültig gewordene Werte in Unit- und Browser-Tests prüfen. Für Matrix und Eventliste jeweils konkrete Filter- und Sortierkombinationen verwenden.
